# frozen_string_literal: true

json.account do
  json.id @account.id
  json.name @account.name
  json.currency @account.currency
  json.classification @account.classification
  json.account_type @account.accountable_type.underscore
  json.current_balance @account.balance
  json.current_balance_formatted @account.balance_money.format
  json.cash_balance @account.cash_balance if @account.balance_type == :investment
end

json.balances @balance_series.values.map { |v|
  {
    date: v.date.iso8601,
    value: v.value.amount.to_f
  }
}

if @cash_series
  json.cash_balances @cash_series.values.map { |v|
    {
      date: v.date.iso8601,
      value: v.value.amount.to_f
    }
  }
end
