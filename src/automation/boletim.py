"""Daily market bulletin written by an LLM from the portfolio data and free news headlines"""

import html
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from src.automation.daily_email import TYPE_ORDER, _day_return, _destaques, _dia_value, _group
from src.logger import get_logger

logger = get_logger("automation.boletim")

MODEL = "claude-haiku-5-5"
MAX_HEADLINES = 4

NEWS_QUERIES = [
    ("US", "Wall Street S&P 500 Nasdaq stocks"),
    ("US tech", "AI chip stocks Nvidia"),
    ("Europe", "European stocks ECB euro"),
    ("China", "China economy stocks yuan"),
    ("Brazil", "Brazil Ibovespa dollar real"),
    ("Israel", "Tel Aviv stock market shekel"),
]

SYSTEM_PROMPT = (
    "You are a financial market analyst writing the daily bulletin for a family portfolio, "
    "in English. Use only the data and headlines provided. "
    "Required structure, with no title at the top of the text:\n"
    "1. At most four short paragraphs, up to three sentences each, summarizing the day: how the "
    "markets, FX and the portfolio result by bank closed.\n"
    "2. A section called 'Top gainers' and another called 'Top losers', with one bullet per asset, "
    "stating the asset, the day's move and the cause, if a headline explains the move.\n"
    "3. A section called 'Macro', with one bullet for each region: US, Europe, China, Brazil and Israel, "
    "summarizing what the headlines say about the day.\n"
    "Rules: do not invent numbers, news or causes. If no headline explains a move, do not mention "
    "the cause: just state the asset and the move, or skip the region if it has no headline. "
    "Do not use asterisks or markdown. Do not recommend buying or selling."
)


def buscar_noticias() -> list:
    noticias = []
    for label, query in NEWS_QUERIES:
        url = (
            "https://news.google.com/rss/search?"
            + urllib.parse.urlencode({"q": f"{query} when:1d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
        )
        try:
            with urllib.request.urlopen(url, timeout=10) as resposta:
                raiz = ET.fromstring(resposta.read())
            for item in list(raiz.iter("item"))[:MAX_HEADLINES]:
                titulo = item.findtext("title", "").strip()
                if titulo:
                    noticias.append({"tema": label, "titulo": titulo, "link": item.findtext("link", "").strip()})
        except Exception as e:
            logger.error(f"Failed to fetch news for {label}: {e}")
    return noticias


def buscar_manchetes() -> list:
    return [f"[{n['tema']}] {n['titulo']}" for n in buscar_noticias()]


def formatar_dados(market: dict, positions: list, today) -> str:
    linhas = [f"Date: {today:%d/%m/%Y}", "", "Markets (day change):"]
    for nome, v in market["mercados"]:
        linhas.append(f"- {nome}: " + ("unavailable" if not v else f"{v[1]:+.2f}%"))

    linhas += ["", "FX (1 USD):"]
    for nome, v in market["cambio"]:
        linhas.append(f"- {nome}: " + ("unavailable" if not v else f"{v[0]:.4f} ({v[1]:+.2f}%)"))

    linhas += ["", "Portfolio day return by bank (weighted by value):"]
    bancos = _group(positions, lambda p: p["banco"] or "-")
    for banco, g in bancos.items():
        dia = _dia_value(g)
        linhas.append(f"- {banco}: " + ("no data" if dia is None else f"{dia:+.2f}%"))

    linhas += ["", "Top gainers and losers by bank and type:"]
    for banco in bancos:
        grupo = [p for p in positions if (p["banco"] or "-") == banco]
        for type_key, type_label in TYPE_ORDER:
            destaques = _destaques(grupo, type_key)
            if destaques:
                itens = ", ".join(f"{p['ticker']} ({p.get('nome') or ''}) {_day_return(p):+.2f}%" for p in destaques)
                linhas.append(f"- {banco} / {type_label}: {itens}")

    manchetes = buscar_manchetes()
    linhas += ["", "Headlines of the day:"]
    linhas += [f"- {m}" for m in manchetes] if manchetes else ["- unavailable"]
    return "\n".join(linhas)


def gerar_boletim(dados: str) -> str:
    chave = os.getenv("ANTHROPIC_API_KEY", "")
    if not chave:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    from anthropic import Anthropic
    client = Anthropic(api_key=chave)
    resposta = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": dados}],
    )
    texto = "".join(bloco.text for bloco in resposta.content if getattr(bloco, "type", "") == "text")
    if not texto.strip():
        raise RuntimeError(f"boletim sem texto (stop_reason={resposta.stop_reason})")
    return texto


def _paragrafo(texto: str) -> str:
    return f"<p style='margin:0 0 10px;line-height:1.5'>{html.escape(texto)}</p>"


def _titulo(texto: str) -> str:
    return f"<div style='font-weight:bold;margin:14px 0 6px;color:#1e8449'>{html.escape(texto)}</div>"


def _lista(itens: list) -> str:
    return "<ul style='margin:0 0 10px;padding-left:20px'>" + "".join(
        f"<li style='margin:4px 0;line-height:1.5'>{html.escape(i)}</li>" for i in itens
    ) + "</ul>"


def _e_titulo(linha: str) -> bool:
    return len(linha) < 60 and (linha.endswith(":") or linha.lower().startswith(("top gainers", "top losers", "macro")))


def texto_para_html(texto: str) -> str:
    texto = texto.replace("**", "").replace("__", "").replace("#", "")
    partes = []
    bullets = []
    paragrafo = []

    def fechar_paragrafo():
        if paragrafo:
            partes.append(_paragrafo(" ".join(paragrafo)))
            paragrafo.clear()

    def fechar_lista():
        if bullets:
            partes.append(_lista(bullets))
            bullets.clear()

    for linha in (l.strip() for l in texto.splitlines()):
        if not linha:
            fechar_paragrafo()
            fechar_lista()
        elif linha.startswith(("- ", "• ")):
            fechar_paragrafo()
            bullets.append(linha[2:])
        elif _e_titulo(linha):
            fechar_paragrafo()
            fechar_lista()
            partes.append(_titulo(linha.rstrip(":")))
        else:
            fechar_lista()
            paragrafo.append(linha)
    fechar_paragrafo()
    fechar_lista()
    return "".join(partes)
