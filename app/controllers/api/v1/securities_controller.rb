# frozen_string_literal: true

class Api::V1::SecuritiesController < Api::V1::BaseController
  include Pagy::Backend

  before_action :ensure_read_scope

  def index
    family = current_resource_owner.family

    # Only return securities that the family actually holds or has traded
    securities_query = Security.joins(:trades)
      .joins("INNER JOIN entries ON entries.entryable_id = trades.id AND entries.entryable_type = 'Trade'")
      .joins("INNER JOIN accounts ON accounts.id = entries.account_id")
      .where(accounts: { family_id: family.id })
      .distinct

    # Search by ticker or name
    if params[:search].present?
      search_term = "%#{params[:search]}%"
      securities_query = securities_query.where("securities.ticker ILIKE ? OR securities.name ILIKE ?", search_term, search_term)
    end

    @pagy, @securities = pagy(securities_query, page: safe_page_param, limit: safe_per_page_param)
    @per_page = safe_per_page_param

    render :index
  rescue => e
    Rails.logger.error "SecuritiesController error: #{e.message}"
    render json: { error: "internal_server_error", message: e.message }, status: :internal_server_error
  end

  def show
    family = current_resource_owner.family
    @security = Security.find(params[:id])

    # Get price history
    start_date = params[:start_date].present? ? Date.parse(params[:start_date]) : 1.year.ago.to_date
    end_date = params[:end_date].present? ? Date.parse(params[:end_date]) : Date.current

    @prices = @security.prices.where(date: start_date..end_date).order(:date)

    render :show
  rescue ActiveRecord::RecordNotFound
    render json: { error: "not_found", message: "Security not found" }, status: :not_found
  rescue => e
    Rails.logger.error "SecuritiesController#show error: #{e.message}"
    render json: { error: "internal_server_error", message: e.message }, status: :internal_server_error
  end

  private

    def ensure_read_scope
      authorize_scope!(:read)
    end

    def safe_page_param
      page = params[:page].to_i
      page > 0 ? page : 1
    end

    def safe_per_page_param
      per_page = params[:per_page].to_i
      case per_page
      when 1..100 then per_page
      else 25
      end
    end
end
