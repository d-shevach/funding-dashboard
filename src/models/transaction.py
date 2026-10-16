"""Transaction model for buy/sell operations"""

from datetime import date
from decimal import Decimal
from typing import Dict, Optional
from src.database import Database
from src.validators import TransactionValidator, ValidationError
from src.logger import get_logger

logger = get_logger("models.transaction")


class Transaction:
    """Handle buy and sell transactions"""

    @staticmethod
    def get_asset_type(position_id: int) -> Optional[str]:
        """Get the asset type for a position"""
        try:
            query = "SELECT tipo FROM portfolio WHERE id_portfolio = %s"
            result = Database.fetch_one(query, (position_id,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting asset type: {e}")
            raise

    @staticmethod
    def sell_complete(
        position_id: int,
        preco_venda: Decimal,
        data_venda: date
    ) -> bool:
        """Complete sale of a position"""
        try:
            # Get position details
            query = """
                SELECT nome, ticker, tipo, banco, moeda, quantidade
                FROM portfolio
                WHERE id_portfolio = %s
            """
            result = Database.fetch_one(query, (position_id,))

            if not result:
                raise ValidationError(f"Position {position_id} not found")

            nome, ticker, tipo, banco, moeda, quantidade = result

            # Validate sale price
            preco_venda = TransactionValidator.validate_price(preco_venda)
            data_venda = TransactionValidator.validate_date(data_venda)

            # Determine table name
            table_map = {
                "ETF": "etf",
                "Ação": "acoes",
                "Fundo": "fundos",
                "Bond": "bond"
            }

            table = table_map.get(tipo)
            if not table:
                raise ValidationError(f"Unknown asset type: {tipo}")

            # Record the sale
            Database.execute_insert(
                table,
                [
                    "tipo_operacao", "nome", "ticker", "data",
                    "quantidade", "preco", "banco", "moeda"
                ],
                [
                    "venda", nome, ticker, data_venda,
                    quantidade, preco_venda, banco, moeda
                ]
            )

            # Delete from portfolio
            Database.execute_delete("portfolio", {"id_portfolio": position_id})

            logger.info(f"Complete sale recorded for position {position_id}: {nome} ({ticker})")
            return True

        except Exception as e:
            logger.error(f"Error in complete sale: {e}")
            raise

    @staticmethod
    def sell_partial(
        position_id: int,
        quantidade_venda: Decimal,
        preco_venda: Decimal,
        data_venda: date
    ) -> bool:
        """Partial sale of a position"""
        try:
            # Get position details
            query = """
                SELECT nome, ticker, tipo, banco, moeda, quantidade
                FROM portfolio
                WHERE id_portfolio = %s
            """
            result = Database.fetch_one(query, (position_id,))

            if not result:
                raise ValidationError(f"Position {position_id} not found")

            nome, ticker, tipo, banco, moeda, quantidade_atual = result

            # Validate inputs
            quantidade_venda, preco_venda = TransactionValidator.validate_sale(
                quantidade_atual, quantidade_venda, preco_venda
            )
            data_venda = TransactionValidator.validate_date(data_venda)

            # Determine table name
            table_map = {
                "ETF": "etf",
                "Ação": "acoes",
                "Fundo": "fundos",
                "Bond": "bond"
            }

            table = table_map.get(tipo)
            if not table:
                raise ValidationError(f"Unknown asset type: {tipo}")

            # Record the sale
            Database.execute_insert(
                table,
                [
                    "tipo_operacao", "nome", "ticker", "data",
                    "quantidade", "preco", "banco", "moeda"
                ],
                [
                    "venda", nome, ticker, data_venda,
                    quantidade_venda, preco_venda, banco, moeda
                ]
            )

            # Update portfolio with remaining quantity
            nova_quantidade = quantidade_atual - quantidade_venda
            Database.execute_update(
                "portfolio",
                {"quantidade": nova_quantidade},
                {"id_portfolio": position_id}
            )

            logger.info(
                f"Partial sale recorded for position {position_id}: "
                f"{quantidade_venda} units of {nome} ({ticker})"
            )
            return True

        except Exception as e:
            logger.error(f"Error in partial sale: {e}")
            raise
