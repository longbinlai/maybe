# frozen_string_literal: true

class Api::V1::BalanceSheetController < Api::V1::BaseController
  before_action :ensure_read_scope

  def show
    family = current_resource_owner.family
    @balance_sheet = family.balance_sheet

    # Determine period for historical data
    start_date = params[:start_date].present? ? Date.parse(params[:start_date]) : [ 5.years.ago.to_date, family.oldest_entry_date ].max
    end_date = params[:end_date].present? ? Date.parse(params[:end_date]) : Date.current
    @period = Period.custom(start_date: start_date, end_date: end_date)

    # Interval for historical data (daily, weekly, monthly)
    @interval = params[:interval] || "monthly"

    render :show
  rescue Date::Error => e
    render json: { error: "bad_request", message: "Invalid date format: #{e.message}" }, status: :bad_request
  rescue => e
    Rails.logger.error "BalanceSheetController error: #{e.message}"
    render json: { error: "internal_server_error", message: e.message }, status: :internal_server_error
  end

  private

    def ensure_read_scope
      authorize_scope!(:read)
    end
end
