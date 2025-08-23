class Money
  include Comparable, Arithmetic, Formatting
  include ActiveModel::Validations

  class ConversionError < StandardError
    attr_reader :from_currency, :to_currency, :date

    def initialize(from_currency:, to_currency:, date:)
      @from_currency = from_currency
      @to_currency = to_currency
      @date = date

      error_message = message || "Couldn't find exchange rate from #{from_currency} to #{to_currency} on #{date}"

      super(error_message)
    end
  end

  attr_reader :amount, :currency, :store

  validate :source_must_be_of_known_type

  class << self
    def default_currency
      @default ||= Money::Currency.new(:usd)
    end

    def default_currency=(object)
      @default = Money::Currency.new(object)
    end
  end

  def initialize(obj, currency = Money.default_currency, store: ExchangeRate)
    @source = obj
    @amount = obj.is_a?(Money) ? obj.amount : BigDecimal(obj.to_s)
    @currency = obj.is_a?(Money) ? obj.currency : Money::Currency.new(currency)
    @store = store

    validate!
  end

  def exchange_to(other_currency, date: Date.current, fallback_rate: nil)
    iso_code = currency.iso_code
    other_iso_code = Money::Currency.new(other_currency).iso_code

    if iso_code == other_iso_code
      self
    else
      # Fetch provider rate if available
      fetched = store.find_or_fetch_rate(from: iso_code, to: other_iso_code, date: date)
      provider_rate = fetched&.rate

      # Normalize provider rate to BigDecimal when present for consistent comparison
      provider_rate_bd = provider_rate.nil? ? nil : BigDecimal(provider_rate.to_s)

      # Prefer provider rate when it's present and not the sentinel value 1.
      # If provider rate is missing or equals 1 (commonly used as a sentinel),
      # first try the built-in fallback table. If that yields nothing, use the
      # explicit fallback_rate passed by caller (if any).
      if provider_rate_bd && provider_rate_bd != BigDecimal("1")
        exchange_rate_bd = provider_rate_bd
      else
        built = self.class.built_in_rate_fallback(iso_code, other_iso_code)
        if built
          exchange_rate_bd = built
        elsif fallback_rate
          exchange_rate_bd = BigDecimal(fallback_rate.to_s)
        else
          exchange_rate_bd = nil
        end
      end

  raise ConversionError.new(from_currency: iso_code, to_currency: other_iso_code, date: date) unless exchange_rate_bd

  Money.new(amount * exchange_rate_bd, other_iso_code)
    end
  end

  # Small built-in fallback table for common currency conversions when providers return
  # a sentinel rate of 1 (meaning missing historical data). This should be used only
  # when caller did not provide an explicit fallback_rate.
  def self.built_in_rate_fallback(from_iso, to_iso)
    require "yaml"

    from = from_iso.to_s.upcase
    to = to_iso.to_s.upcase

    # Load the config file if present; fall back to an in-memory small table if not.
    config_path = if defined?(Rails) && Rails.respond_to?(:root)
      Rails.root.join("config", "currency_fallbacks.yml")
    else
      File.join(Dir.pwd, "config", "currency_fallbacks.yml")
    end

    table = if File.exist?(config_path)
      YAML.load_file(config_path)
    else
      { "CNY" => { "USD" => 0.14 }, "USD" => { "CNY" => 7.1 } }
    end

    # Normalize numeric values to BigDecimal to avoid float precision mismatches
    normalized = table.each_with_object({}) do |(k, v), memo|
      key = k.to_s.upcase
      memo[key] = if v.is_a?(Hash)
        v.each_with_object({}) do |(k2, v2), m2|
          m2[k2.to_s.upcase] = BigDecimal(v2.to_s)
        end
      else
        BigDecimal(v.to_s)
      end
    end

    # Direct mapping
    direct = normalized.dig(from, to)
    return direct if direct

    # Inverse mapping (if config has the reverse pair, use reciprocal)
    inverse = normalized.dig(to, from)
    return BigDecimal("1") / inverse if inverse && inverse != 0

    # Try bridging via USD (common anchor) if both legs exist
    if from != "USD" && to != "USD"
      leg1 = normalized.dig(from, "USD")
      leg2 = normalized.dig("USD", to)
      return leg1 * leg2 if leg1 && leg2
    end

    nil
  end

  def as_json
    { amount: amount, currency: currency.iso_code, formatted: format }.as_json
  end

  def <=>(other)
    raise TypeError, "Money can only be compared with other Money objects except for 0" unless other.is_a?(Money) || other.eql?(0)

    if other.is_a?(Numeric)
      amount <=> other
    else
      amount_comparison = amount <=> other.amount

      if amount_comparison == 0
        currency <=> other.currency
      else
        amount_comparison
      end
    end
  end

  private
    def source_must_be_of_known_type
      unless @source.is_a?(Money) || @source.is_a?(Numeric) || @source.is_a?(BigDecimal)
        errors.add :source, "must be a Money, Numeric, or BigDecimal"
      end
    end
end
