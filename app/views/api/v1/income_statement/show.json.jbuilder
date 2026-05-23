# frozen_string_literal: true

family = @income_statement.family
currency = family.currency

# Build transactions scope for the period
transactions_scope = family.transactions.visible.in_period(@period)
totals = @income_statement.totals(transactions_scope: transactions_scope)

json.as_of_date Date.current
json.currency currency
json.period do
  json.start_date @period.start_date.iso8601
  json.end_date @period.end_date.iso8601
end

json.summary do
  json.total_income totals.income_money.amount.to_f.abs
  json.total_expense totals.expense_money.amount.to_f.abs
  json.net_savings (totals.income_money.amount.to_f.abs - totals.expense_money.amount.to_f.abs)
  json.transactions_count totals.transactions_count
  savings_rate = totals.income_money.amount.zero? ? 0 : ((totals.income_money.amount.to_f.abs - totals.expense_money.amount.to_f.abs) / totals.income_money.amount.to_f.abs * 100)
  json.savings_rate savings_rate.round(1)
end

json.monthly_averages do
  json.median_income @income_statement.median_income(interval: @interval)
  json.median_expense @income_statement.median_expense(interval: @interval)
end

json.expense_by_category do
  expense_total = @income_statement.expense_totals(period: @period)
  expense_total.category_totals.each do |ct|
    next if ct.category.subcategory?
    next if ct.total.zero?
    json.set! ct.category.id do
      json.name ct.category.name
      json.total ct.total.abs
      json.weight ct.weight.round(1)
    end
  end
end

json.income_by_category do
  income_total = @income_statement.income_totals(period: @period)
  income_total.category_totals.each do |ct|
    next if ct.category.subcategory?
    next if ct.total.zero?
    json.set! ct.category.id do
      json.name ct.category.name
      json.total ct.total.abs
      json.weight ct.weight.round(1)
    end
  end
end
