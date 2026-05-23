"""HTTP client for Maybe Finance API."""
import json
import os
from urllib.parse import urljoin

import httpx


class MaybeClient:
    """Thin wrapper around Maybe's REST API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.environ.get("MAYBE_URL", "http://localhost:3000")).rstrip("/")
        self.api_key = api_key or os.environ.get("MAYBE_API_KEY", "")
        if not self.api_key:
            raise SystemExit("Error: MAYBE_API_KEY not set. Export it or pass --api-key.")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-Api-Key": self.api_key, "Accept": "application/json"},
            timeout=30,
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.get(f"/api/v1/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict | None = None) -> dict:
        resp = self._client.post(f"/api/v1/{path}", json=data)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, data: dict | None = None) -> dict:
        resp = self._client.patch(f"/api/v1/{path}", json=data)
        resp.raise_for_status()
        return resp.json()

    # --- endpoints ---

    def accounts(self) -> dict:
        return self._get("accounts")

    def balance_sheet(self, start_date: str | None = None, end_date: str | None = None) -> dict:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get("balance_sheet", params or None)

    def holdings(self, account_id: str | None = None) -> dict:
        params = {}
        if account_id:
            params["account_id"] = account_id
        return self._get("holdings", params or None)

    def trades(self, account_id: str | None = None, security_id: str | None = None,
               start_date: str | None = None, end_date: str | None = None,
               trade_type: str | None = None) -> dict:
        params = {}
        if account_id:
            params["account_id"] = account_id
        if security_id:
            params["security_id"] = security_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if trade_type:
            params["type"] = trade_type
        return self._get("trades", params or None)

    def securities(self, search: str | None = None) -> dict:
        params = {}
        if search:
            params["search"] = search
        return self._get("securities", params or None)

    def security_detail(self, security_id: str, start_date: str | None = None,
                        end_date: str | None = None) -> dict:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get(f"securities/{security_id}", params or None)

    def account_balances(self, account_id: str, start_date: str | None = None,
                         end_date: str | None = None, interval: str | None = None) -> dict:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if interval:
            params["interval"] = interval
        return self._get(f"accounts/{account_id}/balances", params or None)

    def income_statement(self, start_date: str | None = None, end_date: str | None = None) -> dict:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get("income_statement", params or None)

    def exchange_rates(self, from_currency: str | None = None, to_currency: str | None = None) -> dict:
        params = {}
        if from_currency:
            params["from"] = from_currency
        if to_currency:
            params["to"] = to_currency
        return self._get("exchange_rates", params or None)

    def transactions(self, account_id: str | None = None, start_date: str | None = None,
                     end_date: str | None = None) -> dict:
        params = {}
        if account_id:
            params["account_id"] = account_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get("transactions", params or None)

    def valuations(self, account_id: str) -> dict:
        return self._get(f"accounts/{account_id}/valuations")

    def reconcile(self, account_id: str, balance: float, date: str | None = None) -> dict:
        data = {"balance": balance}
        if date:
            data["date"] = date
        return self._post(f"accounts/{account_id}/valuations", data)

    def update_valuation(self, account_id: str, valuation_id: str,
                         balance: float | None = None, date: str | None = None) -> dict:
        data = {}
        if balance is not None:
            data["balance"] = balance
        if date:
            data["date"] = date
        return self._patch(f"accounts/{account_id}/valuations/{valuation_id}", data)

    def categories(self) -> dict:
        return self._get("categories")

    def tags(self) -> dict:
        return self._get("tags")

    def close(self):
        self._client.close()
