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

    # Filter by account
    holdings_query = holdings_query.where(account_id: params[:account_id]) if params[:account_id].present?

    # Get latest holding per security per account
    holdings_query = holdings_query
      .select("DISTINCT ON (holdings.account_id, holdings.security_id) holdings.*")
      .order("holdings.account_id, holdings.security_id, holdings.date DESC")

    @holdings = holdings_query.sort_by { |h| -(h.amount || 0) }
    @total_value = @holdings.sum(&:amount)

    render :index
  end

  # POST /api/v1/holdings
  def create
    ticker = params[:ticker]
    qty = params[:qty].to_d
    price = params[:price]&.to_d
    avg_cost = params[:avg_cost]&.to_d

    # Find or create security
    security = Security.find_or_create_by!(ticker: ticker.upcase) do |s|
      s.name = params[:name] || ticker.upcase
      s.offline = false
    end

    # Get current price from yfinance if not provided
    if price.nil? || price.zero?
      price = fetch_current_price(security.ticker)
      if price.nil?
        return render json: { error: "Could not fetch price for #{ticker}" }, status: :unprocessable_entity
      end
    end

    date = params[:date] || Date.current
    amount = qty * price

    holding = @account.holdings.find_or_initialize_by(
      security: security,
      date: date,
      currency: @account.currency
    )

    holding.assign_attributes(
      qty: qty,
      price: price,
      amount: amount,
      source: "manual"
    )

    if holding.save
      # Adjust account's total balance down by the holding amount
      # so that sync will compute: cash = (total - holdings) correctly
      new_total = @account.balance - amount
      if new_total >= 0
        @account.create_reconciliation(balance: new_total, date: date)
      end

      # Now sync to recalculate balances with holdings
      @account.sync_later

      render json: {
        status: "ok",
        holding: holding_json(holding),
        account: {
          id: @account.id,
          name: @account.name,
          balance: @account.balance.to_f,
          cash_balance: (@account.balance - @account.holdings.where(date: date).sum(:amount)).to_f
        }
      }, status: :created
    else
      render json: { error: holding.errors.full_messages.join(", ") }, status: :unprocessable_entity
    end
  end

  # PATCH /api/v1/holdings/:id
  def update
    family = current_resource_owner.family
    holding = family.holdings.find(params[:id])

    updates = {}
    updates[:qty] = params[:qty].to_d if params[:qty].present?
    updates[:price] = params[:price].to_d if params[:price].present?

    # Recalculate amount
    new_qty = updates[:qty] || holding.qty
    new_price = updates[:price] || holding.price
    updates[:amount] = new_qty * new_price

    updates[:date] = Date.parse(params[:date]) if params[:date].present?

    old_amount = holding.amount

    if holding.update(updates)
      # Adjust account balance for the change in holding amount
      new_amount = holding.reload.amount
      delta = new_amount - old_amount
      account = holding.account

      if delta != 0
        new_total = account.balance - delta
        if new_total >= 0
          account.create_reconciliation(balance: new_total, date: holding.date)
        end
      end

      account.sync_later

      render json: {
        status: "ok",
        holding: holding_json(holding.reload),
        account: {
          id: account.id,
          name: account.name,
          balance: account.balance.to_f,
          cash_balance: (account.balance - account.holdings.where(date: holding.date).sum(:amount)).to_f
        }
      }
    else
      render json: { error: holding.errors.full_messages.join(", ") }, status: :unprocessable_entity
    end
  end

  # DELETE /api/v1/holdings/:id
  def destroy
    family = current_resource_owner.family
    holding = family.holdings.find(params[:id])

    unless holding.is_manual?
      return render json: { error: "Can only delete manual holdings. Trade holdings are managed by trades." }, status: :forbidden
    end

    account = holding.account
    amount_freed = holding.amount

    holding.destroy

    # Add the holding amount back to the account balance (it becomes cash)
    new_total = account.balance + amount_freed
    account.create_reconciliation(balance: new_total, date: Date.current)
    account.sync_later

    render json: { status: "ok", message: "Holding deleted" }
  end

  # POST /api/v1/holdings/sync_prices
  def sync_prices
    family = current_resource_owner.family
    results = { updated: [], errors: [], skipped: [] }

    # Get all securities with holdings
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

        # Update security price record
        Security::Price.find_or_create_by!(
          security: security,
          date: Date.current,
          currency: "USD" # TODO: handle multiple currencies
        ) do |sp|
          sp.price = price
        end

        # Update all holdings for this security
        holdings = family.holdings.where(security: security).where(date: Date.current)
        holdings.each do |holding|
          holding.update_price!(price)
          results[:updated] << {
            ticker: security.ticker,
            account: holding.account.name,
            old_price: holding.price_was.to_f,
            new_price: price.to_f
          }
        end
      rescue => e
        results[:errors] << { ticker: security.ticker, error: e.message }
      end
    end

    # Sync accounts to recalculate balances
    family.accounts.where(accountable_type: [ "Investment", "Crypto" ]).each(&:sync_later)

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

    def fetch_current_price(ticker)
      # Use yfinance via Python subprocess
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
        currency: holding.currency,
        avg_cost: holding.avg_cost&.amount&.to_f,
        trend: holding.trend ? {
          value: holding.trend.value&.amount&.to_f,
          percent: holding.trend.percent
        } : nil
      }
    end
end
