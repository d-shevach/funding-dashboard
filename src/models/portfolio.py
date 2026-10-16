"""Portfolio management model"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from src.database import Database
from src.validators import TransactionValidator, ValidationError
from src.logger import get_logger

logger = get_logger("models.portfolio")


class Portfolio:
    """Portfolio model for managing investments"""

    ASSET_TYPES = {"Ação", "ETF", "Fundo", "Bond"}

    @staticmethod
    def add_stock(
        nome: str,
        ticker: str,
        setor: str,
        data: date,
        quantidade: Decimal,
        preco: Decimal,
        moeda: str,
        banco: str
    ) -> int:
        """Add a stock to portfolio"""
        # Validate input
        data_dict = {
            "nome": nome,
            "ticker": ticker,
            "setor": setor,
            "data": data,
            "quantidade": quantidade,
            "preco": preco,
            "moeda": moeda,
            "banco": banco,
        }

        validated = TransactionValidator.validate_stock_transaction(data_dict)

        valor_investido = validated["quantidade"] * validated["preco"]

        try:
            # Insert into portfolio
            portfolio_id = Database.execute_insert(
                "portfolio",
                [
                    "nome", "ticker", "data", "banco", "moeda",
                    "preco_compra", "quantidade", "valor_investido", "tipo", "setor"
                ],
                [
                    validated["nome"], validated["ticker"], validated["data"],
                    validated["banco"], validated["moeda"], validated["preco"],
                    validated["quantidade"], valor_investido, "Ação", validated["setor"]
                ]
            )

            # Insert into acoes
            Database.execute_insert(
                "acoes",
                [
                    "tipo_operacao", "nome", "ticker", "setor", "data",
                    "quantidade", "preco", "moeda", "banco"
                ],
                [
                    "compra", validated["nome"], validated["ticker"],
                    validated["setor"], validated["data"], validated["quantidade"],
                    validated["preco"], validated["moeda"], validated["banco"]
                ]
            )

            logger.info(f"Stock transaction added: {validated['nome']} ({validated['ticker']})")
            return portfolio_id

        except Exception as e:
            logger.error(f"Error adding stock: {e}")
            raise

    @staticmethod
    def add_etf(
        nome: str,
        ticker: str,
        setor: str,
        data: date,
        quantidade: Decimal,
        preco: Decimal,
        moeda: str,
        banco: str
    ) -> int:
        """Add an ETF to portfolio"""
        validated = TransactionValidator.validate_etf_transaction({
            "nome": nome, "ticker": ticker, "setor": setor, "data": data,
            "quantidade": quantidade, "preco": preco, "moeda": moeda, "banco": banco
        })

        valor_investido = validated["quantidade"] * validated["preco"]

        try:
            portfolio_id = Database.execute_insert(
                "portfolio",
                [
                    "nome", "ticker", "data", "banco", "moeda",
                    "preco_compra", "quantidade", "valor_investido", "tipo", "setor"
                ],
                [
                    validated["nome"], validated["ticker"], validated["data"],
                    validated["banco"], validated["moeda"], validated["preco"],
                    validated["quantidade"], valor_investido, "ETF", validated["setor"]
                ]
            )

            Database.execute_insert(
                "etf",
                [
                    "tipo_operacao", "nome", "ticker", "setor", "data",
                    "quantidade", "preco", "moeda", "banco"
                ],
                [
                    "compra", validated["nome"], validated["ticker"],
                    validated["setor"], validated["data"], validated["quantidade"],
                    validated["preco"], validated["moeda"], validated["banco"]
                ]
            )

            logger.info(f"ETF transaction added: {validated['nome']} ({validated['ticker']})")
            return portfolio_id

        except Exception as e:
            logger.error(f"Error adding ETF: {e}")
            raise

    @staticmethod
    def add_fund(
        nome: str,
        ticker: str,
        tipo: str,
        data: date,
        quantidade: Decimal,
        preco: Decimal,
        moeda: str,
        banco: str,
        taxa_administracao: Decimal = Decimal("0"),
        taxa_performance: Decimal = Decimal("0"),
        resgate: str = "Indeterminado"
    ) -> int:
        """Add a fund to portfolio"""
        validated = TransactionValidator.validate_fund_transaction({
            "nome": nome, "ticker": ticker, "tipo": tipo, "data": data,
            "quantidade": quantidade, "preco": preco, "moeda": moeda,
            "banco": banco, "taxa_administracao": taxa_administracao,
            "taxa_performance": taxa_performance, "resgate": resgate
        })

        valor_investido = validated["quantidade"] * validated["preco"]

        try:
            portfolio_id = Database.execute_insert(
                "portfolio",
                [
                    "nome", "ticker", "data", "banco", "moeda",
                    "preco_compra", "quantidade", "valor_investido", "tipo", "setor"
                ],
                [
                    validated["nome"], validated["ticker"], validated["data"],
                    validated["banco"], validated["moeda"], validated["preco"],
                    validated["quantidade"], valor_investido, "Fundo", validated["tipo"]
                ]
            )

            Database.execute_insert(
                "fundos",
                [
                    "nome", "ticker", "tipo_operacao", "resgate", "data", "banco",
                    "moeda", "preco", "quantidade", "tipo",
                    "taxa_administracao", "taxa_performance"
                ],
                [
                    validated["nome"], validated["ticker"], "compra",
                    validated["resgate"], validated["data"], validated["banco"],
                    validated["moeda"], validated["preco"], validated["quantidade"],
                    validated["tipo"], validated["taxa_administracao"],
                    validated["taxa_performance"]
                ]
            )

            logger.info(f"Fund transaction added: {validated['nome']} ({validated['ticker']})")
            return portfolio_id

        except Exception as e:
            logger.error(f"Error adding fund: {e}")
            raise

    @staticmethod
    def add_bond(
        nome: str,
        ticker: str,
        tipo_titulo: str,
        data: date,
        data_vencimento: date,
        quantidade: Decimal,
        preco: Decimal,
        moeda: str,
        banco: str,
        cupom: Decimal = Decimal("0")
    ) -> int:
        """Add a bond to portfolio"""
        validated = TransactionValidator.validate_bond_transaction({
            "nome": nome, "ticker": ticker, "tipo_titulo": tipo_titulo,
            "data": data, "data_vencimento": data_vencimento,
            "quantidade": quantidade, "preco": preco, "moeda": moeda,
            "banco": banco, "cupom": cupom
        })

        valor_investido = validated["quantidade"] * validated["preco"]

        try:
            portfolio_id = Database.execute_insert(
                "portfolio",
                [
                    "nome", "ticker", "data", "banco", "moeda",
                    "preco_compra", "quantidade", "valor_investido", "tipo", "setor"
                ],
                [
                    validated["nome"], validated["ticker"], validated["data"],
                    validated["banco"], validated["moeda"], validated["preco"],
                    validated["quantidade"], valor_investido, "Bond", validated["tipo_titulo"]
                ]
            )

            Database.execute_insert(
                "bond",
                [
                    "nome", "ticker", "tipo_operacao", "tipo_titulo", "data",
                    "data_vencimento", "quantidade", "preco", "moeda", "banco", "cupom"
                ],
                [
                    validated["nome"], validated["ticker"], "compra",
                    validated["tipo_titulo"], validated["data"],
                    validated["data_vencimento"], validated["quantidade"],
                    validated["preco"], validated["moeda"], validated["banco"],
                    validated["cupom"]
                ]
            )

            logger.info(f"Bond transaction added: {validated['nome']} ({validated['ticker']})")
            return portfolio_id

        except Exception as e:
            logger.error(f"Error adding bond: {e}")
            raise

    @staticmethod
    def get_all_positions() -> List[Dict]:
        """Get all current portfolio positions"""
        try:
            query = """
                SELECT
                    id_portfolio, nome, tipo, ticker, banco, moeda,
                    preco_compra, quantidade, valor_investido,
                    preco_atual, valor_atual, diferenca, percentual,
                    setor, data, saldo_m1, retorno_mes, retorno_ano,
                    fechamento_d1, fechamento_d2, data_fechamento_d1,
                    preco_intraday, hora_intraday
                FROM portfolio
                ORDER BY nome
            """

            results = Database.fetch_all(query)

            positions = []
            for row in results:
                positions.append({
                    "id": row[0],
                    "nome": row[1],
                    "tipo": row[2],
                    "ticker": row[3],
                    "banco": row[4],
                    "moeda": row[5],
                    "preco_compra": row[6],
                    "quantidade": row[7],
                    "valor_investido": row[8],
                    "preco_atual": row[9],
                    "valor_atual": row[10],
                    "diferenca": row[11],
                    "percentual": row[12],
                    "setor": row[13],
                    "data": row[14],
                    "saldo_m1": row[15],
                    "retorno_mes": row[16],
                    "retorno_ano": row[17],
                    "fechamento_d1": row[18],
                    "fechamento_d2": row[19],
                    "data_fechamento_d1": row[20],
                    "preco_intraday": row[21],
                    "hora_intraday": row[22],
                })

            return positions

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise

    @staticmethod
    def get_position(position_id: int) -> Optional[Dict]:
        """Get a specific position by ID"""
        try:
            query = """
                SELECT
                    id_portfolio, nome, tipo, ticker, banco, moeda,
                    preco_compra, quantidade, valor_investido,
                    preco_atual, valor_atual, diferenca, percentual
                FROM portfolio
                WHERE id_portfolio = %s
            """

            result = Database.fetch_one(query, (position_id,))

            if result:
                return {
                    "id": result[0],
                    "nome": result[1],
                    "tipo": result[2],
                    "ticker": result[3],
                    "banco": result[4],
                    "moeda": result[5],
                    "preco_compra": result[6],
                    "quantidade": result[7],
                    "valor_investido": result[8],
                    "preco_atual": result[9],
                    "valor_atual": result[10],
                    "diferenca": result[11],
                    "percentual": result[12],
                }

            return None

        except Exception as e:
            logger.error(f"Error fetching position {position_id}: {e}")
            raise

    @staticmethod
    def delete_position(position_id: int) -> bool:
        """Delete a position (after complete sale)"""
        try:
            Database.execute_delete("portfolio", {"id_portfolio": position_id})
            logger.info(f"Position {position_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting position {position_id}: {e}")
            raise
