json.valuations @valuations do |entry|
  json.id entry.id
  json.date entry.date
  json.amount entry.amount.to_f
  json.amount_formatted entry.amount_money.format
  json.currency entry.currency
  json.name entry.name
  json.notes entry.notes
end

json.pagination do
  json.page @pagy.page
  json.per_page @per_page
  json.total_count @pagy.count
  json.total_pages @pagy.pages
end
