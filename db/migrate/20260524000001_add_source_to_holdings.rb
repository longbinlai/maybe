class AddSourceToHoldings < ActiveRecord::Migration[7.1]
  def change
    add_column :holdings, :source, :string, null: false, default: 'trade'
    add_index :holdings, :source

    # Update existing records
    Holding.update_all(source: 'trade')
  end
end
