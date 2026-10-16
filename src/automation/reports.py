"""Advanced reporting module with comprehensive portfolio analysis"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List
from src.database import Database
from src.logger import get_logger

logger = get_logger("automation.reports")


class PortfolioReports:
    """Generate comprehensive portfolio reports"""

    @staticmethod
    def get_summary() -> Dict:
        """Overall portfolio summary"""
        query = """
            SELECT
                COUNT(*) as total_positions,
                COUNT(DISTINCT tipo) as asset_types,
                COUNT(DISTINCT banco) as num_banks,
                COUNT(DISTINCT moeda) as num_currencies,
                SUM(valor_investido) as total_invested,
                SUM(valor_atual) as total_current,
                SUM(diferenca) as total_gain_loss
            FROM portfolio
        """

        result = Database.fetch_one(query)

        if result and result[4]:  # Has invested value
            roi = (Decimal(str(result[6] or 0)) / Decimal(str(result[4])) * 100)
        else:
            roi = Decimal(0)

        return {
            "total_positions": result[0] or 0,
            "asset_types": result[1] or 0,
            "num_banks": result[2] or 0,
            "num_currencies": result[3] or 0,
            "total_invested": Decimal(str(result[4] or 0)),
            "total_current": Decimal(str(result[5] or 0)),
            "total_gain_loss": Decimal(str(result[6] or 0)),
            "roi_percent": float(roi)
        }

    @staticmethod
    def by_bank() -> List[Dict]:
        """Portfolio breakdown by bank"""
        query = """
            SELECT
                banco,
                COUNT(*) as count,
                COUNT(DISTINCT tipo) as asset_types,
                SUM(valor_investido) as invested,
                SUM(valor_atual) as current_value,
                SUM(diferenca) as gain_loss
            FROM portfolio
            GROUP BY banco
            ORDER BY current_value DESC
        """

        results = Database.fetch_all(query)

        breakdown = []
        for row in results:
            if row[3]:  # Has invested value
                roi = (Decimal(str(row[5] or 0)) / Decimal(str(row[3])) * 100)
            else:
                roi = Decimal(0)

            breakdown.append({
                "bank": row[0],
                "count": row[1] or 0,
                "asset_types": row[2] or 0,
                "invested": Decimal(str(row[3] or 0)),
                "current_value": Decimal(str(row[4] or 0)),
                "gain_loss": Decimal(str(row[5] or 0)),
                "roi_percent": float(roi)
            })

        return breakdown

    @staticmethod
    def by_sector() -> List[Dict]:
        """Portfolio breakdown by sector"""
        query = """
            SELECT
                setor,
                COUNT(*) as count,
                COUNT(DISTINCT banco) as num_banks,
                SUM(valor_investido) as invested,
                SUM(valor_atual) as current_value,
                SUM(diferenca) as gain_loss
            FROM portfolio
            GROUP BY setor
            ORDER BY current_value DESC
        """

        results = Database.fetch_all(query)

        breakdown = []
        for row in results:
            if row[3]:  # Has invested value
                roi = (Decimal(str(row[5] or 0)) / Decimal(str(row[3])) * 100)
            else:
                roi = Decimal(0)

            breakdown.append({
                "sector": row[0],
                "count": row[1] or 0,
                "num_banks": row[2] or 0,
                "invested": Decimal(str(row[3] or 0)),
                "current_value": Decimal(str(row[4] or 0)),
                "gain_loss": Decimal(str(row[5] or 0)),
                "roi_percent": float(roi)
            })

        return breakdown

    @staticmethod
    def by_asset_type() -> List[Dict]:
        """Portfolio breakdown by asset type (Stock, ETF, Fund, Bond)"""
        query = """
            SELECT
                tipo,
                COUNT(*) as count,
                COUNT(DISTINCT banco) as num_banks,
                COUNT(DISTINCT setor) as num_sectors,
                SUM(valor_investido) as invested,
                SUM(valor_atual) as current_value,
                SUM(diferenca) as gain_loss
            FROM portfolio
            GROUP BY tipo
            ORDER BY current_value DESC
        """

        results = Database.fetch_all(query)

        breakdown = []
        for row in results:
            if row[4]:  # Has invested value
                roi = (Decimal(str(row[6] or 0)) / Decimal(str(row[4])) * 100)
            else:
                roi = Decimal(0)

            breakdown.append({
                "asset_type": row[0],
                "count": row[1] or 0,
                "num_banks": row[2] or 0,
                "num_sectors": row[3] or 0,
                "invested": Decimal(str(row[4] or 0)),
                "current_value": Decimal(str(row[5] or 0)),
                "gain_loss": Decimal(str(row[6] or 0)),
                "roi_percent": float(roi)
            })

        return breakdown

    @staticmethod
    def by_currency() -> List[Dict]:
        """Portfolio breakdown by currency"""
        query = """
            SELECT
                moeda,
                COUNT(*) as count,
                COUNT(DISTINCT banco) as num_banks,
                COUNT(DISTINCT tipo) as asset_types,
                SUM(valor_investido) as invested,
                SUM(valor_atual) as current_value,
                SUM(diferenca) as gain_loss
            FROM portfolio
            GROUP BY moeda
            ORDER BY current_value DESC
        """

        results = Database.fetch_all(query)

        breakdown = []
        for row in results:
            if row[4]:  # Has invested value
                roi = (Decimal(str(row[6] or 0)) / Decimal(str(row[4])) * 100)
            else:
                roi = Decimal(0)

            breakdown.append({
                "currency": row[0],
                "count": row[1] or 0,
                "num_banks": row[2] or 0,
                "asset_types": row[3] or 0,
                "invested": Decimal(str(row[4] or 0)),
                "current_value": Decimal(str(row[5] or 0)),
                "gain_loss": Decimal(str(row[6] or 0)),
                "roi_percent": float(roi)
            })

        return breakdown

    @staticmethod
    def by_bank_and_sector() -> List[Dict]:
        """Portfolio breakdown by bank AND sector combined"""
        query = """
            SELECT
                banco,
                setor,
                COUNT(*) as count,
                SUM(valor_investido) as invested,
                SUM(valor_atual) as current_value,
                SUM(diferenca) as gain_loss
            FROM portfolio
            GROUP BY banco, setor
            ORDER BY banco, current_value DESC
        """

        results = Database.fetch_all(query)

        breakdown = []
        for row in results:
            if row[3]:  # Has invested value
                roi = (Decimal(str(row[5] or 0)) / Decimal(str(row[3])) * 100)
            else:
                roi = Decimal(0)

            breakdown.append({
                "bank": row[0],
                "sector": row[1],
                "count": row[2] or 0,
                "invested": Decimal(str(row[3] or 0)),
                "current_value": Decimal(str(row[4] or 0)),
                "gain_loss": Decimal(str(row[5] or 0)),
                "roi_percent": float(roi)
            })

        return breakdown

    @staticmethod
    def returns_analysis() -> Dict:
        """Calculate returns: MTD, YTD, Since Inception"""
        today = date.today()
        first_day_month = date(today.year, today.month, 1)
        first_day_year = date(today.year, 1, 1)

        # MTD (Month-to-Date)
        mtd_query = """
            SELECT SUM(diferenca) FROM portfolio_history
            WHERE data_snapshot >= %s AND data_snapshot <= %s
        """
        mtd_result = Database.fetch_one(mtd_query, (first_day_month, today))
        mtd_gain = Decimal(str(mtd_result[0] or 0)) if mtd_result else Decimal(0)

        # YTD (Year-to-Date)
        ytd_query = """
            SELECT SUM(diferenca) FROM portfolio_history
            WHERE data_snapshot >= %s AND data_snapshot <= %s
        """
        ytd_result = Database.fetch_one(ytd_query, (first_day_year, today))
        ytd_gain = Decimal(str(ytd_result[0] or 0)) if ytd_result else Decimal(0)

        # Since Inception
        inception_query = """
            SELECT MIN(data), SUM(valor_investido) FROM portfolio
        """
        inception_result = Database.fetch_one(inception_query)

        inception_date = inception_result[0] if inception_result else None
        total_invested = Decimal(str(inception_result[1] or 0)) if inception_result else Decimal(0)

        # Current total gain/loss
        summary = PortfolioReports.get_summary()
        total_gain = summary["total_gain_loss"]

        # Calculate percentages
        if total_invested > 0:
            inception_roi = (total_gain / total_invested * 100)
        else:
            inception_roi = Decimal(0)

        # MTD and YTD percentages (estimate from snapshot)
        mtd_invested_query = """
            SELECT SUM(valor_investido) FROM portfolio_history
            WHERE data_snapshot = %s
        """
        mtd_invested_result = Database.fetch_one(mtd_invested_query, (first_day_month,))
        mtd_invested = Decimal(str(mtd_invested_result[0] or 1)) if mtd_invested_result else Decimal(1)

        mtd_roi = (mtd_gain / mtd_invested * 100) if mtd_invested > 0 else Decimal(0)
        ytd_roi = (ytd_gain / total_invested * 100) if total_invested > 0 else Decimal(0)

        return {
            "inception": {
                "date": inception_date,
                "gain_loss": total_gain,
                "roi_percent": float(inception_roi)
            },
            "ytd": {
                "gain_loss": ytd_gain,
                "roi_percent": float(ytd_roi)
            },
            "mtd": {
                "gain_loss": mtd_gain,
                "roi_percent": float(mtd_roi)
            }
        }

    @staticmethod
    def full_report() -> Dict:
        """Generate complete portfolio report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": PortfolioReports.get_summary(),
            "by_bank": PortfolioReports.by_bank(),
            "by_sector": PortfolioReports.by_sector(),
            "by_asset_type": PortfolioReports.by_asset_type(),
            "by_currency": PortfolioReports.by_currency(),
            "by_bank_and_sector": PortfolioReports.by_bank_and_sector(),
            "returns": PortfolioReports.returns_analysis()
        }
