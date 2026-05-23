# frozen_string_literal: true

class Api::V1::ExchangeRatesController < Api::V1::BaseController
  before_action :ensure_read_scope, only: [ :index ]
  before_action :ensure_read_write_scope, only: [ :create ]

  def index
    family = current_resource_owner.family
    from_currency = params[:from] || family.currency
    to_currency = params[:to]

    if to_currency.blank?
      # Return all recent exchange rates for the family's currency
      @rates = ExchangeRate
        .where(to_currency: family.currency)
        .where(date: 30.days.ago.to_date..Date.current)
        .order(:from_currency, date: :desc)
        .select("DISTINCT ON (from_currency) *")
    else
      # Return specific currency pair history
      start_date = params[:start_date].present? ? Date.parse(params[:start_date]) : 90.days.ago.to_date
      end_date = params[:end_date].present? ? Date.parse(params[:end_date]) : Date.current

      @rates = ExchangeRate
        .where(from_currency: from_currency, to_currency: to_currency)
        .where(date: start_date..end_date)
        .order(date: :desc)
    end

    render :index
  end

  # POST /api/v1/exchange_rates — create or update a rate
  def create
    from_currency = params[:from_currency]
    to_currency = params[:to_currency]
    rate = params[:rate].to_d
    date = params[:date] || Date.current

    # Create or update the rate
    exchange_rate = ExchangeRate.find_or_initialize_by(
      from_currency: from_currency,
      to_currency: to_currency,
      date: date
    )
    exchange_rate.rate = rate

    if exchange_rate.save
      # Also create the reverse rate
      reverse_rate = ExchangeRate.find_or_initialize_by(
        from_currency: to_currency,
        to_currency: from_currency,
        date: date
      )
      reverse_rate.rate = 1.0 / rate
      reverse_rate.save

      render json: {
        status: "ok",
        rate: {
          from_currency: from_currency,
          to_currency: to_currency,
          rate: rate.to_f,
          date: date.iso8601,
          reverse_rate: (1.0 / rate).to_f
        }
      }, status: :created
    else
      render json: { error: exchange_rate.errors.full_messages.join(", ") }, status: :unprocessable_entity
    end
  end

  private

    def ensure_read_scope
      authorize_scope!(:read)
    end

    def ensure_read_write_scope
      authorize_scope!(:read_write)
    end
end
