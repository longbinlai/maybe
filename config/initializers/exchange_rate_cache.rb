# Exchange Rate Cache Optimization
# Preload commonly used exchange rates to improve performance

Rails.application.config.after_initialize do
  # Only run in production or when explicitly enabled
  if Rails.env.production? || ENV['PRELOAD_EXCHANGE_RATES'] == 'true'
    Rails.logger.info "Preloading exchange rate cache..."
    
    # Get all unique currency pairs from the database
    begin
      if defined?(ExchangeRate) && ExchangeRate.table_exists?
        currency_pairs = ExchangeRate.distinct.pluck(:from_currency, :to_currency).uniq
        
        # Preload the latest rate for each pair into cache
        currency_pairs.each do |from_currency, to_currency|
          ExchangeRate.find_latest_rate(from: from_currency, to: to_currency)
        end
        
        Rails.logger.info "Preloaded #{currency_pairs.count} exchange rate pairs into cache"
      end
    rescue => e
      Rails.logger.warn "Could not preload exchange rates: #{e.message}"
    end
  end
end
