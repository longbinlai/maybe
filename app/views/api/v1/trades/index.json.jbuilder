# frozen_string_literal: true

json.trades @trades do |trade|
  json.id trade.id
  json.entry_id trade.entry_id
  json.date trade.entry.date.iso8601
  json.account do
    json.id trade.entry.account.id
    json.name trade.entry.account.name
  end
  json.security do
    json.id trade.security.id
    json.ticker trade.security.ticker
    json.name trade.security.name
  end
  json.type trade.qty.positive? ? "buy" : "sell"
  json.quantity trade.qty.abs
  json.price trade.price
  json.amount trade.entry.amount.to_f
  json.currency trade.currency
end

json.pagination do
  json.page @pagy.page
  json.per_page @per_page
  json.total_count @pagy.count
  json.total_pages @pagy.pages
end
