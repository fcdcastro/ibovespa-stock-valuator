from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from main import run_valuation_pipeline
import os
import numpy as np

app = Flask(__name__)
CORS(app)

# Lista atualizada de 20 tickers (Mid/Small Caps)
TICKERS = [
    "ACER3.SA", "AZUL4.SA", "BEES3.SA", "BRFS3.SA", "CSAN3.SA",
    "CYRE3.SA", "EGIE3.SA", "HAPV3.SA", "HAGA3.SA", "IRBR3.SA",
    "LWSA3.SA", "MGLU3.SA", "QUAL3.SA", "RADL3.SA", "SUZB3.SA",
    "VAMO3.SA", "WEGE3.SA", "XPLG3.SA", "YDUQ3.SA", "ZAP3.SA"
]

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/valuation', methods=['GET'])
def get_valuation():
    try:
        # Executa o pipeline para os 20 tickers
        df = run_valuation_pipeline(TICKERS)
        
        if df is None or df.empty:
            return jsonify({"error": "Nenhum dado encontrado"}), 404
            
        # Trata valores NaN/Inf para JSON
        df = df.replace([np.inf, -np.inf], None)
        df = df.where(df.notnull(), None)
        
        results = df.to_dict(orient='records')
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Servidor iniciado em http://localhost:5000")
    app.run(debug=True, port=5000)
