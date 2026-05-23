class Assistant::Function::GetPortfolioAllocation < Assistant::Function
  class << self
    def name
      "get_portfolio_allocation"
    end

    def description
      <<~INSTRUCTIONS
        Use this to get the user's overall portfolio allocation broken down by asset class (account type).

        This shows how the user's total wealth is distributed across:
        - Cash/depository accounts
        - Investment accounts (stocks, bonds, funds)
        - Real estate (property)
        - Crypto
        - Vehicles
        - Other assets
        - Liabilities (loans, credit cards)

        This is great for answering questions like:
        - How diversified is my portfolio?
        - What percentage is in stocks vs bonds vs cash?
        - Is my allocation balanced?
      INSTRUCTIONS
    end
  end

  def call(params = {})
    balance_sheet = family.balance_sheet
    net_worth = balance_sheet.net_worth

    allocation = balance_sheet.account_groups.map do |group|
      {
        type: group.key,
        name: group.name,
        classification: group.classification,
        total: group.total,
        total_formatted: group.total_money.format,
        weight_of_classification: group.weight.round(1),
        weight_of_net_worth: net_worth.zero? ? 0 : ((group.total / net_worth.to_f) * 100).round(1)
      }
    end

    # Investment account breakdown (holdings by security)
    investment_accounts = family.accounts.visible.where(accountable_type: "Investment")
    investment_detail = investment_accounts.flat_map do |account|
      current = account.current_holdings
      total = current.sum(&:amount)
      current.map do |holding|
        {
          account: account.name,
          ticker: holding.security.ticker,
          name: holding.security.name,
          value: holding.amount,
          weight: total.zero? ? 0 : ((holding.amount / total) * 100).round(1)
        }
      end
    end

    {
      as_of_date: Date.current,
      currency: family.currency,
      net_worth: net_worth,
      net_worth_formatted: balance_sheet.net_worth_money.format,
      total_assets: balance_sheet.assets.total,
      total_liabilities: balance_sheet.liabilities.total,
      allocation_by_type: allocation,
      investment_holdings: investment_detail
    }
  end
end
