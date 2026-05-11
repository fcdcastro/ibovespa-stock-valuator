from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from main import run_valuation_pipeline
import os

app = Flask(__name__)
CORS(app)

# Default list of stocks (you can expand this)
TICKERS = ["VALE3", "PETR4", "ITUB4", "MGLU3", "BBDC4", "BBAS3", "ABEV3", "WEGE3"]

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/valuation', methods=['GET'])
def get_valuation():
    try:
        # Run the existing pipeline logic
        df = run_valuation_pipeline(TICKERS)
        
        if df is None or df.empty:
            return jsonify({"error": "No data found"}), 404
            
        # Convert DataFrame to JSON serializable list
        # Replace NaN/Inf with None (null in JSON)
        df = df.replace([float('inf'), float('-inf')], None)
        df = df.where(df.notnull(), None)
        
        results = df.to_dict(orient='records')
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Server starting at http://localhost:5000")
    app.run(debug=True, port=5000)
