"""Automated tasks for price updates, exchange rates, and snapshots"""

from datetime import date, datetime
from decimal import Decimal
from src.database import Database
from src.api import YFinanceClient, ExchangeRatesClient
from src.automation.returns import record_close, revalue_by_quote
from src.logger import get_logger

logger = get_logger("automation.tasks")


class PriceUpdateTask:
    """Update current prices for all holdings"""

    @staticmethod
    def execute() -> dict:
        """Execute price update task"""
        stats = {
            "updated": 0,
            "failed": 0,
            "total": 0,
            "errors": []
        }

        try:
            # Get all unique tickers
            query = "SELECT DISTINCT ticker FROM portfolio WHERE ticker IS NOT NULL"
            tickers = Database.fetch_all(query)

            stats["total"] = len(tickers)
            logger.info(f"Starting price update for {stats['total']} tickers")

            for ticker_row in tickers:
                ticker = ticker_row[0]

                try:
                    # Fetch current price
                    price = YFinanceClient.get_current_price(ticker)

                    if price is None:
                        stats["failed"] += 1
                        error_msg = f"No price data for {ticker}"
                        logger.warning(error_msg)
                        stats["errors"].append(error_msg)
                        continue

                    # Update portfolio
                    Database.execute_update(
                        "portfolio",
                        {
                            "preco_atual": price,
                            "hoje": date.today()
                        },
                        {"ticker": ticker}
                    )

                    record_close(ticker, price, date.today())
                    revalue_by_quote(ticker, price)

                    stats["updated"] += 1
                    logger.info(f"Updated {ticker}: ${price}")

                except Exception as e:
                    stats["failed"] += 1
                    error_msg = f"Error updating {ticker}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            logger.info(f"Price update completed: {stats['updated']}/{stats['total']} succeeded")
            return stats

        except Exception as e:
            logger.error(f"Price update task failed: {e}")
            stats["errors"].append(str(e))
            return stats


class ExchangeRateUpdateTask:
    """Update exchange rates for FX holdings"""

    @staticmethod
    def execute() -> dict:
        """Execute exchange rate update task"""
        stats = {
            "updated": 0,
            "failed": 0,
            "total": 0,
            "errors": []
        }

        try:
            # Define currency pairs to fetch
            pairs = {
                "USDEUR": ("USD", "EUR"),
                "EURUSD": ("EUR", "USD"),
                "USDBRL": ("USD", "BRL"),
                "BRLUSD": ("BRL", "USD"),
            }

            stats["total"] = len(pairs)
            logger.info(f"Starting exchange rate update for {stats['total']} pairs")

            for ticker, (base, target) in pairs.items():
                try:
                    # Fetch exchange rate
                    rate = ExchangeRatesClient.get_exchange_rate(base, target)

                    if rate is None:
                        stats["failed"] += 1
                        error_msg = f"No rate data for {ticker}"
                        logger.warning(error_msg)
                        stats["errors"].append(error_msg)
                        continue

                    # Update FX table
                    Database.execute_update(
                        "fx",
                        {"paridade": rate},
                        {"ticker": ticker}
                    )

                    stats["updated"] += 1
                    logger.info(f"Updated {ticker}: {rate}")

                except Exception as e:
                    stats["failed"] += 1
                    error_msg = f"Error updating {ticker}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            logger.info(f"Exchange rate update completed: {stats['updated']}/{stats['total']} succeeded")
            return stats

        except Exception as e:
            logger.error(f"Exchange rate update task failed: {e}")
            stats["errors"].append(str(e))
            return stats


class PortfolioSnapshotTask:
    """Create daily portfolio snapshot for history tracking"""

    @staticmethod
    def execute() -> dict:
        """Execute portfolio snapshot task"""
        stats = {
            "inserted": 0,
            "skipped": False,
            "errors": []
        }

        try:
            today = date.today()

            # Check if today's snapshot already exists
            query = "SELECT COUNT(*) FROM portfolio_history WHERE data_snapshot = %s"
            count_result = Database.fetch_one(query, (today,))

            if count_result and count_result[0] > 0:
                logger.info(f"Snapshot for {today} already exists, skipping")
                stats["skipped"] = True
                return stats

            # Get all current portfolio data
            query = """
                SELECT
                    ticker, nome, tipo, banco, moeda, preco_compra,
                    quantidade, valor_investido, preco_atual, valor_atual,
                    diferenca, percentual, setor
                FROM portfolio
            """

            portfolio_data = Database.fetch_all(query)
            stats["total"] = len(portfolio_data)
            logger.info(f"Creating snapshot with {stats['total']} positions")

            # Insert all rows into history
            insert_query = """
                INSERT INTO portfolio_history
                (ticker, nome, tipo, banco, moeda, preco_compra,
                 quantidade, valor_investido, preco_atual, valor_atual,
                 diferenca, percentual, setor, data_snapshot)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            operations = []
            for row in portfolio_data:
                operations.append((insert_query, row + (today,)))

            Database.execute_transaction(operations)

            stats["inserted"] = len(portfolio_data)
            logger.info(f"Portfolio snapshot created: {stats['inserted']} positions")
            return stats

        except Exception as e:
            logger.error(f"Portfolio snapshot task failed: {e}")
            stats["errors"].append(str(e))
            return stats


class ReportGenerationTask:
    """Generate portfolio reports"""

    @staticmethod
    def generate_summary() -> dict:
        """Generate portfolio summary"""
        try:
            query = """
                SELECT
                    COUNT(*) as total_positions,
                    COUNT(DISTINCT tipo) as asset_types,
                    SUM(valor_investido) as total_invested,
                    SUM(valor_atual) as total_current,
                    SUM(diferenca) as total_gain_loss
                FROM portfolio
            """

            result = Database.fetch_one(query)

            if result:
                return {
                    "total_positions": result[0] or 0,
                    "asset_types": result[1] or 0,
                    "total_invested": Decimal(str(result[2] or 0)),
                    "total_current": Decimal(str(result[3] or 0)),
                    "total_gain_loss": Decimal(str(result[4] or 0)),
                    "roi_percent": float(
                        (Decimal(str(result[4] or 0)) / Decimal(str(result[2] or 1))) * 100
                    ) if result[2] else 0
                }

            return None

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None

    @staticmethod
    def generate_by_asset_type() -> list:
        """Generate summary by asset type"""
        try:
            query = """
                SELECT
                    tipo,
                    COUNT(*) as count,
                    SUM(valor_investido) as total_invested,
                    SUM(valor_atual) as total_current,
                    SUM(diferenca) as total_gain_loss
                FROM portfolio
                GROUP BY tipo
                ORDER BY total_current DESC
            """

            results = Database.fetch_all(query)

            summaries = []
            for row in results:
                summaries.append({
                    "asset_type": row[0],
                    "count": row[1] or 0,
                    "total_invested": Decimal(str(row[2] or 0)),
                    "total_current": Decimal(str(row[3] or 0)),
                    "total_gain_loss": Decimal(str(row[4] or 0)),
                })

            return summaries

        except Exception as e:
            logger.error(f"Error generating asset type summary: {e}")
            return []
