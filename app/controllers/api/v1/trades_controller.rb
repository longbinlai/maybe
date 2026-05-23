# frozen_string_literal: true

class Api::V1::TradesController < Api::V1::BaseController
  include Pagy::Backend

  before_action :ensure_read_scope

  def index
    family = current_resource_owner.family
    trades_query = family.trades
      .joins(:entry)
      .includes(:security, entry: :account)
      .reverse_chronological

    # Filter by account
    if params[:account_id].present?
      trades_query = trades_query.joins(:entry).where(entries: { account_id: params[:account_id] })
    end

    # Filter by security
    if params[:security_id].present?
      trades_query = trades_query.where(security_id: params[:security_id])
    end

    # Filter by date range
    if params[:start_date].present?
      trades_query = trades_query.joins(:entry).where("entries.date >= ?", Date.parse(params[:start_date]))
    end
    if params[:end_date].present?
      trades_query = trades_query.joins(:entry).where("entries.date <= ?", Date.parse(params[:end_date]))
    end

    # Filter by type (buy/sell)
    if params[:type].present?
      case params[:type].downcase
      when "buy"
        trades_query = trades_query.where("trades.qty > 0")
      when "sell"
        trades_query = trades_query.where("trades.qty < 0")
      end
    end

    @pagy, @trades = pagy(trades_query, page: safe_page_param, limit: safe_per_page_param)
    @per_page = safe_per_page_param

    render :index
  rescue => e
    Rails.logger.error "TradesController error: #{e.message}"
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
