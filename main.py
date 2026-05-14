import pandas as pd
import numpy as np
from data_provider import YahooFinanceProvider
from analyzer import StockAnalyzer
from valuation import ValuationModels
import time

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
            # Se não retornar métricas (ex: sem preço), o analyzer retorna None
            print(f"[AVISO] {ticker}: Dados incompletos ou ativo inativo. Pulando.")
            continue

        # 3. Aplicar Modelos de Valuation
        full_data = ValuationModels.apply_all(metrics)
        if full_data:
            results.append(full_data)
            print(f"[OK] {ticker} capturado com sucesso.")
        
        # Delay de 0.5s para evitar bloqueio (Rate Limit)
        time.sleep(0.5)

    if not results:
        print("❌ Nenhum dado foi coletado.")
        return None

    # Criar DataFrame
    df = pd.DataFrame(results)
    
    # --- TRATAMENTO DE DADOS INTELIGENTE (Sugestão do Usuário) ---
    
    # 1. Preencher lacunas numéricas com a mediana para não perder a linha
    # Apenas para colunas numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    
    # 2. Lógica de Ranking Magic Formula
    if 'magic_roc' in df.columns and 'magic_yield' in df.columns:
        df['roc_rank'] = df['magic_roc'].rank(ascending=False)
        df['yield_rank'] = df['magic_yield'].rank(ascending=False)
        df['magic_score'] = df['roc_rank'] + df['yield_rank']
    
    # 3. Ordenação Final (Aqui ordenamos por ROE conforme o exemplo, mas mantemos Upside como principal)
    df = df.sort_values(by="upside", ascending=False)
    
    return df

if __name__ == "__main__":
    # Nova lista de tickers de 2ª linha (Mid/Small Caps) fornecida pelo usuário
    target_tickers = [
        "ACER3.SA", "AZUL4.SA", "BEES3.SA", "BRFS3.SA", "CSAN3.SA",
        "CYRE3.SA", "EGIE3.SA", "HAPV3.SA", "HAGA3.SA", "IRBR3.SA",
        "LWSA3.SA", "MGLU3.SA", "QUAL3.SA", "RADL3.SA", "SUZB3.SA",
        "VAMO3.SA", "WEGE3.SA", "XPLG3.SA", "YDUQ3.SA", "ZAP3.SA"
    ]

    try:
        df_results = run_valuation_pipeline(target_tickers)
        
        if df_results is not None:
            # Selecionar colunas para o resumo no terminal (estilo o exemplo do usuário)
            resumo_cols = ['ticker', 'p_e', 'p_b', 'roe', 'dividend_yield', 'upside']
            # Garantir que as colunas existem
            resumo_cols = [c for c in resumo_cols if c in df_results.columns]
            
            print("\n--- DADOS PROCESSADOS PARA ANÁLISE ---")
            print(df_results[resumo_cols].head(10).to_string(index=False))
            
            # Salvar CSV Limpo (Usando separador ";" conforme solicitado para Excel)
            output_file = "carteira_fundamentalista_limpa.csv"
            df_results.to_csv(output_file, index=False, sep=";")
            
            # Manter compatibilidade com o Dashboard (data.json)
            df_json = df_results.replace([np.inf, -np.inf], None)
            df_json = df_json.where(df_json.notnull(), None)
            df_json.to_json("data.json", orient='records', indent=2)
            
            print(f"\nSucesso! Dados salvos em '{output_file}' e 'data.json'.")
            
    except Exception as e:
        print(f"Erro critico no pipeline: {e}")
        import traceback
        traceback.print_exc()
