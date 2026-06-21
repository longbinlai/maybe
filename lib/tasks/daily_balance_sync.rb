#!/usr/bin/env ruby
# 每日余额快照同步 - 为每个账户创建当天的 Balance 记录
# 用法: docker exec maybe-web-1 bin/rails runner /rails/lib/tasks/daily_balance_sync.rb

today = Date.today
family = Family.first

unless family
  puts "❌ No family found"
  exit 1
end

count = 0
family.accounts.visible.each do |account|
  # 检查今天是否已有记录
  existing = Balance.find_by(account: account, date: today)
  
  if existing
    # 更新现有记录
    existing.update!(
      balance: account.balance,
      cash_balance: account.cash_balance || account.balance,
      end_balance: account.balance,
      end_cash_balance: account.cash_balance || account.balance,
      start_balance: existing.start_balance.presence || account.balance,
      start_cash_balance: existing.start_cash_balance.presence || (account.cash_balance || account.balance),
      flows_factor: account.classification == "liability" ? -1 : 1
    )
  else
    # 创建新记录
    Balance.create!(
      account: account,
      date: today,
      balance: account.balance,
      cash_balance: account.cash_balance || account.balance,
      end_balance: account.balance,
      end_cash_balance: account.cash_balance || account.balance,
      start_balance: account.balance,
      start_cash_balance: account.cash_balance || account.balance,
      start_non_cash_balance: 0,
      end_non_cash_balance: 0,
      cash_inflows: 0,
      cash_outflows: 0,
      non_cash_inflows: 0,
      non_cash_outflows: 0,
      net_market_flows: 0,
      cash_adjustments: 0,
      non_cash_adjustments: 0,
      flows_factor: account.classification == "liability" ? -1 : 1,
      currency: account.currency
    )
  end
  
  count += 1
end

puts "✅ Synced #{count} balance records for #{today}"
