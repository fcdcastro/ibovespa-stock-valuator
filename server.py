from flask import Flask, jsonify, send_from_directory
from datetime import datetime, timedelta
from flask_cors import CORS
from main import run_valuation_pipeline
from correlation import CorrelationEngine
import os
import json
import numpy as np
import time
import threading

app = Flask(__name__)
CORS(app)

TICKERS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", 
    "ABEV3.SA", "WEGE3.SA", "SUZB3.SA", "MGLU3.SA", "CYRE3.SA",
    "AZUL4.SA", "BEES3.SA", "HAGA3.SA", "IRBR3.SA", "LWSA3.SA", 
    "QUAL3.SA", "VAMO3.SA", "YDUQ3.SA", "JHSF3.SA", "POMO4.SA"
]

DATA_FILE = "data.json"
CACHE_TTL = 300

_cache = {
    "data": None,
    "timestamp": 0.0,
    "lock": threading.Lock()
}

def _is_cache_valid():
    return (time.time() - _cache["timestamp"]) < CACHE_TTL

def _load_data_json():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/valuation', methods=['GET'])
def get_valuation():
    with _cache["lock"]:
        if _cache["data"] is not None and _is_cache_valid():
            return jsonify(_cache["data"])

    # Primeiro tenta carregar do data.json (pre-computado)
    cached = _load_data_json()
    if cached and "stocks" in cached:
        with _cache["lock"]:
            _cache["data"] = cached
            _cache["timestamp"] = time.time()
        return jsonify(cached)

    # Fallback: executa pipeline (pode demorar)
    try:
        df, model_metrics = run_valuation_pipeline(TICKERS)
        if df is None or df.empty:
            return jsonify({"error": "Nenhum dado encontrado"}), 404

        df = df.replace([np.inf, -np.inf], None)
        df = df.where(df.notnull(), None)
        results = {
            "stocks": df.to_dict(orient='records'),
            "model_info": model_metrics,
            "last_update": time.strftime("%d/%m/%Y %H:%M:%S")
        }

        with _cache["lock"]:
            _cache["data"] = results
            _cache["timestamp"] = time.time()
        return jsonify(results)
    except Exception as e:
        with _cache["lock"]:
            if _cache["data"] is not None:
                return jsonify(_cache["data"])
        return jsonify({"error": str(e)}), 500

_corr_engine = CorrelationEngine()

@app.route('/api/correlation', methods=['GET'])
def get_correlation():
    from flask import request
    start = request.args.get('start', (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    result = _corr_engine.calculate(start, end)
    return jsonify(result)

if __name__ == '__main__':
    print("Servidor iniciado em http://localhost:5000")
    app.run(debug=True, port=5000)
