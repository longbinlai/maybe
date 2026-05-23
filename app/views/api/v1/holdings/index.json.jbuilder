# frozen_string_literal: true

json.as_of_date Date.current
json.currency @family_currency
json.total_portfolio_value @total_value

json.holdings @holdings do |holding|
  json.id holding.id
  json.account_id holding.account_id
  json.account_name holding.account.name
  json.security do
    json.id holding.security.id
    json.ticker holding.security.ticker
    json.name holding.security.name
    json.exchange holding.security.exchange_operating_mic
    json.country_code holding.security.country_code
    json.logo_url holding.security.logo_url
  end
  json.quantity holding.qty
  json.price holding.price
  json.market_value holding.amount
  json.weight @total_value.zero? ? 0 : ((holding.amount / @total_value) * 100).round(2)
  json.avg_cost holding.avg_cost.amount.to_f
  json.date holding.date.iso8601
  json.currency holding.currency
  json.source holding.source

  # Trend (unrealized gain/loss)
  trend = holding.trend
  if trend
    json.trend do
      json.value trend.value&.amount&.to_f
      json.percent trend.percent&.round(2)
      json.direction trend.color
    end
  end
end
