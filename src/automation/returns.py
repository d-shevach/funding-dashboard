"""Previous-close and intraday price tracking for D-1 and intraday returns"""

import html
from datetime import date, datetime
from decimal import Decimal
import yfinance as yf
from src.api import YFinanceClient
from src.automation.daily_email import send_email
from src.database import Database
from src.logger import get_logger
from src.web.auth import list_report_recipients

logger = get_logger("automation.returns")

NEW_COLUMNS = {
    "fechamento_d1": "DECIMAL(18,6) NULL",
    "fechamento_d2": "DECIMAL(18,6) NULL",
    "data_fechamento_d1": "DATE NULL",
    "preco_intraday": "DECIMAL(18,6) NULL",
    "hora_intraday": "DATETIME NULL",
    "alerta_intraday_data": "DATE NULL",
    "alerta_queda_data": "DATE NULL",
    "valor_extrato": "DECIMAL(18,2) NULL",
}

REVALUE_TOLERANCE = 0.25
REVALUE_TYPES = ("Stock", "ETF")

ALERT_THRESHOLD_PCT = 5.0


def ensure_return_columns():
    for name, definition in NEW_COLUMNS.items():
        exists = Database.fetch_one(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'portfolio' AND COLUMN_NAME = %s
            """,
            (name,),
        )[0]
        if not exists:
            Database.execute_transaction([(f"ALTER TABLE portfolio ADD COLUMN {name} {definition}", ())])
    Database.execute_transaction([(
        "UPDATE portfolio SET valor_extrato = valor_atual WHERE valor_extrato IS NULL",
        (),
    )])


def revalue_by_quote(ticker: str, price: Decimal):
    rows = Database.fetch_all(
        """
        SELECT id_portfolio, tipo, quantidade, valor_extrato, valor_investido FROM portfolio
        WHERE ticker = %s AND quantidade > 0 AND valor_extrato > 0
        """,
        (ticker,),
    )
    operations = []
    for id_portfolio, tipo, quantidade, valor_extrato, valor_investido in rows:
        if tipo not in REVALUE_TYPES:
            continue
        referencia = float(valor_extrato) / float(quantidade)
        if abs(float(price) / referencia - 1) > REVALUE_TOLERANCE:
            logger.warning(f"Cotação de {ticker} ({price}) fora da faixa do extrato ({referencia:.2f}); valor mantido")
            continue
        novo_valor = float(quantidade) * float(price)
        operations.append((
            "UPDATE portfolio SET valor_atual = %s, diferenca = %s, percentual = %s WHERE id_portfolio = %s",
            (
                round(novo_valor, 2),
                round(novo_valor - float(valor_investido), 2),
                round((novo_valor / float(valor_investido) - 1) * 100, 2) if valor_investido else 0,
                id_portfolio,
            ),
        ))
    if operations:
        Database.execute_transaction(operations)


def record_close(ticker: str, price: Decimal, today: date):
    Database.execute_transaction([(
        """
        UPDATE portfolio SET
            fechamento_d2 = IF(data_fechamento_d1 IS NULL OR data_fechamento_d1 <> %s, fechamento_d1, fechamento_d2),
            fechamento_d1 = %s,
            data_fechamento_d1 = %s
        WHERE ticker = %s
        """,
        (today, price, today, ticker),
    )])


def _alert_table(title: str, color: str, alerts: list, value_header: str = "Hoje") -> str:
    rows = "".join(
        f"<tr><td style='padding:6px;border-bottom:1px solid #eee'>{html.escape(a['ticker'])}</td>"
        f"<td style='padding:6px;border-bottom:1px solid #eee'>{html.escape(a['nome'] or '')}</td>"
        f"<td style='padding:6px;border-bottom:1px solid #eee'>{html.escape(a['banco'] or '')}</td>"
        f"<td style='padding:6px;border-bottom:1px solid #eee;color:{color};font-weight:bold'>{a['pct']:+.2f}%</td></tr>"
        for a in alerts
    )
    return (
        f"<h3 style='color:{color}'>{title}</h3>"
        "<table style='border-collapse:collapse;width:100%;font-size:14px'>"
        "<tr><th style='text-align:left;padding:6px;border-bottom:1px solid #ddd'>Ticker</th>"
        "<th style='text-align:left;padding:6px;border-bottom:1px solid #ddd'>Ativo</th>"
        "<th style='text-align:left;padding:6px;border-bottom:1px solid #ddd'>Banco</th>"
        f"<th style='text-align:left;padding:6px;border-bottom:1px solid #ddd'>{value_header}</th></tr>"
        f"{rows}</table>"
    )


def _build_alert_html(alerts: list) -> str:
    altas = [a for a in alerts if a["pct"] > ALERT_THRESHOLD_PCT]
    quedas = [a for a in alerts if a["pct"] < -ALERT_THRESHOLD_PCT]
    body = ""
    if altas:
        body += _alert_table(f"Altas acima de {ALERT_THRESHOLD_PCT:.0f}%", "#2e7d32", altas)
    if quedas:
        body += _alert_table(f"Quedas de mais de {ALERT_THRESHOLD_PCT:.0f}%", "#c0392b", quedas)
    return (
        "<html><body style='font-family:Segoe UI,Tahoma,sans-serif;color:#1f2d24'>"
        "<h2 style='color:#27AE60'>Alerta intraday</h2>"
        f"{body}</body></html>"
    )


class IntradayUpdateTask:
    """Refresh intraday prices during US market hours and alert on large moves"""

    @staticmethod
    def execute() -> dict:
        stats = {"updated": 0, "failed": 0, "total": 0, "alerts": 0, "errors": []}
        today = date.today()
        alerts = []

        try:
            tickers = Database.fetch_all("SELECT DISTINCT ticker FROM portfolio WHERE ticker IS NOT NULL")
            stats["total"] = len(tickers)

            for (ticker,) in tickers:
                try:
                    quote = YFinanceClient.get_quote(ticker)
                    if quote is None:
                        stats["failed"] += 1
                        continue

                    Database.execute_transaction([(
                        "UPDATE portfolio SET preco_intraday = %s, hora_intraday = %s WHERE ticker = %s",
                        (quote, datetime.now(), ticker),
                    )])
                    stats["updated"] += 1

                    nome, banco, fechamento, alerta_data = Database.fetch_one(
                        """
                        SELECT MAX(nome), MAX(banco), MAX(fechamento_d1), MAX(alerta_intraday_data)
                        FROM portfolio WHERE ticker = %s
                        """,
                        (ticker,),
                    )
                    if fechamento and alerta_data != today:
                        pct = (float(quote) / float(fechamento) - 1) * 100
                        if abs(pct) > ALERT_THRESHOLD_PCT:
                            alerts.append({"ticker": ticker, "nome": nome, "banco": banco, "pct": pct})
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append(f"{ticker}: {e}")

            if alerts:
                result = send_email(
                    f"Alerta intraday - {len(alerts)} asset(s) with a move above {ALERT_THRESHOLD_PCT:.0f}%",
                    _build_alert_html(alerts),
                    list_report_recipients(),
                )
                if result["sent"]:
                    for a in alerts:
                        Database.execute_transaction([(
                            "UPDATE portfolio SET alerta_intraday_data = %s WHERE ticker = %s",
                            (today, a["ticker"]),
                        )])
                    stats["alerts"] = len(alerts)
                else:
                    stats["errors"].extend(result["errors"])

            logger.info(f"Intraday update: {stats['updated']}/{stats['total']} succeeded, {stats['alerts']} alerts")
            return stats

        except Exception as e:
            logger.error(f"Intraday update task failed: {e}")
            stats["errors"].append(str(e))
            return stats
