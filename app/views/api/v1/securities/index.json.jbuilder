# frozen_string_literal: true

json.securities @securities do |security|
  json.id security.id
  json.ticker security.ticker
  json.name security.name
  json.exchange security.exchange_operating_mic
  json.country_code security.country_code
  json.logo_url security.logo_url
  json.current_price security.current_price&.amount&.to_f
  json.current_price_currency security.current_price&.currency
end

json.pagination do
  json.page @pagy.page
  json.per_page @per_page
  json.total_count @pagy.count
  json.total_pages @pagy.pages
end
