module ExchangeRate::Provided
  extend ActiveSupport::Concern

  class_methods do
    def provider
      registry = Provider::Registry.for_concept(:exchange_rates)
      registry.get_provider(:synth)
    end

    # Find latest available exchange rate in database with permanent caching (NO external API calls)
    def find_latest_rate(from:, to:)
      cache_key = "exchange_rate_latest_#{from}_#{to}"
      
      # Use Rails cache without expiration - only update when new rates are added
      Rails.cache.fetch(cache_key) do
        where(from_currency: from, to_currency: to)
          .order(date: :desc)
          .first
      end
    end

    # Update cache with new rate (used when new rates are added)
    def update_rate_cache(from:, to:, rate:)
      cache_key = "exchange_rate_latest_#{from}_#{to}"
      Rails.cache.write(cache_key, rate)
    end

    # Clear cache for a specific currency pair
    def clear_rate_cache(from:, to:)
      cache_key = "exchange_rate_latest_#{from}_#{to}"
      Rails.cache.delete(cache_key)
    end

    def find_or_fetch_rate(from:, to:, date: Date.current, cache: true)
      rate = find_by(from_currency: from, to_currency: to, date: date)
      return rate if rate.present?

      return nil unless provider.present? # No provider configured (some self-hosted apps)

      response = provider.fetch_exchange_rate(from: from, to: to, date: date)

      return nil unless response.success? # Provider error

      rate = response.data
      if cache
        new_rate = ExchangeRate.find_or_create_by!(
          from_currency: rate.from,
          to_currency: rate.to,
          date: rate.date,
          rate: rate.rate
        )
        
        # Check if this new rate is newer than cached rate and update cache if needed
        cached_rate = Rails.cache.read("exchange_rate_latest_#{rate.from}_#{rate.to}")
        if cached_rate.nil? || cached_rate.date < new_rate.date
          update_rate_cache(from: rate.from, to: rate.to, rate: new_rate)
        end
        
        new_rate
      else
        rate
      end
    end

    # @return [Integer] The number of exchange rates synced
    def import_provider_rates(from:, to:, start_date:, end_date:, clear_cache: false)
      unless provider.present?
        Rails.logger.warn("No provider configured for ExchangeRate.import_provider_rates")
        return 0
      end

      ExchangeRate::Importer.new(
        exchange_rate_provider: provider,
        from: from,
        to: to,
        start_date: start_date,
        end_date: end_date,
        clear_cache: clear_cache
      ).import_provider_rates
    end
  end
end
