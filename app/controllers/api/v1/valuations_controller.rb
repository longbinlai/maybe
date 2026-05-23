class Api::V1::ValuationsController < Api::V1::BaseController
  include Pagy::Backend

  before_action :ensure_read_write_scope, only: [ :create, :update ]
  before_action :ensure_read_scope, only: [ :index ]
  before_action :set_account

  def index
    entries = @account.entries.where(entryable_type: "Valuation").order(date: :desc)
    @pagy, @valuations = pagy(entries, page: safe_page_param, limit: safe_per_page_param)
    @per_page = safe_per_page_param

    render :index
  end

  def create
    balance = params[:balance]
    date = params[:date] || Date.current

    if balance.blank?
      return render json: { error: "balance is required" }, status: :unprocessable_entity
    end

    result = @account.create_reconciliation(balance: balance.to_d, date: Date.parse(date.to_s))

    if result.success?
      old_bal = result.old_balance&.to_f || 0.0
      new_bal = result.new_balance&.to_f || 0.0

      render json: {
        status: "ok",
        account: {
          id: @account.id,
          name: @account.name,
          balance: @account.balance.to_f,
          balance_formatted: @account.balance_money.format
        },
        old_balance: old_bal,
        new_balance: new_bal,
        delta: new_bal - old_bal
      }, status: :created
    else
      render json: { error: result.error_message }, status: :unprocessable_entity
    end
  end

  def update
    entry = @account.entries.find(params[:id])
    balance = params[:balance] || entry.amount
    date = params[:date] || entry.date

    result = @account.update_reconciliation(entry, balance: balance.to_d, date: Date.parse(date.to_s))

    if result.success?
      old_bal = result.old_balance&.to_f || 0.0
      new_bal = result.new_balance&.to_f || 0.0

      render json: {
        status: "ok",
        account: {
          id: @account.id,
          name: @account.name,
          balance: @account.balance.to_f,
          balance_formatted: @account.balance_money.format
        },
        old_balance: old_bal,
        new_balance: new_bal
      }
    else
      render json: { error: result.error_message }, status: :unprocessable_entity
    end
  end

  private

    def set_account
      @account = current_resource_owner.family.accounts.find(params[:account_id])
    end

    def ensure_read_write_scope
      authorize_scope!(:read_write)
    end

    def ensure_read_scope
      authorize_scope!(:read)
    end

    def safe_page_param
      page = params[:page].to_i
      page > 0 ? page : 1
    end

    def safe_per_page_param
      per_page = params[:per_page].to_i
      per_page.between?(1, 100) ? per_page : 25
    end
end
