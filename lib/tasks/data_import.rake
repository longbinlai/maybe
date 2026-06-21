# Data import from NDJSON export
#
# Usage (inside Docker container):
#   bin/rails data:import_ndjson[<path_to_ndjson>]
#   bin/rails data:import_ndjson[/tmp/all.ndjson]
#
# Or with family email/password for creating the user:
#   FAMILY_EMAIL=admin@example.com FAMILY_PASSWORD=password123 bin/rails data:import_ndjson[/tmp/all.ndjson]

namespace :data do
  desc "Import family data from NDJSON export file"
  task :import_ndjson, [:file_path] => :environment do |_, args|
    file_path = args[:file_path]
    abort "Usage: bin/rails data:import_ndjson[/path/to/all.ndjson]" unless file_path && File.exist?(file_path)

    email = ENV.fetch("FAMILY_EMAIL", "admin@family.local")
    password = ENV.fetch("FAMILY_PASSWORD", "password123")
    family_name = ENV.fetch("FAMILY_NAME", "Family")

    lines = File.readlines(file_path).map(&:strip).reject(&:empty?)
    puts "Read #{lines.size} records from #{file_path}"

    # Parse all records
    records = lines.map { |l| JSON.parse(l) }

    # Determine family_id from data
    family_id = nil
    records.each do |r|
      data = r["data"]
      if data["family_id"]
        family_id = data["family_id"]
        break
      end
    end
    abort "Cannot determine family_id from NDJSON data" unless family_id

    puts "Family ID: #{family_id}"

    # ── Step 1: Ensure Family exists ──
    family = Family.find_by(id: family_id)
    if family
      puts "✓ Family already exists: #{family.name}"
    else
      family = Family.create!(id: family_id, name: family_name)
      puts "✓ Created family: #{family.name}"
    end

    # ── Step 2: Ensure User exists ──
    user = family.users.find_by(email: email)
    if user
      puts "✓ User already exists: #{user.email}"
    else
      user = User.new(
        family: family,
        email: email,
        password: password,
        password_confirmation: password,
        first_name: "Admin",
        last_name: "User",
        role: "super_admin"
      )
      user.skip_confirmation! if user.respond_to?(:skip_confirmation!)
      user.save!(validate: false)
      puts "✓ Created user: #{user.email}"
    end

    stats = { account: 0, category: 0, tag: 0, merchant: 0, transaction: 0, trade: 0, valuation: 0, budget: 0, budget_category: 0, errors: [] }

    # ── Step 3: Import Categories ──
    puts "\n── Importing Categories ──"
    records.select { |r| r["type"] == "Category" }.each do |r|
      data = r["data"]
      begin
        cat = Category.find_or_initialize_by(id: data["id"])
        cat.assign_attributes(
          family: family,
          name: data["name"],
          color: data["color"],
          classification: data["classification"],
          lucide_icon: data["lucide_icon"],
          parent_id: data["parent_id"]
        )
        cat.save!(validate: false)
        stats[:category] += 1
      rescue => e
        stats[:errors] << "Category #{data['name']}: #{e.message}"
      end
    end
    puts "  Categories: #{stats[:category]}"

    # ── Step 4: Import Tags ──
    puts "\n── Importing Tags ──"
    records.select { |r| r["type"] == "Tag" }.each do |r|
      data = r["data"]
      begin
        tag = Tag.find_or_initialize_by(id: data["id"])
        tag.assign_attributes(
          family: family,
          name: data["name"],
          color: data["color"]
        )
        tag.save!(validate: false)
        stats[:tag] += 1
      rescue => e
        stats[:errors] << "Tag #{data['name']}: #{e.message}"
      end
    end
    puts "  Tags: #{stats[:tag]}"

    # ── Step 5: Import Merchants ──
    puts "\n── Importing Merchants ──"
    records.select { |r| r["type"] == "Merchant" }.each do |r|
      data = r["data"]
      begin
        merchant = Merchant.find_or_initialize_by(id: data["id"])
        attrs = { name: data["name"], color: data["color"] }
        attrs[:family] = family if data["family_id"]
        merchant.assign_attributes(attrs)
        merchant.save!(validate: false)
        stats[:merchant] += 1
      rescue => e
        stats[:errors] << "Merchant #{data['name']}: #{e.message}"
      end
    end
    puts "  Merchants: #{stats[:merchant]}"

    # ── Step 6: Import Accounts (with accountable) ──
    puts "\n── Importing Accounts ──"
    records.select { |r| r["type"] == "Account" }.each do |r|
      data = r["data"]
      begin
        accountable_type = data["accountable_type"]
        accountable_data = data["accountable"] || {}
        accountable_id = data["accountable_id"] || accountable_data["id"]

        # Create or update the accountable record
        if accountable_type.present? && accountable_id.present?
          accountable_class = accountable_type.constantize
          accountable = accountable_class.find_or_initialize_by(id: accountable_id)
          accountable_attrs = accountable_data.except("id", "created_at", "updated_at")
          accountable.assign_attributes(accountable_attrs)
          accountable.save!(validate: false)
        end

        # Create or update the account
        account = Account.find_or_initialize_by(id: data["id"])
        account.assign_attributes(
          family: family,
          name: data["name"],
          accountable_type: accountable_type,
          accountable_id: accountable_id,
          subtype: data["subtype"],
          balance: data["balance"],
          currency: data["currency"],
          classification: data["classification"],
          cash_balance: data["cash_balance"] || data["balance"],
          status: data["status"] || "active"
        )
        account.save!(validate: false)
        stats[:account] += 1
      rescue => e
        stats[:errors] << "Account #{data['name']}: #{e.message}"
      end
    end
    puts "  Accounts: #{stats[:account]}"

    # ── Step 7: Import Valuations ──
    puts "\n── Importing Valuations ──"
    records.select { |r| r["type"] == "Valuation" }.each do |r|
      data = r["data"]
      begin
        # Create the entry first
        entry = Entry.find_or_initialize_by(id: data["entry_id"])
        entry.assign_attributes(
          account_id: data["account_id"],
          date: data["date"],
          amount: data["amount"],
          currency: data["currency"],
          name: data["name"],
          entryable_type: "Valuation"
        )

        # Create the valuation record
        valuation = Valuation.find_or_initialize_by(id: data["id"])
        entry.entryable = valuation
        entry.save!(validate: false)
        stats[:valuation] += 1
      rescue => e
        stats[:errors] << "Valuation #{data['id']}: #{e.message}"
      end
    end
    puts "  Valuations: #{stats[:valuation]}"

    # ── Step 8: Import Transactions ──
    puts "\n── Importing Transactions ──"
    records.select { |r| r["type"] == "Transaction" }.each do |r|
      data = r["data"]
      begin
        # Create the transaction record
        transaction = Transaction.find_or_initialize_by(id: data["id"])
        transaction.assign_attributes(
          category_id: data["category_id"],
          merchant_id: data["merchant_id"],
          kind: data["kind"]
        )

        # Create the entry
        entry = Entry.find_or_initialize_by(id: data["entry_id"])
        entry.assign_attributes(
          account_id: data["account_id"],
          date: data["date"],
          amount: data["amount"],
          currency: data["currency"],
          name: data["name"],
          notes: data["notes"],
          excluded: data["excluded"] || false,
          entryable_type: "Transaction"
        )
        entry.entryable = transaction
        entry.save!(validate: false)

        # Associate tags
        if data["tag_ids"].is_a?(Array) && data["tag_ids"].any?
          transaction.tags = Tag.where(id: data["tag_ids"]) rescue nil
        end

        stats[:transaction] += 1
      rescue => e
        stats[:errors] << "Transaction #{data['id']}: #{e.message}"
      end
    end
    puts "  Transactions: #{stats[:transaction]}"

    # ── Step 9: Import Trades ──
    puts "\n── Importing Trades ──"
    records.select { |r| r["type"] == "Trade" }.each do |r|
      data = r["data"]
      begin
        # Ensure security exists
        security_id = data["security_id"]
        begin
          if security_id && !Security.exists?(security_id)
            ticker = data["ticker"] || "UNKNOWN"
            Security.find_or_create_by!(id: security_id) do |s|
              s.ticker = ticker
              s.name = ticker
            end
          end
        rescue => e
          stats[:errors] << "Security #{security_id}: #{e.message}"
        end

        # Create the trade record
        trade = Trade.find_or_initialize_by(id: data["id"])
        trade.assign_attributes(
          security_id: security_id,
          qty: data["qty"],
          price: data["price"]
        )

        # Create the entry
        entry = Entry.find_or_initialize_by(id: data["entry_id"])
        entry.assign_attributes(
          account_id: data["account_id"],
          date: data["date"],
          amount: data["amount"],
          currency: data["currency"],
          entryable_type: "Trade"
        )
        entry.entryable = trade
        entry.save!(validate: false)

        stats[:trade] += 1
      rescue => e
        stats[:errors] << "Trade #{data['id']}: #{e.message}"
      end
    end
    puts "  Trades: #{stats[:trade]}"

    # ── Step 10: Import Budgets ──
    puts "\n── Importing Budgets ──"
    records.select { |r| r["type"] == "Budget" }.each do |r|
      data = r["data"]
      begin
        budget = Budget.find_or_initialize_by(id: data["id"])
        budget.assign_attributes(data.except("id", "created_at", "updated_at").merge(family: family))
        budget.save!(validate: false)
        stats[:budget] += 1
      rescue => e
        stats[:errors] << "Budget #{data['id']}: #{e.message}"
      end
    end
    puts "  Budgets: #{stats[:budget]}"

    # ── Step 11: Import Budget Categories ──
    puts "\n── Importing Budget Categories ──"
    records.select { |r| r["type"] == "BudgetCategory" }.each do |r|
      data = r["data"]
      begin
        bc = BudgetCategory.find_or_initialize_by(id: data["id"])
        bc.assign_attributes(data.except("id", "created_at", "updated_at"))
        bc.save!(validate: false)
        stats[:budget_category] += 1
      rescue => e
        stats[:errors] << "BudgetCategory #{data['id']}: #{e.message}"
      end
    end
    puts "  Budget Categories: #{stats[:budget_category]}"

    # ── Summary ──
    puts "\n" + "=" * 60
    puts "IMPORT COMPLETE"
    puts "=" * 60
    puts "  Accounts:          #{stats[:account]}"
    puts "  Categories:        #{stats[:category]}"
    puts "  Tags:              #{stats[:tag]}"
    puts "  Merchants:         #{stats[:merchant]}"
    puts "  Valuations:        #{stats[:valuation]}"
    puts "  Transactions:      #{stats[:transaction]}"
    puts "  Trades:            #{stats[:trade]}"
    puts "  Budgets:           #{stats[:budget]}"
    puts "  Budget Categories: #{stats[:budget_category]}"
    puts "  Errors:            #{stats[:errors].size}"

    if stats[:errors].any?
      puts "\nErrors:"
      stats[:errors].each { |e| puts "  ✗ #{e}" }
    end

    puts "\nLogin: #{email} / #{password}"
    puts "URL: http://localhost:3000"
  end
end
