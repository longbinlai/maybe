class Api::V1::HoldingsController < Api::V1::BaseController
  before_action :ensure_read_scope, only: [ :index ]
  before_action :ensure_read_write_scope, only: [ :create, :update, :destroy, :sync_prices ]
  before_action :set_account, only: [ :create ]

  # GET /api/v1/holdings
  def index
    family = current_resource_owner.family
    holdings_query = family.holdings
      .joins(:account)
      .where(accounts: { status: "active" })
      .where("holdings.qty > 0")

    holdings_query = holdings_query.where(account_id: params[:account_id]) if params[:account_id].present?

    holdings_query = holdings_query
      .select("DISTINCT ON (holdings.account_id, holdings.security_id) holdings.*")
      .order("holdings.account_id, holdings.security_id, holdings.date DESC")

    @holdings = holdings_query.sort_by { |h| -(h.amount || 0) }
    @total_value = @holdings.sum(&:amount)

    render :index
  end

  # POST /api/v1/holdings — Buy shares
  def create
    ticker = params[:ticker]
    qty = params[:qty].to_d
    price = params[:price]&.to_d

    security = Security.find_or_create_by!(ticker: ticker.upcase) do |s|
      s.name = params[:name] || ticker.upcase
      s.offline = false
    end

    if price.nil? || price.zero?
      price = fetch_current_price(security.ticker)
      return render json: { error: "Could not fetch price for #{ticker}" }, status: :unprocessable_entity if price.nil?
    end

    cost = qty * price
    date = params[:date] || Date.current

    # Calculate current holdings value and available cash
    holdings_value = current_holdings_value(@account)
    available_cash = @account.balance - holdings_value

    # Check if this is adding to an existing position
    existing = @account.holdings.find_by(security: security, date: date, currency: @account.currency)
    incremental_cost = if existing
      qty * price - (existing.qty * existing.price)
    else
      cost
    end

    if incremental_cost > available_cash + 0.01
      return render json: {
        error: "Insufficient cash. Available: #{available_cash.to_f.round(2)}, needed: #{incremental_cost.to_f.round(2)}"
      }, status: :unprocessable_entity
    end

    holding = @account.holdings.find_or_initialize_by(
      security: security,
      date: date,
      currency: @account.currency
    )

    holding.assign_attributes(
      qty: qty,
      price: price,
      amount: qty * price,
      source: "manual"
    )

    if holding.save
      # Directly update cash balance (no sync needed for manual holdings)
      new_holdings_value = current_holdings_value(@account)
      new_cash = @account.balance - new_holdings_value
      @account.update_columns(cash_balance: new_cash)
      
      # Trigger balance recalculation to keep historical data accurate
      @account.sync_later

      render json: {
        status: "ok",
        action: existing ? "bought_more" : "bought",
        holding: holding_json(holding),
        account: account_state_json(@account)
      }, status: :created
    else
      render json: { error: holding.errors.full_messages.join(", ") }, status: :unprocessable_entity
    end
  end

  # PATCH /api/v1/holdings/:id — Update position
  def update
    family = current_resource_owner.family
    holding = family.holdings.find(params[:id])
    account = holding.account

    new_qty = params[:qty].present? ? params[:qty].to_d : holding.qty
    new_price = params[:price].present? ? params[:price].to_d : holding.price
    new_amount = new_qty * new_price

    old_amount = holding.qty * holding.price
    delta = new_amount - old_amount

    # Determine what changed
    qty_changed = params[:qty].present? && new_qty != holding.qty
    price_changed = params[:price].present? && new_price != holding.price

    # If increasing position (buying more), check cash
    if delta > 0.01 && qty_changed
      holdings_without_this = current_holdings_value(account) - old_amount
      available_cash = account.balance - holdings_without_this

      if delta > available_cash + 0.01
        return render json: {
          error: "Insufficient cash. Available: #{available_cash.to_f.round(2)}, needed: #{delta.to_f.round(2)}"
        }, status: :unprocessable_entity
      end
    end

    # If selling all, delete the holding
    if new_qty <= 0
      ticker = holding.security.ticker
      holding.destroy
      new_holdings_value = current_holdings_value(account)
      new_cash = account.balance - new_holdings_value
      account.update_columns(cash_balance: new_cash)

      return render json: {
        status: "ok",
        action: "sold_all",
        message: "Sold all #{ticker} shares",
        account: account_state_json(account)
      }
    end

    updates = { qty: new_qty, price: new_price, amount: new_amount }
    updates[:date] = Date.parse(params[:date]) if params[:date].present?

    if holding.update(updates)
      # Recalculate balances based on what changed
      if qty_changed
        # Buy/sell: total stays same, cash changes
        new_holdings_value = current_holdings_value(account)
        new_cash = account.balance - new_holdings_value
        account.update_columns(cash_balance: new_cash)
      elsif price_changed
        # Price update: cash stays same, total changes (market gain/loss)
        new_holdings_value = current_holdings_value(account)
        new_total = account.cash_balance + new_holdings_value
        account.update_columns(balance: new_total)
      end

      # Trigger balance recalculation to keep historical data accurate
      account.sync_later

      action = if qty_changed
        delta > 0.01 ? "bought_more" : "sold_some"
      else
        "price_updated"
      end

      render json: {
        status: "ok",
        action: action,
        holding: holding_json(holding.reload),
        account: account_state_json(account)
      }
    else
      render json: { error: holding.errors.full_messages.join(", ") }, status: :unprocessable_entity
    end
  end

  # DELETE /api/v1/holdings/:id — Sell all shares
  def destroy
    family = current_resource_owner.family
    holding = family.holdings.find(params[:id])

    unless holding.is_manual?
      return render json: { error: "Can only delete manual holdings" }, status: :forbidden
    end

    account = holding.account
    ticker = holding.security.ticker
    amount_sold = holding.amount

    holding.destroy

    new_holdings_value = current_holdings_value(account)
    new_cash = account.balance - new_holdings_value
    account.update_columns(cash_balance: new_cash)
    
    # Trigger balance recalculation to keep historical data accurate
    account.sync_later

    render json: {
      status: "ok",
      action: "sold_all",
      message: "Sold all #{ticker} shares (#{amount_sold.to_f.round(2)} #{holding.currency})",
      account: account_state_json(account)
    }
  end

  # POST /api/v1/holdings/sync_prices
  def sync_prices
    family = current_resource_owner.family
    results = { updated: [], errors: [], skipped: [] }

    securities = Security.joins(:holdings)
      .where(holdings: { account_id: family.accounts.select(:id) })
      .distinct

    securities.each do |security|
      begin
        price = fetch_current_price(security.ticker)
        if price.nil?
          results[:skipped] << { ticker: security.ticker, reason: "no price available" }
          next
        end

        Security::Price.find_or_create_by!(
          security: security,
          date: Date.current,
          currency: security.holdings.first&.currency || "USD"
        ) do |sp|
          sp.price = price
        end

        family.holdings.where(security: security, date: Date.current).each do |holding|
          old_price = holding.price
          holding.update!(price: price, amount: holding.qty * price)
          results[:updated] << {
            ticker: security.ticker,
            account: holding.account.name,
            old_price: old_price.to_f,
            new_price: price.to_f
          }
        end

        # After price update, recalculate account cash
        # Price changes affect holdings_value but NOT cash
        # However, the total account value changes (market gain/loss)
      rescue => e
        results[:errors] << { ticker: security.ticker, error: e.message }
      end
    end

    render json: { status: "ok", results: results }
  end

  private

    def set_account
      @account = current_resource_owner.family.accounts.find(params[:account_id])
    end

    def ensure_read_scope
      authorize_scope!(:read)
    end

    def ensure_read_write_scope
      authorize_scope!(:read_write)
    end

    # Sum of latest holding amounts for an account
    def current_holdings_value(account)
      account.holdings
        .select("DISTINCT ON (security_id) *")
        .order("security_id, date DESC")
        .sum(:amount)
    end

    def account_state_json(account)
      holdings_value = current_holdings_value(account)
      cash = account.balance - holdings_value

      {
        id: account.id,
        name: account.name,
        total_balance: account.balance.to_f,
        holdings_value: holdings_value.to_f,
        cash: cash.to_f,
        currency: account.currency
      }
    end

    def fetch_current_price(ticker)
      result = `python3 -c "import yfinance as yf; t = yf.Ticker('#{ticker}'); h = t.history(period='5d'); print(h['Close'].iloc[-1] if not h.empty else '')" 2>/dev/null`.strip
      result.present? ? result.to_d : nil
    rescue
      nil
    end

    def holding_json(holding)
      {
        id: holding.id,
        account_id: holding.account_id,
        account_name: holding.account.name,
        security: {
          id: holding.security.id,
          ticker: holding.security.ticker,
          name: holding.security.name
        },
        qty: holding.qty.to_f,
        price: holding.price.to_f,
        amount: holding.amount.to_f,
        weight: holding.weight,
        source: holding.source,
        date: holding.date.iso8601,
        currency: holding.currency
      }
    end
end
