import { Controller } from "@hotwired/stimulus";

// Connects to data-controller="transfer-form"
export default class extends Controller {
  connect() {
    this.accountsData = JSON.parse(document.getElementById('accounts-data').textContent);
  }

  updateAccountInfo() {
    this.updateFromAccountInfo();
    this.updateToAccountInfo();
    this.updateTransferCurrency();
  }

  updateFromAccountInfo() {
    const fromSelect = document.getElementById('transfer_from_account_id');
    const fromAccountInfo = document.getElementById('from_account_info');
    const fromBalance = document.getElementById('from_balance');
    const fromCurrency = document.getElementById('from_currency');

    if (fromSelect.value) {
      const account = this.accountsData.find(acc => acc.id.toString() === fromSelect.value);
      if (account) {
        fromBalance.textContent = `余额: ${account.balance}`;
        fromCurrency.textContent = account.currency;
        fromAccountInfo.classList.remove('hidden');
      }
    } else {
      fromAccountInfo.classList.add('hidden');
    }
  }

  updateToAccountInfo() {
    const toSelect = document.getElementById('transfer_to_account_id');
    const toAccountInfo = document.getElementById('to_account_info');
    const toBalance = document.getElementById('to_balance');
    const toCurrency = document.getElementById('to_currency');

    if (toSelect.value) {
      const account = this.accountsData.find(acc => acc.id.toString() === toSelect.value);
      if (account) {
        toBalance.textContent = `余额: ${account.balance}`;
        toCurrency.textContent = account.currency;
        toAccountInfo.classList.remove('hidden');
      }
    } else {
      toAccountInfo.classList.add('hidden');
    }
  }

  updateTransferCurrency() {
    const fromSelect = document.getElementById('transfer_from_account_id');
    const toSelect = document.getElementById('transfer_to_account_id');
    const amountCurrencyInfo = document.getElementById('amount_currency_info');
    const transferCurrency = document.getElementById('transfer_currency');

    if (fromSelect.value) {
      const fromAccount = this.accountsData.find(acc => acc.id.toString() === fromSelect.value);
      if (fromAccount) {
        transferCurrency.textContent = fromAccount.currency;
        amountCurrencyInfo.classList.remove('hidden');
        
        // 如果目标账户货币不同，显示警告
        if (toSelect.value) {
          const toAccount = this.accountsData.find(acc => acc.id.toString() === toSelect.value);
          if (toAccount && fromAccount.currency !== toAccount.currency) {
            transferCurrency.textContent = `${fromAccount.currency} → ${toAccount.currency}`;
            transferCurrency.className = 'text-orange-600 font-medium';
          } else {
            transferCurrency.className = '';
          }
        }
      }
    } else {
      amountCurrencyInfo.classList.add('hidden');
    }
  }
}
