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

    # Lista simplificada das principais componentes do Ibovespa para classificacao
    ibov_components = [
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "B3SA3.SA", 
        "WEGE3.SA", "SUZB3.SA", "RENT3.SA", "LREN3.SA", "JBSS3.SA", "RADL3.SA", "EQTL3.SA",
        "ELET3.SA", "ELET6.SA", "HAPV3.SA", "PRIO3.SA", "RDOR3.SA", "RAIL3.SA", "SBSP3.SA",
        "VIVT3.SA", "BBSE3.SA", "CPLE6.SA", "CMIG4.SA", "CCRO3.SA", "CSNA3.SA", "GGBR4.SA",
        "USIM5.SA", "BRFS3.SA", "TOTS3.SA", "ASAI3.SA", "NTCO3.SA", "KLBN11.SA", "TIMS3.SA",
        "BPAC11.SA", "CSAN3.SA", "MGLU3.SA", "EGIE3.SA", "CPFE3.SA", "CYRE3.SA", "MULT3.SA",
        "VBBR3.SA", "CRFB3.SA", "ENGI11.SA", "TAEE11.SA", "TRPL4.SA", "ALOS3.SA", "IGTI11.SA"
    ]

    for res in results:
        res['category'] = 'IBOVESPA' if f"{res['ticker']}.SA" in ibov_components else 'SMALL_CAP'

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
        "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "B3SA3.SA", "ITSA4.SA", "JBSS3.SA", "RENT3.SA",
        "LREN3.SA", "WEGE3.SA", "SUZB3.SA", "GGBR4.SA", "CSNA3.SA", "USIM5.SA", "EMBR3.SA", "CPLE6.SA", "EQTL3.SA", "RADL3.SA",
        "RAIL3.SA", "SBSP3.SA", "VIVT3.SA", "HYPE3.SA", "ELET3.SA", "ELET6.SA", "BRFS3.SA", "CCRO3.SA", "RDOR3.SA", "BPAC11.SA",
        "KLBN11.SA", "SANB11.SA", "CRFB3.SA", "TOTS3.SA", "ASAI3.SA", "NTCO3.SA", "SLCE3.SA", "ENGI11.SA", "TRPL4.SA", "TAEE11.SA",
        "GOAU4.SA", "MRVE3.SA", "CYRE3.SA", "MULT3.SA", "IGTI11.SA", "ALOS3.SA", "BRAP4.SA", "CMIG4.SA", "CPFE3.SA", "CSMG3.SA",
        "EGIE3.SA", "PRIO3.SA", "VBBR3.SA", "RRRP3.SA", "RECV3.SA", "PSSA3.SA", "BBSE3.SA", "IRBR3.SA", "AZUL4.SA", "MOVI3.SA",
        "STBP3.SA", "TIMS3.SA", "FLRY3.SA", "QUAL3.SA", "DXCO3.SA", "BEEF3.SA", "MRFG3.SA", "CAML3.SA", "SMTO3.SA", "JHSF3.SA",
        "EZTC3.SA", "DIRR3.SA", "CURY3.SA", "TEND3.SA", "GFSA3.SA", "MYPK3.SA", "EVEN3.SA", "PCAR3.SA", "BHIA3.SA", "LJQQ3.SA",
        "AMBP3.SA", "SIMH3.SA", "VAMO3.SA", "POSI3.SA", "KEPL3.SA", "UNIP6.SA", "RANI3.SA", "KLBN4.SA", "AESB3.SA", "ENAT3.SA",
        "ROMI3.SA", "SHUL4.SA", "LEVE3.SA", "FRAS3.SA", "POMO4.SA", "RAPT4.SA", "TGMA3.SA", "WIZC3.SA", "PARD3.SA", "HAPV3.SA",
        "LWSA3.SA", "YDUQ3.SA", "COGN3.SA", "BEES3.SA", "HAGA3.SA"
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

            with open("data.js", "w", encoding="utf-8") as f:
                f.write("window.__STOCK_DATA__ = ")
                json.dump(final_output, f)
                f.write(";\n")
            
            print(f"\n[SUCESSO] Dados salvos com predicoes. R2 do modelo: {model_metrics['r2']:.4f}")

            print("\n--- Gerando dados de correlação com Ibovespa ---")
            from correlation import CorrelationEngine
            from datetime import datetime
            _corr_engine = CorrelationEngine()
            _end = datetime.now()
            _all_periods = {}
            for _y in [1, 3, 5]:
                _start = _end.replace(year=_end.year - _y)
                _data = _corr_engine.calculate(_start.strftime("%Y-%m-%d"), _end.strftime("%Y-%m-%d"))
                if "error" not in _data:
                    _all_periods[str(_y)] = _data
                    print(f"  Correlação {_y} ano(s): {_data['total_tickers']} ativos")
            with open("correlation_data.js", "w", encoding="utf-8") as f:
                f.write("window.__CORRELATION_DATA__ = ")
                json.dump(_all_periods, f)
                f.write(";\n")
            print("[OK] correlation_data.js gerado.\n")

    except Exception as e:
        print(f"Erro critico no pipeline: {e}")
        import traceback
        traceback.print_exc()

