# frozen_string_literal: true

class Api::V1::ExchangeRatesController < Api::V1::BaseController
  before_action :ensure_read_scope

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
  rescue => e
    Rails.logger.error "ExchangeRatesController error: #{e.message}"
    render json: { error: "internal_server_error", message: e.message }, status: :internal_server_error
  end

  private

    def ensure_read_scope
      authorize_scope!(:read)
    end
end
