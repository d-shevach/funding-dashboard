"""Flask web dashboard for portfolio"""

import time
from datetime import timedelta
from functools import wraps
from flask import Flask, Response, render_template, jsonify, request, redirect, url_for, session
from datetime import datetime
from src.config import Config
from src.database import Database, DatabasePool
from src.automation.tasks import ReportGenerationTask
from src.logger import get_logger
from src.web.auth import ensure_users_table, verify_credentials
from src.automation.returns import ensure_return_columns
from src.automation.monthly_returns import ensure_monthly_returns_table, ensure_benchmark_table, list_monthly_returns

logger = get_logger("web.app")

app = Flask(__name__, template_folder="templates")
app.config["JSON_SORT_KEYS"] = False
app.secret_key = Config.FLASK_SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=5)

# Initialize database on startup
with app.app_context():
    DatabasePool.initialize()
    ensure_users_table()
    ensure_return_columns()
    ensure_monthly_returns_table()
    ensure_benchmark_table()


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("usuario"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "unauthorized"}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    aviso = "Session ended due to inactivity. Please log in again." if request.args.get("motivo") == "inatividade" else None
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        if verify_credentials(usuario, senha):
            session.clear()
            session.permanent = True
            session["usuario"] = usuario
            destino = request.args.get("next", "")
            if not destino.startswith("/") or destino.startswith("//"):
                destino = url_for("index")
            return redirect(destino)
        erro = "Invalid user or password"
    return render_template("login.html", erro=erro, aviso=aviso)


@app.route("/logout")
def logout():
    motivo = request.args.get("motivo")
    session.clear()
    if motivo == "inatividade":
        return redirect(url_for("login", motivo="inatividade"))
    return redirect(url_for("login"))


def format_currency(value):
    """Format value as currency"""
    if value is None:
        return "$0.00"
    try:
        return f"${float(value):,.2f}"
    except:
        return "$0.00"


app.jinja_env.filters["currency"] = format_currency


@app.route("/")
@login_required
def index():
    """Main dashboard page"""
    try:
        summary = ReportGenerationTask.generate_summary()
        breakdown = ReportGenerationTask.generate_by_asset_type()

        return render_template(
            "dashboard.html",
            summary=summary,
            breakdown=breakdown,
            last_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template("error.html", error=str(e)), 500


@app.route("/api/portfolio")
@login_required
def api_portfolio():
    """Get portfolio data as JSON"""
    try:
        from src.models import Portfolio
        from datetime import date

        positions = Portfolio.get_all_positions()
        today = date.today()

        def calculate_returns(purchase_date, valor_atual, valor_investido, saldo_m1, retorno_mes, retorno_ano):
            """Calculate Daily, MTD, YTD and Total returns"""
            if not valor_investido or valor_investido == 0:
                return None, None, 0

            try:
                valor_atual = float(valor_atual) if valor_atual else 0
                valor_investido = float(valor_investido) if valor_investido else 0
                saldo_m1 = float(saldo_m1) if saldo_m1 else 0
                retorno_mes = float(retorno_mes) if retorno_mes else 0
                retorno_ano = float(retorno_ano) if retorno_ano else 0

                # Total return: from purchase to today
                total_return = ((valor_atual - valor_investido) / valor_investido * 100) if valor_investido else 0

                if saldo_m1 and saldo_m1 > 0:
                    mtd_return = ((valor_atual - saldo_m1) / saldo_m1 * 100)
                elif retorno_mes and retorno_mes != 0:
                    mtd_return = retorno_mes
                else:
                    mtd_return = None

                ytd_return = retorno_ano if retorno_ano and retorno_ano != 0 else None

                return mtd_return, ytd_return, total_return
            except Exception as e:
                return None, None, 0

        def d1_return(p):
            if p.get("fechamento_d1") and p.get("fechamento_d2"):
                return (float(p["fechamento_d1"]) / float(p["fechamento_d2"]) - 1) * 100
            return None

        def intraday_return(p, d1):
            hora = p.get("hora_intraday")
            if p.get("preco_intraday") and p.get("fechamento_d1") and hora and hora.date() == today:
                return (float(p["preco_intraday"]) / float(p["fechamento_d1"]) - 1) * 100
            return d1

        result_positions = []
        for i, p in enumerate(positions):
            mtd, ytd, total = calculate_returns(
                p.get("data"),
                p.get("valor_atual"),
                p.get("valor_investido"),
                p.get("saldo_m1"),
                p.get("retorno_mes"),
                p.get("retorno_ano")
            )

            is_mutual_fund = p.get("tipo") in ("Fund", "Fundo")
            d1 = None if is_mutual_fund else d1_return(p)
            intraday = None if is_mutual_fund else intraday_return(p, d1)

            valor_hoje = float(p["valor_atual"]) if p["valor_atual"] else 0.0
            if not is_mutual_fund and p.get("preco_intraday") and p.get("fechamento_d1") and p.get("hora_intraday") and p["hora_intraday"].date() == today:
                valor_hoje *= float(p["preco_intraday"]) / float(p["fechamento_d1"])
            diferenca_hoje = valor_hoje - (float(p["valor_investido"]) if p["valor_investido"] else 0.0)

            mtd_rounded = None if is_mutual_fund or mtd is None else round(mtd, 2)
            ytd_rounded = None if is_mutual_fund or ytd is None else round(ytd, 2)
            investido_base = float(p["valor_investido"]) if p["valor_investido"] else 0.0
            total_rounded = round((valor_hoje - investido_base) / investido_base * 100, 2) if investido_base else 0

            pos_dict = {
                "id": p["id"],
                "nome": p["nome"],
                "tipo": p["tipo"],
                "ticker": p["ticker"],
                "banco": p["banco"],
                "moeda": p["moeda"],
                "setor": p.get("setor"),
                "data": str(p.get("data")) if p.get("data") else "-",
                "preco_compra": float(p["preco_compra"]) if p["preco_compra"] else 0,
                "quantidade": float(p["quantidade"]) if p["quantidade"] else 0,
                "valor_investido": float(p["valor_investido"]) if p["valor_investido"] else 0,
                "preco_atual": float(p["preco_atual"]) if p["preco_atual"] else 0,
                "valor_atual": round(valor_hoje, 2),
                "diferenca": round(diferenca_hoje, 2),
                "percentual": float(p["percentual"]) if p["percentual"] else 0,
                "d1": round(d1, 2) if d1 is not None else None,
                "intraday": round(intraday, 2) if intraday is not None else None,
                "mtd": mtd_rounded,
                "ytd": ytd_rounded,
                "total": total_rounded,
            }
            result_positions.append(pos_dict)

        return jsonify({
            "success": True,
            "positions": result_positions,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/monthly_returns")
@login_required
def api_monthly_returns():
    return jsonify({"success": True, "data": list_monthly_returns()})


_cache = {}


def _cached(chave, ttl_segundos, buscar):
    agora = time.time()
    if chave not in _cache or agora - _cache[chave][0] > ttl_segundos:
        _cache[chave] = (agora, buscar())
    return _cache[chave][1]


@app.route("/api/market")
@login_required
def api_market():
    from src.automation.market_summary import get_market_summary
    return jsonify({"success": True, "data": _cached("market", 600, get_market_summary)})


@app.route("/caixa-dividendos")
@login_required
def caixa_dividendos_page():
    return render_template("caixa.html")


@app.route("/api/caixa_dividendos")
@login_required
def api_caixa_dividendos():
    from src.automation.caixa import caixa_dividendos
    return jsonify({"success": True, "data": caixa_dividendos()})


def _csv_response(nome: str, cabecalho: list, linhas: list):
    import csv
    import io
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return Response(
        "﻿" + saida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


@app.route("/api/export/posicoes.csv")
@login_required
def export_posicoes():
    posicoes = api_portfolio().get_json()["positions"]
    cabecalho = ["banco", "tipo", "nome", "ticker", "moeda", "valor_investido", "valor_atual",
                 "ganho_perda", "retorno_total_pct", "intraday_pct", "d1_pct", "mtd_pct", "ytd_pct"]
    linhas = [
        [p["banco"], p["tipo"], p["nome"], p["ticker"], p["moeda"], p["valor_investido"], p["valor_atual"],
         p["diferenca"], p["total"], p["intraday"], p["d1"], p["mtd"], p["ytd"]]
        for p in posicoes
    ]
    return _csv_response("posicoes.csv", cabecalho, linhas)


@app.route("/api/export/retornos.csv")
@login_required
def export_retornos():
    dados = list_monthly_returns()
    cabecalho = ["serie", "ano", "mes", "retorno_mes_pct", "acumulado_no_ano_pct", "acumulado_pct"]
    linhas = [
        [serie, m["ano"], m["mes"], m["retorno"], m["acumulado_ano"], m["acumulado"]]
        for serie, s in dados.items() for m in s["meses"]
    ]
    return _csv_response("retornos.csv", cabecalho, linhas)


@app.route("/api/news")
@login_required
def api_news():
    from src.automation.boletim import buscar_noticias
    return jsonify({"success": True, "data": _cached("news", 1800, buscar_noticias)})


@app.route("/api/summary")
@login_required
def api_summary():
    """Get portfolio summary as JSON"""
    try:
        summary = ReportGenerationTask.generate_summary()

        return jsonify({
            "success": True,
            "data": {
                "total_positions": summary["total_positions"],
                "asset_types": summary["asset_types"],
                "total_invested": float(summary["total_invested"]),
                "total_current": float(summary["total_current"]),
                "total_gain_loss": float(summary["total_gain_loss"]),
                "roi_percent": summary["roi_percent"],
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/breakdown")
@login_required
def api_breakdown():
    """Get asset breakdown as JSON"""
    try:
        breakdown = ReportGenerationTask.generate_by_asset_type()

        return jsonify({
            "success": True,
            "data": [
                {
                    "asset_type": b["asset_type"],
                    "count": b["count"],
                    "total_invested": float(b["total_invested"]),
                    "total_current": float(b["total_current"]),
                    "total_gain_loss": float(b["total_gain_loss"]),
                }
                for b in breakdown
            ],
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting breakdown: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template("error.html", error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return render_template("error.html", error="Internal server error"), 500


if __name__ == "__main__":
    logger.info("Starting web dashboard")
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )
