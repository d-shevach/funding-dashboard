"""Monthly returns per bank, taken from account statements"""

from decimal import Decimal
from src.database import Database

BANK_RETURNS = {}


def ensure_monthly_returns_table():
    Database.execute_transaction([(
        """
        CREATE TABLE IF NOT EXISTS monthly_returns (
            banco VARCHAR(50) NOT NULL,
            ano INT NOT NULL,
            mes INT NOT NULL,
            retorno_pct DECIMAL(10,4) NOT NULL,
            PRIMARY KEY (banco, ano, mes)
        )
        """,
        (),
    )])


def seed_monthly_returns():
    operations = []
    for banco, months in BANK_RETURNS.items():
        for (ano, mes), pct in months.items():
            operations.append((
                """
                INSERT INTO monthly_returns (banco, ano, mes, retorno_pct) VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE retorno_pct = VALUES(retorno_pct)
                """,
                (banco, ano, mes, Decimal(pct)),
            ))
    Database.execute_transaction(operations)


BOFA_OPENING_BALANCES = {}


def _current_value(banco: str) -> float:
    row = Database.fetch_one(
        "SELECT COALESCE(SUM(valor_atual), 0) FROM portfolio WHERE banco = %s", (banco,)
    )
    return float(row[0])


def _openings_by_backward_calc(returns_by_key: dict, closing_atual: float) -> dict:
    openings = {}
    closing = closing_atual
    for key in sorted(returns_by_key, reverse=True):
        opening = closing / (1 + returns_by_key[key] / 100)
        openings[key] = opening
        closing = opening
    return openings


def _cumulative(meses: list) -> list:
    fator = 1.0
    fator_ano = {}
    result = []
    for m in meses:
        fator *= 1 + m["retorno"] / 100
        fator_ano[m["ano"]] = fator_ano.get(m["ano"], 1.0) * (1 + m["retorno"] / 100)
        result.append({
            **m,
            "acumulado": round((fator - 1) * 100, 2),
            "acumulado_ano": round((fator_ano[m["ano"]] - 1) * 100, 2),
        })
    return result


BENCHMARKS = {
    "SPY": "S&P 500 (SPY)",
    "BIL": "T-Bill (BIL)",
}
BENCHMARK_PREFIX = "Benchmark: "


def ensure_benchmark_table():
    Database.execute_transaction([(
        """
        CREATE TABLE IF NOT EXISTS benchmark_returns (
            ticker VARCHAR(10) NOT NULL,
            ano INT NOT NULL,
            mes INT NOT NULL,
            retorno_pct DECIMAL(10,4) NOT NULL,
            PRIMARY KEY (ticker, ano, mes)
        )
        """,
        (),
    )])


def update_benchmarks():
    import yfinance as yf
    from datetime import date

    ensure_benchmark_table()
    today = date.today()
    operations = []
    for ticker in BENCHMARKS:
        try:
            closes = yf.Ticker(ticker).history(start="2023-12-01", interval="1mo", auto_adjust=True)["Close"].dropna()
        except Exception:
            continue
        previous = None
        for stamp, close in closes.items():
            key = (stamp.year, stamp.month)
            if key >= (today.year, today.month):
                previous = None
                continue
            if previous is not None:
                pct = round((float(close) / float(previous) - 1) * 100, 4)
                operations.append((
                    """
                    INSERT INTO benchmark_returns (ticker, ano, mes, retorno_pct) VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE retorno_pct = VALUES(retorno_pct)
                    """,
                    (ticker, key[0], key[1], Decimal(str(pct))),
                ))
            previous = close
    if operations:
        Database.execute_transaction(operations)


def _benchmark_series() -> dict:
    rows = Database.fetch_all(
        "SELECT ticker, ano, mes, retorno_pct FROM benchmark_returns ORDER BY ticker, ano, mes"
    )
    by_ticker = {}
    for ticker, ano, mes, pct in rows:
        by_ticker.setdefault(ticker, []).append({"ano": ano, "mes": mes, "retorno": round(float(pct), 2)})
    return {
        f"{BENCHMARK_PREFIX}{BENCHMARKS[t]}": {"meses": _cumulative(meses)}
        for t, meses in by_ticker.items()
        if t in BENCHMARKS
    }


def list_monthly_returns() -> dict:
    rows = Database.fetch_all(
        "SELECT banco, ano, mes, retorno_pct FROM monthly_returns ORDER BY banco, ano, mes"
    )
    returns = {}
    for banco, ano, mes, pct in rows:
        returns.setdefault(banco, {})[(ano, mes)] = float(pct)

    openings = {}
    for banco, by_key in returns.items():
        if banco == "BofA":
            openings[banco] = {k: BOFA_OPENING_BALANCES[k] for k in by_key if k in BOFA_OPENING_BALANCES}
        else:
            openings[banco] = _openings_by_backward_calc(by_key, _current_value(banco))

    result = {
        banco: {
            "meses": _cumulative([
                {"ano": ano, "mes": mes, "retorno": round(pct, 2)}
                for (ano, mes), pct in sorted(by_key.items())
            ])
        }
        for banco, by_key in returns.items()
    }

    portfolio_meses = []
    all_keys = sorted({k for by_key in returns.values() for k in by_key})
    for key in all_keys:
        num = den = 0.0
        for banco in returns:
            if key in returns[banco] and key in openings.get(banco, {}):
                w = openings[banco][key]
                num += w * returns[banco][key]
                den += w
        if den > 0:
            portfolio_meses.append({"ano": key[0], "mes": key[1], "retorno": round(num / den, 2)})
    result["Weighted portfolio"] = {"meses": _cumulative(portfolio_meses)}
    result.update(_benchmark_series())

    return result
