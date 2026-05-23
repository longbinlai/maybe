# frozen_string_literal: true

json.exchange_rates @rates do |rate|
  json.from_currency rate.from_currency
  json.to_currency rate.to_currency
  json.rate rate.rate.to_f
  json.date rate.date.iso8601
end
