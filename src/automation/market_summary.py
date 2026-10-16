"""Market moves, FX rates and the YTD chart for the daily email"""

import io
from typing import Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yfinance as yf
from src.logger import get_logger

logger = get_logger("automation.market_summary")

MARKETS = [
    ("S&P 500", ["^GSPC"]),
    ("Ibovespa", ["^BVSP"]),
    ("TA-125", ["^TA125.TA"]),
]

FX = [
    ("USD → BRL", ["BRL=X"], False),
    ("USD → ILS", ["ILS=X"], False),
    ("USD → EUR", ["EURUSD=X"], True),
    ("BTC → USD", ["BTC-USD"], False),
]

MONTH_LABELS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _last_and_change(symbols, invert: bool = False) -> Optional[tuple]:
    for symbol in symbols:
        try:
            closes = yf.Ticker(symbol).history(period="7d", interval="1d")["Close"].dropna()
            if len(closes) < 2:
                continue
            last, previous = float(closes.iloc[-1]), float(closes.iloc[-2])
            if invert:
                last, previous = 1 / last, 1 / previous
            return last, (last / previous - 1) * 100
        except Exception as e:
            logger.debug(f"Market symbol {symbol} failed: {e}")
    return None


def get_market_summary() -> dict:
    return {
        "mercados": [(name, _last_and_change(symbols)) for name, symbols in MARKETS],
        "cambio": [(name, _last_and_change(symbols, invert)) for name, symbols, invert in FX],
    }


def build_ytd_chart(data: dict) -> bytes:
    ano = max(m["ano"] for s in data.values() for m in s["meses"])
    keys = sorted({(m["ano"], m["mes"]) for s in data.values() for m in s["meses"] if m["ano"] == ano})
    labels = [MONTH_LABELS[mes - 1] for _, mes in keys]

    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=110)
    for name, s in data.items():
        values = {(m["ano"], m["mes"]): m["acumulado_ano"] for m in s["meses"]}
        ys = [values.get(k) for k in keys]
        if all(y is None for y in ys):
            continue
        is_benchmark = name.startswith("Benchmark")
        ax.plot(
            labels, ys, marker="o", markersize=4,
            linestyle="--" if is_benchmark else "-",
            linewidth=2.2 if name == "Weighted portfolio" else 1.6,
            label=name.replace("Benchmark: ", ""),
        )
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_title(f"Retorno acumulado no ano ({ano})", fontsize=11)
    ax.set_ylabel("%")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return buffer.getvalue()
