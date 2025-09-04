class Settings::ExchangeRatesController < ApplicationController
  layout "settings"

  def index
    @exchange_rates = ExchangeRate.order(date: :desc, from_currency: :asc, to_currency: :asc)
                                  .limit(50)
    
    @supported_currencies = ["USD", "CNY", "EUR", "GBP", "JPY"]
    @fallback_rates = load_fallback_rates
  end

  def create
    @exchange_rate = ExchangeRate.new(exchange_rate_params)
    
    if @exchange_rate.save
      redirect_to settings_exchange_rates_path, notice: t(".success")
    else
      redirect_to settings_exchange_rates_path, alert: t(".error")
    end
  end

  def destroy
    @exchange_rate = ExchangeRate.find(params[:id])
    @exchange_rate.destroy
    redirect_to settings_exchange_rates_path, notice: t(".deleted")
  end

  def sync_current_rates
    currencies = load_supported_currencies
    success_count = 0
    error_count = 0

    currencies.each do |from_currency|
      currencies.each do |to_currency|
        next if from_currency == to_currency
        
        begin
          ExchangeRate::Provided.fetch_rate_by_date(
            from: from_currency,
            to: to_currency,
            date: Date.current
          )
          success_count += 1
        rescue => e
          error_count += 1
          Rails.logger.error "Failed to fetch rate #{from_currency} -> #{to_currency}: #{e.message}"
        end
      end
    end

    if error_count == 0
      redirect_to settings_exchange_rates_path, notice: t(".sync_success", count: success_count)
    else
      redirect_to settings_exchange_rates_path, 
                  alert: t(".sync_partial", success: success_count, errors: error_count)
    end
  end

  private

  def exchange_rate_params
    params.require(:exchange_rate).permit(:from_currency, :to_currency, :rate, :date)
  end

  def load_supported_currencies
    # 从currencies.yml加载支持的货币
    YAML.load_file(Rails.root.join('config', 'currencies.yml')).keys.map(&:upcase)
  end

  def load_fallback_rates
    # 从currency_fallbacks.yml加载后备汇率
    YAML.load_file(Rails.root.join('config', 'currency_fallbacks.yml'))
  end
end
