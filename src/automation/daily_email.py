"""Daily end-of-day portfolio email"""

import html
import smtplib
from collections import defaultdict
from datetime import date
from email.message import EmailMessage

from src.config import Config
from src.logger import get_logger
from src.models import Portfolio
from src.web.auth import list_report_recipients

logger = get_logger("automation.daily_email")

MUTUAL_FUND_TYPES = ("Fund", "Fundo")
GREEN = "#2e7d32"
RED = "#c0392b"
BRAND = "#27AE60"
DARK = "#1e8449"
MUTED = "#8a9a8f"
FONT = "font-family:'Segoe UI',Tahoma,Arial,sans-serif;"

TYPE_ORDER = [
    ("stock", "Stocks"),
    ("etf", "ETFs"),
    ("fund", "Funds"),
    ("bond", "Bonds"),
    ("cash", "Cash"),
    ("other", "Other"),
]
_TYPE_KEYS = {
    "Ação": "stock", "Acao": "stock", "Stock": "stock",
    "ETF": "etf",
    "Fund": "fund", "Fundo": "fund",
    "Bond": "bond", "Título": "bond", "Titulo": "bond",
    "Cash": "cash", "Caixa": "cash",
}


def _type_key(p) -> str:
    return _TYPE_KEYS.get(p.get("tipo"), "other")


def _destaques(group, type_key: str, limite: int = 5) -> list:
    typed = [p for p in group if _type_key(p) == type_key and _day_return(p) is not None]
    ordered = sorted(typed, key=_day_return, reverse=True)
    gainers = [p for p in ordered if _day_return(p) > 0][:limite]
    losers = [p for p in reversed(ordered) if _day_return(p) < 0][:limite]
    return gainers + losers


def _num(value) -> float:
    return float(value) if value else 0.0


def _day_return(p):
    if p.get("tipo") in MUTUAL_FUND_TYPES:
        return None
    if p.get("fechamento_d1") and p.get("fechamento_d2"):
        return (float(p["fechamento_d1"]) / float(p["fechamento_d2"]) - 1) * 100
    return None


def _group(positions, key):
    groups = defaultdict(lambda: {"investido": 0.0, "atual": 0.0, "count": 0, "dia_num": 0.0, "dia_base": 0.0})
    for p in positions:
        g = groups[key(p)]
        g["investido"] += _num(p["valor_investido"])
        g["atual"] += _num(p["valor_atual"])
        g["count"] += 1
        dia = _day_return(p)
        if dia is not None:
            g["dia_num"] += dia * _num(p["valor_atual"])
            g["dia_base"] += _num(p["valor_atual"])
    return groups


def _ret(investido: float, atual: float) -> float:
    return ((atual - investido) / investido * 100) if investido else 0.0


def _dia_value(g):
    return g["dia_num"] / g["dia_base"] if g["dia_base"] else None


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _pct_span(value):
    if value is None:
        return f"<span style='color:{MUTED}'>-</span>"
    color = GREEN if value >= 0 else RED
    return f"<span style='color:{color};font-weight:bold'>{value:+.2f}%</span>"


def _cell(content, align="left", extra=""):
    return f"<td style='padding:9px 10px;border-bottom:1px solid #e6ece8;text-align:{align};{extra}'>{content}</td>"


def _table(headers, rows, aligns) -> str:
    head = "".join(
        f"<th style='padding:9px 10px;background:transparent;color:{MUTED};text-align:{a};font-size:12px;"
        f"text-transform:uppercase;letter-spacing:0.4px;border-bottom:2px solid #dddddd'>{h}</th>"
        for h, a in zip(headers, aligns)
    )
    body = ""
    for i, row in enumerate(rows):
        bg = "#f5faf6" if i % 2 else "#ffffff"
        cells = "".join(_cell(c, a, f"background:{bg};font-size:14px") for c, a in zip(row, aligns))
        body += f"<tr>{cells}</tr>"
    return (
        "<table role='presentation' cellspacing='0' cellpadding='0' style='width:100%;border-collapse:collapse;"
        f"border-radius:8px;overflow:hidden;{FONT}'><tr>{head}</tr>{body}</table>"
    )


def _section(title: str, content: str) -> str:
    return (
        f"<div style='margin:28px 0 10px;font-size:16px;font-weight:bold;color:{BRAND};{FONT}'>{title}</div>"
        f"{content}"
    )


def _summary_cards(by_moeda) -> str:
    cards = ""
    for moeda, g in sorted(by_moeda.items()):
        dia = _dia_value(g)
        cards += (
            "<td style='width:50%;padding:0 6px 12px;vertical-align:top'>"
            "<div style='background:#ffffff;border-radius:10px;padding:16px 18px;"
            f"box-shadow:0 1px 3px rgba(0,0,0,0.08);{FONT}'>"
            f"<div style='font-size:12px;color:{MUTED};text-transform:uppercase;letter-spacing:0.5px'>{html.escape(moeda)}</div>"
            f"<div style='font-size:24px;font-weight:bold;color:#1f2d24;margin:6px 0 10px'>{_money(g['atual'])}</div>"
            f"<div style='font-size:13px;color:{MUTED}'>Retorno do dia {_pct_span(dia)}</div>"
            f"<div style='font-size:13px;color:{MUTED};margin-top:4px'>Since inception {_pct_span(_ret(g['investido'], g['atual']))}</div>"
            "</div></td>"
        )
    return "<table role='presentation' cellspacing='0' cellpadding='0' style='width:100%'><tr>" + cards + "</tr></table>"


FX_FORMATS = {"USD → BRL": "R$ {:.2f}", "USD → ILS": "₪ {:.3f}", "USD → EUR": "€ {:.4f}", "BTC → USD": "US$ {:,.0f}"}


def _quote_card(label, value_text, change):
    return (
        "<td style='width:25%;padding:0 4px 8px;vertical-align:top'>"
        f"<div style='background:#ffffff;border-radius:8px;padding:10px;text-align:center;{FONT}'>"
        f"<div style='font-size:11px;color:{MUTED};text-transform:uppercase'>{html.escape(label)}</div>"
        f"<div style='font-size:16px;font-weight:bold;color:#1f2d24;margin:4px 0'>{value_text}</div>"
        f"<div style='font-size:12px'>{_pct_span(change)}</div>"
        "</div></td>"
    )


def _market_block(market) -> str:
    fx_cards = "".join(
        _quote_card(name, FX_FORMATS[name].format(v[0]) if v else "-", v[1] if v else None)
        for name, v in market["cambio"]
    )
    index_cards = "".join(
        _quote_card(name, f"{v[0]:,.2f}" if v else "-", v[1] if v else None)
        for name, v in market["mercados"]
    )
    return (
        _section("Currency (1 USD)", f"<table role='presentation' cellspacing='0' cellpadding='0' style='width:100%'><tr>{fx_cards}</tr></table>")
        + _section("Markets today", f"<table role='presentation' cellspacing='0' cellpadding='0' style='width:100%'><tr>{index_cards}</tr></table>")
    )


def _chart_block(cid: str) -> str:
    return _section(
        "Cumulative return year to date",
        f"<img src='cid:{cid}' alt='Retorno acumulado no ano' style='width:100%;max-width:680px;display:block;border-radius:8px'>",
    )


def build_report_html(positions, today: date, market=None, chart_cid=None, boletim_html=None) -> str:
    boletim_block = _section("Bass - Daily bulletin", boletim_html) if boletim_html else ""
    market_html = _market_block(market) if market else ""
    chart_html = _chart_block(chart_cid) if chart_cid else ""
    by_moeda = _group(positions, lambda p: p["moeda"] or "-")

    moeda_rows = [
        [html.escape(moeda), str(g["count"]), _money(g["investido"]), _money(g["atual"]),
         _pct_span(_dia_value(g)), _pct_span(_ret(g["investido"], g["atual"]))]
        for moeda, g in sorted(by_moeda.items())
    ]
    sections = [
        _section("Por moeda", _table(
            ["Currency", "Positions", "Invested", "Current value", "Day", "Since inception"],
            moeda_rows, ["left", "center", "right", "right", "right", "right"])),
    ]

    for title, key in (("Por banco", lambda p: p["banco"] or "-"),
                       ("Por tipo", lambda p: p["tipo"] or "-")):
        groups = _group(positions, key)
        rows = [
            [html.escape(name), str(g["count"]), _money(g["atual"]),
             _pct_span(_dia_value(g)), _pct_span(_ret(g["investido"], g["atual"]))]
            for name, g in sorted(groups.items(), key=lambda kv: -kv[1]["atual"])
        ]
        sections.append(_section(title, _table(
            ["Group", "Positions", "Current value", "Day", "Since inception"],
            rows, ["left", "center", "right", "right", "right"])))

    banks = _group(positions, lambda p: p["banco"] or "-")
    for bank, g in sorted(banks.items(), key=lambda kv: -kv[1]["atual"]):
        group = [p for p in positions if (p["banco"] or "-") == bank]
        rows = []
        for type_key, type_label in TYPE_ORDER:
            for p in _destaques(group, type_key):
                rows.append([
                    html.escape(p["nome"] or "-"),
                    type_label,
                    html.escape(p["moeda"] or "-"),
                    _money(_num(p["valor_atual"])),
                    _pct_span(_day_return(p)),
                    _pct_span(_ret(_num(p["valor_investido"]), _num(p["valor_atual"]))),
                ])
        sections.append(_section(
            f"{html.escape(bank)} ({g['count']})",
            _table(
                ["Asset", "Type", "Currency", "Current value", "Day", "Since inception"],
                rows, ["left", "left", "center", "right", "right", "right"]),
        ))

    return (
        "<html><body style='margin:0;padding:0;background:#f4f6f5'>"
        "<table role='presentation' cellspacing='0' cellpadding='0' style='width:100%;background:#f4f6f5'>"
        "<tr><td align='center' style='padding:24px 12px'>"
        "<table role='presentation' cellspacing='0' cellpadding='0' style='width:100%;max-width:680px'>"
        f"<tr><td style='background:{BRAND};border-radius:12px 12px 0 0;padding:22px 26px;{FONT}'>"
        f"<div style='color:#ffffff;font-size:20px;font-weight:bold'>{today.strftime('%d/%m/%Y')} - Daily portfolio report</div>"
        "</td></tr>"
        "<tr><td style='background:#f4f6f5;padding:18px 0 0'>"
        f"{market_html}{boletim_block}{_summary_cards(by_moeda)}{chart_html}"
        "</td></tr>"
        "<tr><td style='background:#ffffff;border-radius:0 0 12px 12px;padding:6px 22px 22px'>"
        + "".join(sections) +
        "</td></tr>"
        f"<tr><td style='padding:16px 8px;text-align:center;font-size:11px;color:{MUTED};{FONT}'>"
        "Day = return of the last closed session. Since inception = current value over invested amount. "
        "Mutual funds have no day return.</td></tr>"
        "</table></td></tr></table></body></html>"
    )


def send_email(subject: str, body_html: str, recipients: list, inline_png: bytes = None) -> dict:
    if not recipients:
        return {"sent": 0, "errors": ["no recipients"]}

    if not (Config.SMTP_HOST and Config.SMTP_FROM):
        logger.error("SMTP not configured; email not sent")
        return {"sent": 0, "errors": ["SMTP not configured"]}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM
    msg["Bcc"] = ", ".join(recipients)
    msg.set_content("Your email client does not show HTML. Please open it in a browser or a compatible client.")
    msg.add_alternative(body_html, subtype="html")
    if inline_png:
        msg.get_body(preferencelist=("html",)).add_related(
            inline_png, maintype="image", subtype="png", cid="<ytd_chart>"
        )

    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=30) as smtp:
            smtp.starttls()
            if Config.SMTP_USER:
                smtp.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info(f"Email '{subject}' sent to {len(recipients)} recipient(s)")
        return {"sent": len(recipients), "errors": []}
    except Exception as e:
        logger.error(f"Failed to send email '{subject}': {e}")
        return {"sent": 0, "errors": [str(e)]}


def _mercado_americano_aberto(dia: date) -> bool:
    from holidays import financial_holidays
    return dia.weekday() < 5 and dia not in financial_holidays("NYSE", years=dia.year)


def send_daily_report() -> dict:
    from src.automation.market_summary import build_ytd_chart, get_market_summary
    from src.automation.monthly_returns import list_monthly_returns

    today = date.today()
    if not _mercado_americano_aberto(today):
        logger.info(f"Relatório diário não enviado: mercado americano fechado em {today:%d/%m/%Y}")
        return {"sent": 0, "errors": [], "skipped": "mercado americano fechado"}

    positions = Portfolio.get_all_positions()

    try:
        market = get_market_summary()
    except Exception as e:
        logger.error(f"Market summary failed: {e}")
        market = None

    try:
        chart = build_ytd_chart(list_monthly_returns())
    except Exception as e:
        logger.error(f"YTD chart failed: {e}")
        chart = None

    from src.automation.boletim import formatar_dados, gerar_boletim, texto_para_html
    boletim_html = None
    if market:
        try:
            boletim_html = texto_para_html(gerar_boletim(formatar_dados(market, positions, today)))
        except Exception as e:
            logger.error(f"Boletim failed, sending report without it: {e}")

    body = build_report_html(positions, today, market, "ytd_chart" if chart else None, boletim_html)
    subject = f"{today.strftime('%d/%m/%Y')} - Daily portfolio report"
    return send_email(subject, body, list_report_recipients(), inline_png=chart)
