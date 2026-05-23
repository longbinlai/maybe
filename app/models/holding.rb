class Holding < ApplicationRecord
  include Monetizable, Gapfillable

  monetize :amount

  belongs_to :account
  belongs_to :security

  validates :qty, :currency, :date, :price, :amount, presence: true
  validates :qty, :price, :amount, numericality: { greater_than_or_equal_to: 0 }

  scope :chronological, -> { order(:date) }
  scope :for, ->(security) { where(security_id: security).order(:date) }
  scope :manual, -> { where(source: 'manual') }
  scope :trade, -> { where(source: 'trade') }

  delegate :ticker, to: :security

  def name
    security.name || ticker
  end

  def weight
    return nil unless amount
    return 0 if amount.zero?

    account.balance.zero? ? 1 : amount / account.balance * 100
  end

  # Basic approximation of cost-basis
  def avg_cost
    avg_cost = account.trades
      .with_entry
      .joins(ActiveRecord::Base.sanitize_sql_array([
        "LEFT JOIN exchange_rates ON (
          exchange_rates.date = entries.date AND
          exchange_rates.from_currency = trades.currency AND
          exchange_rates.to_currency = ?
        )", account.currency
      ]))
      .where(security_id: security.id)
      .where("trades.qty > 0 AND entries.date <= ?", date)
      .average("trades.price * COALESCE(exchange_rates.rate, 1)")

    Money.new(avg_cost || price, currency)
  end

  def trend
    @trend ||= calculate_trend
  end

  def trades
    account.entries.where(entryable: account.trades.where(security: security)).reverse_chronological
  end

  def destroy_holding_and_entries!
    transaction do
      account.entries.where(entryable: account.trades.where(security: security)).destroy_all
      destroy
    end

    account.sync_later
  end

  def is_manual?
    source == 'manual'
  end

  def update_price!(new_price)
    return unless new_price.present? && new_price > 0

    self.price = new_price
    self.amount = qty * new_price
    save!
  end

  # Update holdings value while preserving quantity
  def recalculate_amount!
    self.amount = qty * price
    save!
  end

  private
    def calculate_trend
      return nil unless amount_money

      start_amount = qty * avg_cost

      Trend.new \
        current: amount_money,
        previous: start_amount
    end
end
