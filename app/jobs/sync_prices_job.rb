# Syncs security prices and exchange rates from yfinance
# Runs daily after market close
class SyncPricesJob < ApplicationJob
  queue_as :default

  def perform
    Rails.logger.info "Starting price and exchange rate sync..."

    sync_security_prices
    sync_exchange_rates

    Rails.logger.info "Price sync completed"
  end

  private

    def sync_security_prices
      # Get all securities with active holdings
      securities = Security.joins(:holdings)
        .joins("INNER JOIN accounts ON accounts.id = holdings.account_id")
        .where(accounts: { status: "active" })
        .where("holdings.qty > 0")
        .distinct

      Rails.logger.info "Syncing prices for #{securities.count} securities"

      securities.each do |security|
        sync_single_security(security)
      end
    end

    def sync_single_security(security)
      yf_ticker = resolve_yf_ticker(security)
      return unless yf_ticker

      price = fetch_yf_price(yf_ticker)
      return unless price

      # Store the price
      currency = detect_currency(security)
      Security::Price.find_or_create_by!(
        security: security,
        date: Date.current,
        currency: currency
      ) do |sp|
        sp.price = price
      end

      # Update all current holdings for this security
      holdings = Holding.where(security: security, date: Date.current, source: "manual")
      holdings.each do |holding|
        holding.update!(price: price, amount: holding.qty * price)
      end

      Rails.logger.info "  #{security.ticker}: $#{price}"
    rescue => e
      Rails.logger.error "  Error syncing #{security.ticker}: #{e.message}"
    end

    def sync_exchange_rates
      # Get all currency pairs needed by the family
      currencies = Account.active.distinct.pluck(:currency).compact
      base_currency = Family.first&.currency || "USD"

      pairs = currencies.reject { |c| c == base_currency }.map { |c| [ c, base_currency ] }

      Rails.logger.info "Syncing #{pairs.size} exchange rate pairs"

      pairs.each do |from, to|
        sync_single_rate(from, to)
      end
    end

    def sync_single_rate(from, to)
      yf_ticker = "#{from}#{to}=X"
      rate = fetch_yf_price(yf_ticker)
      return unless rate

      ExchangeRate.find_or_create_by!(
        from_currency: from,
        to_currency: to,
        date: Date.current
      ) do |er|
        er.rate = rate
      end

      # Also store reverse
      ExchangeRate.find_or_create_by!(
        from_currency: to,
        to_currency: from,
        date: Date.current
      ) do |er|
        er.rate = 1.0 / rate
      end

      Rails.logger.info "  #{from}/#{to}: #{rate}"
    rescue => e
      Rails.logger.error "  Error syncing #{from}/#{to}: #{e.message}"
    end

    def fetch_yf_price(ticker)
      cmd = "python3 -c \"import yfinance as yf; t = yf.Ticker('#{ticker}'); h = t.history(period='5d'); print(h['Close'].iloc[-1] if not h.empty else '')\" 2>/dev/null"
      result = `#{cmd}`.strip
      result.present? ? result.to_d : nil
    end

    def resolve_yf_ticker(security)
      ticker = security.ticker

      # Already in yfinance format (contains . or =)
      return ticker if ticker.include?(".") || ticker.include?("=")

      # Map exchange MIC to yfinance suffix
      mic = security.exchange_operating_mic
      case mic
      when "XHKG"
        "#{ticker}.HK"
      when "XTKS", "XJPX"
        "#{ticker}.T"
      when "XSHG"
        "#{ticker}.SS"
      when "XSHE"
        "#{ticker}.SZ"
      when "XLON"
        "#{ticker}.L"
      else
        ticker # Default to US format
      end
    end

    def detect_currency(security)
      # Try to detect from holdings or default to USD
      holding = Holding.where(security: security).first
      holding&.currency || "USD"
    end
end
