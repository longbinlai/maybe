class Assistant::Function::GetHoldings < Assistant::Function
  class << self
    def name
      "get_holdings"
    end

    def description
      <<~INSTRUCTIONS
        Use this to get the user's current investment holdings across all accounts.

        This is great for answering questions like:
        - What stocks/securities do I own?
        - What is my portfolio allocation?
        - What are my largest positions?
        - What is my unrealized gain/loss?
      INSTRUCTIONS
    end
  end

  def call(params = {})
    holdings = family.holdings
      .joins(:account)
      .where(accounts: { status: "active" })
      .where("holdings.qty > 0")
      .select("DISTINCT ON (holdings.account_id, holdings.security_id) holdings.*")
      .order("holdings.account_id, holdings.security_id, holdings.date DESC")
      .sort_by { |h| -(h.amount || 0) }

    total_value = holdings.sum(&:amount)

    {
      as_of_date: Date.current,
      currency: family.currency,
      total_portfolio_value: total_value,
      holdings: holdings.map do |holding|
        {
          ticker: holding.security.ticker,
          name: holding.security.name || holding.security.ticker,
          account: holding.account.name,
          quantity: holding.qty,
          price: holding.price,
          market_value: holding.amount,
          weight_percent: total_value.zero? ? 0 : ((holding.amount / total_value) * 100).round(2),
          avg_cost: holding.avg_cost.amount.to_f,
          unrealized_gain_loss: holding.trend&.value&.amount&.to_f,
          unrealized_gain_loss_percent: holding.trend&.percent&.round(2)
        }
      end
    }
  end
end
