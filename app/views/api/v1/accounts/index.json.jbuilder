# frozen_string_literal: true

json.accounts @accounts do |account|
  json.id account.id
  json.name account.name
  json.balance account.balance
  json.balance_formatted account.balance_money.format
  json.cash_balance account.cash_balance if account.balance_type == :investment
  json.currency account.currency
  json.classification account.classification
  json.account_type account.accountable_type.underscore
  json.status account.status
  json.is_plaid_linked account.plaid_account_id.present?
end

json.pagination do
  json.page @pagy.page
  json.per_page @per_page
  json.total_count @pagy.count
  json.total_pages @pagy.pages
end
