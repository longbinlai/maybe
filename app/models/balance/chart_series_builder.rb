class Balance::ChartSeriesBuilder
  def initialize(account_ids:, currency:, period: Period.last_30_days, interval: "1 day", favorable_direction: "up")
    @account_ids = account_ids
    @currency = currency
    @period = period
    @interval = interval
    @favorable_direction = favorable_direction
  end

  def balance_series
    build_series_for(:end_balance)
  rescue => e
    Rails.logger.error "Balance series error: #{e.message} for accounts #{@account_ids}"
    raise
  end

  def cash_balance_series
    build_series_for(:end_cash_balance)
  rescue => e
    Rails.logger.error "Cash balance series error: #{e.message} for accounts #{@account_ids}"
    raise
  end

  def holdings_balance_series
    build_series_for(:end_holdings_balance)
  rescue => e
    Rails.logger.error "Holdings balance series error: #{e.message} for accounts #{@account_ids}"
    raise
  end

  private
    attr_reader :account_ids, :currency, :period, :favorable_direction

    def interval
      @interval || period.interval
    end

    def build_series_for(column)
      values = query_data.map do |datum|
        # Map column names to their start equivalents
        previous_column = case column
        when :end_balance then :start_balance
        when :end_cash_balance then :start_cash_balance
        when :end_holdings_balance then :start_holdings_balance
        end

        Series::Value.new(
          date: datum.date,
          date_formatted: I18n.l(datum.date, format: :long),
          value: Money.new(datum.send(column), currency),
          trend: Trend.new(
            current: Money.new(datum.send(column), currency),
            previous: Money.new(datum.send(previous_column), currency),
            favorable_direction: favorable_direction
          )
        )
      end

      Series.new(
        start_date: period.start_date,
        end_date: period.end_date,
        interval: interval,
        values: values,
        favorable_direction: favorable_direction
      )
    end

    def query_data
      @query_data ||= Balance.find_by_sql([
        query,
        {
          account_ids: account_ids,
          target_currency: currency,
          start_date: period.start_date,
          end_date: period.end_date,
          interval: interval,
          sign_multiplier: sign_multiplier
        }
      ])
    rescue => e
      Rails.logger.error "Query data error: #{e.message} for accounts #{account_ids}, period #{period.start_date} to #{period.end_date}"
      raise
    end

    # Build a SQL CASE expression that maps each account currency to the
    # built-in fallback rate for converting to the target currency. This
    # ensures that when there is no entry in exchange_rates for a given
    # account/date, we use the configured fallback (from
    # config/currency_fallbacks.yml via Money.built_in_rate_fallback) rather
    # than defaulting to 1.0 which incorrectly skews chart values.
    def fallback_case_sql
      currencies = Account.where(id: account_ids).distinct.pluck(:currency)

      return '1' if currencies.blank?

      cases = currencies.map do |cur|
        # Use built_in_rate_fallback which returns a BigDecimal
        rate = Money.built_in_rate_fallback(cur, currency) || 1
        "WHEN '#{cur}' THEN #{rate.to_f}"
      end.join(" ")

      "(CASE accounts.currency #{cases} ELSE 1 END)"
    end

    # Since the query aggregates the *net* of assets - liabilities, this means that if we're looking at
    # a single liability account, we'll get a negative set of values.  This is not what the user expects
    # to see.  When favorable direction is "down" (i.e. liability, decrease is "good"), we need to invert
    # the values by multiplying by -1.
    def sign_multiplier
      favorable_direction == "down" ? -1 : 1
    end

    def query
      <<~SQL
        WITH dates AS (
          SELECT generate_series(DATE :start_date, DATE :end_date, :interval::interval)::date AS date
          UNION DISTINCT
          SELECT :end_date::date  -- Ensure end date is included
        )
        SELECT
          d.date,
          -- Use flows_factor: already handles asset (+1) vs liability (-1)
          COALESCE(SUM(last_bal.end_balance * last_bal.flows_factor * COALESCE(er.rate, #{fallback_case_sql}) * :sign_multiplier::integer), 0) AS end_balance,
          COALESCE(SUM(last_bal.end_cash_balance * last_bal.flows_factor * COALESCE(er.rate, #{fallback_case_sql}) * :sign_multiplier::integer), 0) AS end_cash_balance,
          -- Holdings only for assets (flows_factor = 1)
          COALESCE(SUM(
            CASE WHEN last_bal.flows_factor = 1
              THEN last_bal.end_non_cash_balance
              ELSE 0
            END * COALESCE(er.rate, #{fallback_case_sql}) * :sign_multiplier::integer
          ), 0) AS end_holdings_balance,
          -- Previous balances
          COALESCE(SUM(last_bal.start_balance * last_bal.flows_factor * COALESCE(er.rate, #{fallback_case_sql}) * :sign_multiplier::integer), 0) AS start_balance,
          COALESCE(SUM(last_bal.start_cash_balance * last_bal.flows_factor * COALESCE(er.rate, #{fallback_case_sql}) * :sign_multiplier::integer), 0) AS start_cash_balance,
          COALESCE(SUM(
            CASE WHEN last_bal.flows_factor = 1
              THEN last_bal.start_non_cash_balance
              ELSE 0
            END * COALESCE(er.rate, #{fallback_case_sql}) * :sign_multiplier::integer
          ), 0) AS start_holdings_balance
        FROM dates d
        CROSS JOIN accounts
        LEFT JOIN LATERAL (
          SELECT b.end_balance,
                 b.end_cash_balance,
                 b.end_non_cash_balance,
                 b.start_balance,
                 b.start_cash_balance,
                 b.start_non_cash_balance,
                 b.flows_factor
          FROM balances b
          WHERE b.account_id = accounts.id
            AND b.date <= d.date
          ORDER BY b.date DESC
          LIMIT 1
        ) last_bal ON TRUE
        LEFT JOIN LATERAL (
          SELECT er.rate
          FROM exchange_rates er
          WHERE er.from_currency = accounts.currency
            AND er.to_currency = :target_currency
            AND er.date <= d.date
          ORDER BY er.date DESC
          LIMIT 1
        ) er ON TRUE
        WHERE accounts.id = ANY(array[:account_ids]::uuid[])
        GROUP BY d.date
        ORDER BY d.date
      SQL
    end
end
