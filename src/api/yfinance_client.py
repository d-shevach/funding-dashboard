"""YFinance API client for fetching stock prices"""

from decimal import Decimal
from typing import Optional
import yfinance as yf
from src.logger import get_logger

logger = get_logger("api.yfinance")


SYMBOL_OVERRIDES = {
    "EJPD": "IJPA.L",
    "VNUA": "VNRG.L",
    "VCORP": "VUCP.L",
    "VTRB": "VDTY.L",
    "XGOV": "XTRXF",
    "XHYC": "XUHY.L",
}


def _ticker_variants(ticker: str) -> list:
    if ticker in SYMBOL_OVERRIDES:
        return [SYMBOL_OVERRIDES[ticker]]
    return [ticker, f"{ticker}.L", f"{ticker}.DE", f"{ticker}.SG", f"{ticker}.AS", f"{ticker}.MI"]


class YFinanceClient:
    """Client for fetching stock and ETF prices from Yahoo Finance"""

    @staticmethod
    def get_current_price(ticker: str, timeout: int = 10) -> Optional[Decimal]:
        """Get current price for a ticker"""
        try:
            ticker = ticker.strip().upper()

            ticker_variants = _ticker_variants(ticker)

            for ticker_variant in ticker_variants:
                try:
                    # Fetch latest data
                    data = yf.download(ticker_variant, period="1d", progress=False, timeout=timeout)

                    # Check if data is None or empty
                    if data is None:
                        continue

                    import pandas as pd

                    close_price = None

                    # yfinance returns different structures depending on the data
                    if isinstance(data, pd.Series):
                        # Series with OHLCV data for a single ticker
                        if 'Close' in data.index:
                            close_price = data.loc['Close']
                        else:
                            close_price = data.iloc[-1]
                    elif isinstance(data, pd.DataFrame):
                        if data.empty:
                            continue

                        # Check if it's a MultiIndex DataFrame (ticker in columns)
                        if isinstance(data.columns, pd.MultiIndex):
                            if 'Close' in data.columns.get_level_values(0):
                                close_price = data[('Close', ticker_variant)].iloc[-1]
                            else:
                                continue
                        else:
                            # Regular DataFrame with Close column
                            if 'Close' not in data.columns:
                                continue
                            close_price = data['Close'].iloc[-1]

                    if close_price is None or (isinstance(close_price, (int, float)) and close_price == 0):
                        continue

                    price = Decimal(str(close_price))
                    logger.debug(f"Fetched price for {ticker} (as {ticker_variant}): {price}")
                    return price

                except Exception as variant_e:
                    logger.debug(f"Ticker variant {ticker_variant} failed: {variant_e}")
                    continue

            logger.warning(f"No data available for {ticker}")
            return None

        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            return None

    @staticmethod
    def get_quote(ticker: str) -> Optional[Decimal]:
        """Get the latest traded price, including intraday"""
        ticker = ticker.strip().upper()
        for ticker_variant in _ticker_variants(ticker):
            try:
                last = yf.Ticker(ticker_variant).fast_info.last_price
                if last and last > 0:
                    return Decimal(str(last))
            except Exception as e:
                logger.debug(f"Quote variant {ticker_variant} failed: {e}")
        return None

    @staticmethod
    def get_historical_data(
        ticker: str,
        period: str = "1y",
        timeout: int = 10
    ) -> Optional[dict]:
        """Get historical data for a ticker"""
        try:
            ticker = ticker.strip().upper()

            # Try different ticker formats
            ticker_variants = [
                ticker,
                f"{ticker}.L",
                f"{ticker}.DE",
                f"{ticker}.SG",
            ]

            for ticker_variant in ticker_variants:
                try:
                    data = yf.download(ticker_variant, period=period, progress=False, timeout=timeout)

                    if data is None or (hasattr(data, 'empty') and data.empty):
                        continue

                    return {
                        "ticker": ticker,
                        "data": data,
                        "close": Decimal(str(data["Close"].iloc[-1])),
                        "open": Decimal(str(data["Open"].iloc[0])),
                        "high": Decimal(str(data["High"].max())),
                        "low": Decimal(str(data["Low"].min())),
                        "volume": int(data["Volume"].iloc[-1]) if "Volume" in data.columns else 0
                    }
                except Exception as variant_e:
                    logger.debug(f"Ticker variant {ticker_variant} failed: {variant_e}")
                    continue

            logger.warning(f"No historical data for {ticker}")
            return None

        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            return None

    @staticmethod
    def get_ticker_info(ticker: str) -> Optional[dict]:
        """Get ticker information"""
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            return {
                "ticker": ticker,
                "name": info.get("longName", info.get("shortName", ticker)),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "currency": info.get("currency", "USD"),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "dividend_yield": info.get("dividendYield", 0),
            }

        except Exception as e:
            logger.error(f"Error fetching ticker info for {ticker}: {e}")
            return None
