# frozen_string_literal: true

json.security do
  json.id @security.id
  json.ticker @security.ticker
  json.name @security.name
  json.exchange @security.exchange_operating_mic
  json.country_code @security.country_code
  json.logo_url @security.logo_url
end

json.prices @prices do |price|
  json.date price.date.iso8601
  json.price price.price.to_f
  json.currency price.currency
end
