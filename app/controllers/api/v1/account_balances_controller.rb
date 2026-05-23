# frozen_string_literal: true

class Api::V1::AccountBalancesController < Api::V1::BaseController
  before_action :ensure_read_scope
  before_action :set_account

  def index
    start_date = params[:start_date].present? ? Date.parse(params[:start_date]) : [ @account.start_date, 5.years.ago.to_date ].max
    end_date = params[:end_date].present? ? Date.parse(params[:end_date]) : Date.current
    interval = params[:interval] || "1 month"

    period = Period.custom(start_date: start_date, end_date: end_date)

    @balance_series = @account.balance_series(period: period, interval: interval)
    @cash_series = @account.balance_series(period: period, view: :cash_balance, interval: interval) if @account.balance_type == :investment

    render :index
  rescue => e
    Rails.logger.error "AccountBalancesController error: #{e.message}"
    render json: { error: "internal_server_error", message: e.message }, status: :internal_server_error
  end

  private

    def ensure_read_scope
      authorize_scope!(:read)
    end

    def set_account
      family = current_resource_owner.family
      @account = family.accounts.find(params[:account_id])
    rescue ActiveRecord::RecordNotFound
      render json: { error: "not_found", message: "Account not found" }, status: :not_found
    end
end
