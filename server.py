from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from main import run_valuation_pipeline
import os
import numpy as np
import time
import threading

app = Flask(__name__)
CORS(app)

# Lista atualizada de 20 tickers (10 Ibovespa e 10 Small/Mid Caps)
TICKERS = [
    # IBOVESPA
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", 
    "ABEV3.SA", "WEGE3.SA", "SUZB3.SA", "MGLU3.SA", "CYRE3.SA",
    # SMALL/MID CAPS
    "AZUL4.SA", "BEES3.SA", "HAGA3.SA", "IRBR3.SA", "LWSA3.SA", 
    "QUAL3.SA", "VAMO3.SA", "YDUQ3.SA", "JHSF3.SA", "POMO4.SA"
]

# ── Cache simples com TTL ────────────────────────────────────────────────
CACHE_TTL = 300  # 5 minutos em segundos

_cache = {
    "data": None,
    "timestamp": 0.0,
    "lock": threading.Lock()
}

def _is_cache_valid():
    return (time.time() - _cache["timestamp"]) < CACHE_TTL

def _build_response(df, model_metrics):
    df = df.replace([np.inf, -np.inf], None)
    df = df.where(df.notnull(), None)
    return {
        "stocks": df.to_dict(orient='records'),
        "model_info": model_metrics,
        "last_update": time.strftime("%d/%m/%Y %H:%M:%S")
    }

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/valuation', methods=['GET'])
def get_valuation():
    # Retorna cache se ainda estiver válido
    with _cache["lock"]:
        if _cache["data"] is not None and _is_cache_valid():
            return jsonify(_cache["data"])

    try:
        df, model_metrics = run_valuation_pipeline(TICKERS)

        if df is None or df.empty:
            return jsonify({"error": "Nenhum dado encontrado"}), 404

        results = _build_response(df, model_metrics)

        # Atualiza cache
        with _cache["lock"]:
            _cache["data"] = results
            _cache["timestamp"] = time.time()

        return jsonify(results)
    except Exception as e:
        # Se o cache expirou mas temos dados antigos, serve como fallback
        with _cache["lock"]:
            if _cache["data"] is not None:
                return jsonify(_cache["data"])
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Servidor iniciado em http://localhost:5000")
    app.run(debug=True, port=5000)
