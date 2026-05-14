import pandas as pd
import numpy as np
from data_provider import YahooFinanceProvider
from analyzer import StockAnalyzer
from valuation import ValuationModels
import time

from prediction import PredictionEngine

def run_valuation_pipeline(tickers):
    provider = YahooFinanceProvider()
    results = []

    print(f"Iniciando coleta inteligente de {len(tickers)} ativos...")

    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Processando {ticker}...")
        
        # 1. Buscar Dados via Yahoo Finance
        raw_data = provider.get_stock_data(ticker)
        if not raw_data:
            continue

        # 2. Extrair Métricas com Tratamento de Erros
        metrics = StockAnalyzer.extract_metrics(raw_data)
        if not metrics:
            print(f"[AVISO] {ticker}: Dados incompletos ou ativo inativo. Pulando.")
            continue

        # 3. Aplicar Modelos de Valuation
        full_data = ValuationModels.apply_all(metrics)
        if full_data:
            results.append(full_data)
            print(f"[OK] {ticker} capturado com sucesso.")
        
        time.sleep(0.5)

    if not results:
        print("❌ Nenhum dado foi coletado.")
        return None

    # Criar DataFrame
    df = pd.DataFrame(results)
    
    # --- TRATAMENTO DE DADOS INTELIGENTE ---
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    
    # Magic Formula
    if 'magic_roc' in df.columns and 'magic_yield' in df.columns:
        df['roc_rank'] = df['magic_roc'].rank(ascending=False)
        df['yield_rank'] = df['magic_yield'].rank(ascending=False)
        df['magic_score'] = df['roc_rank'] + df['yield_rank']
    
    # 4. Inteligencia Preditiva (Regressao)
    engine = PredictionEngine()
    df, model_metrics = engine.train_and_predict(df)
    
    # Ordenacao Final
    df = df.sort_values(by="expected_return", ascending=False)
    
    return df, model_metrics

if __name__ == "__main__":
    target_tickers = [
        "CYRE3.SA", "EGIE3.SA", "HAPV3.SA", "IRBR3.SA", "LWSA3.SA",
        "MGLU3.SA", "QUAL3.SA", "RADL3.SA", "SUZB3.SA", "VAMO3.SA",
        "WEGE3.SA", "YDUQ3.SA", "BEES3.SA", "CSAN3.SA", "HAGA3.SA"
    ]

    try:
        df_results, model_metrics = run_valuation_pipeline(target_tickers)
        
        if df_results is not None:
            # Salvar CSV
            output_file = "carteira_fundamentalista_limpa.csv"
            df_results.to_csv(output_file, index=False, sep=";")
            
            # Salvar JSON com Metadados do Modelo
            df_json = df_results.replace([np.inf, -np.inf], None)
            df_json = df_json.where(df_json.notnull(), None)
            
            final_output = {
                "stocks": df_json.to_dict(orient='records'),
                "model_info": model_metrics,
                "last_update": time.strftime("%d/%m/%Y %H:%M:%S")
            }
            
            import json
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(final_output, f, indent=2)
            
            print(f"\n[SUCESSO] Dados salvos com predicoes. R2 do modelo: {model_metrics['r2']:.4f}")
            
    except Exception as e:
        print(f"Erro critico no pipeline: {e}")
        import traceback
        traceback.print_exc()

