"""Cash positions and dividend/coupon income"""

from datetime import date
from src.database import Database
from src.logger import get_logger

logger = get_logger("automation.caixa")

BOFA_CASH = {"nome": "Caixa banco (USD)", "valor": 0.0}

DIVIDENDS = []


def ensure_dividend_table():
    Database.execute_transaction([(
        """
        CREATE TABLE IF NOT EXISTS dividendos (
            banco VARCHAR(50) NOT NULL,
            ano INT NOT NULL,
            mes INT NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            nome VARCHAR(120),
            bruto DECIMAL(18,2) NOT NULL,
            imposto DECIMAL(18,2) NOT NULL,
            PRIMARY KEY (banco, ano, mes, ticker)
        )
        """,
        (),
    )])


def seed_caixa_dividendos():
    ensure_dividend_table()
    operations = [(
        """
        INSERT INTO dividendos (banco, ano, mes, ticker, nome, bruto, imposto) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE nome = VALUES(nome), bruto = VALUES(bruto), imposto = VALUES(imposto)
        """,
        d,
    ) for d in DIVIDENDS]
    existe = Database.fetch_one(
        "SELECT COUNT(*) FROM portfolio WHERE nome = %s AND banco = 'BofA'", (BOFA_CASH["nome"],)
    )[0]
    if not existe:
        Database.execute_insert(
            "portfolio",
            ["nome", "ticker", "data", "banco", "moeda", "preco_compra", "quantidade",
             "valor_investido", "tipo", "setor", "preco_atual", "valor_atual", "diferenca", "percentual"],
            [BOFA_CASH["nome"], "CASH-BOFA", date(2026, 9, 30), "BofA", "USD", 1, BOFA_CASH["valor"],
             BOFA_CASH["valor"], "Cash", "Caixa", 1, BOFA_CASH["valor"], 0, 0],
        )
    Database.execute_transaction(operations)


def caixa_dividendos() -> dict:
    caixa = Database.fetch_all(
        "SELECT banco, COALESCE(SUM(valor_atual), 0) FROM portfolio WHERE tipo = 'Cash' GROUP BY banco"
    )
    divs = Database.fetch_all(
        "SELECT banco, ano, mes, ticker, nome, bruto, imposto FROM dividendos ORDER BY ano, mes, banco, ticker"
    )
    return {
        "caixa": [{"banco": b, "valor": round(float(v), 2)} for b, v in caixa],
        "caixa_total": round(sum(float(v) for _, v in caixa), 2),
        "dividendos": [
            {"banco": b, "ano": a, "mes": m, "ticker": t, "nome": n,
             "bruto": round(float(br), 2), "imposto": round(float(i), 2), "liquido": round(float(br) - float(i), 2)}
            for b, a, m, t, n, br, i in divs
        ],
    }
