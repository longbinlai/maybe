# frozen_string_literal: true

class Api::V1::HoldingsController < Api::V1::BaseController
  include Pagy::Backend

  before_action :ensure_read_scope

  def index
    family = current_resource_owner.family

    # Get current holdings across all investment accounts
    holdings_query = family.holdings
      .joins(:account)
      .where(accounts: { status: "active" })
      .where("holdings.qty > 0")

    # Filter by account if specified
    if params[:account_id].present?
      holdings_query = holdings_query.where(account_id: params[:account_id])
    end

    # Get latest holding per security per account
    holdings_query = holdings_query
      .select("DISTINCT ON (holdings.account_id, holdings.security_id) holdings.*")
      .order("holdings.account_id, holdings.security_id, holdings.date DESC")

    # Sort by amount descending (largest positions first)
    @holdings = holdings_query.sort_by { |h| -(h.amount || 0) }

    # Calculate family-wide portfolio totals
    @total_value = @holdings.sum(&:amount)
    @family_currency = family.currency

    render :index
  rescue => e
    Rails.logger.error "HoldingsController error: #{e.message}"
    render json: { error: "internal_server_error", message: e.message }, status: :internal_server_error
  end

  private

    def ensure_read_scope
      authorize_scope!(:read)
    end
end
