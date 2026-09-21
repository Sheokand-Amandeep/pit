
"""NSE API access. Keep all NSE HTTP/API changes in this file."""

from datetime import date
from typing import Any
import requests

from config import (
    NSE_BASE_URL, PIT_API_PATH, DEFAULT_HEADERS,
    REQUEST_TIMEOUT, MAX_RETRIES,
)


class NSEClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _warm_up(self) -> None:
        response = self.session.get(
            NSE_BASE_URL + "/companies-listing/corporate-filings-insider-trading",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

    def _get(self, params: dict[str, str]) -> list[dict[str, Any]]:
        self._warm_up()

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    NSE_BASE_URL + PIT_API_PATH,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data")
                if not isinstance(data, list):
                    raise ValueError("NSE returned an unexpected PIT response.")
                return data
            except Exception as exc:
                last_error = exc
                if attempt == MAX_RETRIES:
                    raise RuntimeError(
                        f"NSE PIT API failed after {MAX_RETRIES} attempts: {exc}"
                    ) from exc

        raise RuntimeError(str(last_error))

    def get_pit_filings(self, from_date: date, to_date: date) -> list[dict[str, Any]]:
        return self._get({
            "index": "equities",
            "from_date": from_date.strftime("%d-%m-%Y"),
            "to_date": to_date.strftime("%d-%m-%Y"),
        })

    def get_pit_filings_without_dates(self) -> list[dict[str, Any]]:
        return self._get({"index": "equities"})
