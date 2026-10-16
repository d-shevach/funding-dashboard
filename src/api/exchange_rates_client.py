"""Exchange rates API client"""

from decimal import Decimal
from typing import Optional, Dict
import requests
from src.config import Config
from src.logger import get_logger

logger = get_logger("api.exchange_rates")


class ExchangeRatesClient:
    """Client for fetching exchange rates from Open Exchange Rates API"""

    BASE_URL = "https://open.er-api.com/v6/latest"

    @staticmethod
    def get_exchange_rate(
        base_currency: str,
        target_currency: str,
        timeout: int = 10
    ) -> Optional[Decimal]:
        """Get exchange rate between two currencies"""
        try:
            base_currency = base_currency.strip().upper()
            target_currency = target_currency.strip().upper()

            params = {
                "apikey": Config.OPENEXCHANGERATES_API_KEY,
                "symbols": target_currency
            }

            response = requests.get(
                f"{ExchangeRatesClient.BASE_URL}/{base_currency}",
                params=params,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()

            if "error" in data:
                logger.error(f"API error: {data.get('error', 'Unknown')}")
                return None

            if "rates" not in data or target_currency not in data["rates"]:
                logger.warning(f"No rate available for {base_currency}/{target_currency}")
                return None

            rate = Decimal(str(data["rates"][target_currency]))
            logger.debug(f"Fetched {base_currency}/{target_currency}: {rate}")
            return rate

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
            return None

    @staticmethod
    def get_multiple_rates(
        base_currency: str,
        target_currencies: list,
        timeout: int = 10
    ) -> Optional[Dict[str, Decimal]]:
        """Get exchange rates for multiple target currencies"""
        try:
            base_currency = base_currency.strip().upper()
            target_currencies = [c.strip().upper() for c in target_currencies]

            params = {
                "apikey": Config.OPENEXCHANGERATES_API_KEY,
                "symbols": ",".join(target_currencies)
            }

            response = requests.get(
                f"{ExchangeRatesClient.BASE_URL}/{base_currency}",
                params=params,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()

            if "error" in data:
                logger.error(f"API error: {data.get('error', 'Unknown')}")
                return None

            if "rates" not in data:
                logger.warning(f"No rates available")
                return None

            rates = {}
            for currency, rate in data["rates"].items():
                if currency in target_currencies:
                    rates[currency] = Decimal(str(rate))

            logger.debug(f"Fetched {len(rates)} exchange rates from {base_currency}")
            return rates

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching exchange rates: {e}")
            return None
