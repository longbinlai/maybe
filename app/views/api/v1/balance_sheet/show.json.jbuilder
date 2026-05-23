# frozen_string_literal: true

family = @balance_sheet.family
period = @period

json.as_of_date Date.current
json.currency @balance_sheet.currency

json.net_worth do
  json.current @balance_sheet.net_worth
  json.current_formatted @balance_sheet.net_worth_money.format
  series = @balance_sheet.net_worth_series(period: period)
  json.history series.values.map { |v| { date: v.date.iso8601, value: v.value.amount.to_f } }
end

json.assets do
  json.current @balance_sheet.assets.total
  json.current_formatted @balance_sheet.assets.total_money.format
  json.by_type @balance_sheet.assets.account_groups.map { |g|
    { type: g.key, name: g.name, total: g.total, weight: g.weight.round(1) }
  }
end

json.liabilities do
  json.current @balance_sheet.liabilities.total
  json.current_formatted @balance_sheet.liabilities.total_money.format
  json.by_type @balance_sheet.liabilities.account_groups.map { |g|
    { type: g.key, name: g.name, total: g.total, weight: g.weight.round(1) }
  }
end

json.insights do
  assets = @balance_sheet.assets.total
  liabilities = @balance_sheet.liabilities.total
  ratio = liabilities.zero? ? 0 : (liabilities / assets.to_f)
  json.debt_to_asset_ratio (ratio * 100).round(1)
end
