import pandas as pd
from data_provider import BrapiProvider
from analyzer import StockAnalyzer
from valuation import ValuationModels
import time

def run_valuation_pipeline(tickers):
    provider = BrapiProvider()
    results = []

    print(f"Starting analysis for {len(tickers)} stocks...")

    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Analyzing {ticker}...")
        
        # 1. Fetch data
        raw_data = provider.get_stock_data(ticker)
        if not raw_data:
            continue

        # 2. Extract and Calculate Ratios
        metrics = StockAnalyzer.extract_metrics(raw_data)
        if not metrics:
            continue

        # 3. Apply Valuation Models
        full_data = ValuationModels.apply_all(metrics)
        if full_data:
            results.append(full_data)
        
        # Small delay to respect API rate limits (optional depending on plan)
        time.sleep(0.1)

    if not results:
        print("No data collected.")
        return None

    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Ranking Logic
    # 1. Magic Formula Ranking (Rank by ROC and Yield, then sum ranks)
    df['roc_rank'] = df['magic_roc'].rank(ascending=False)
    df['yield_rank'] = df['magic_yield'].rank(ascending=False)
    df['magic_score'] = df['roc_rank'] + df['yield_rank']
    
    # 2. Final Sorting (By Upside or Magic Score)
    df = df.sort_values(by="upside", ascending=False)
    
    return df

if __name__ == "__main__":
    # Sample list of major Ibovespa stocks (Blue Chips)
    # In a real scenario, we could fetch the full list using provider.get_available_tickers()
    target_tickers = [
        "VALE3", "PETR4", "ITUB4", "BBDC4", "ABEV3", 
        "BBAS3", "ELET3", "WEGE3", "RENT3", "SANB11"
    ]

    try:
        df_results = run_valuation_pipeline(target_tickers)
        
        if df_results is not None:
            # Reorder columns for better readability
            cols = [
                'ticker', 'price', 'upside', 'valuation_graham', 'valuation_dcf', 
                'p_e', 'p_b', 'dividend_yield', 'roe', 'magic_score'
            ]
            display_df = df_results[cols]
            
            print("\n--- STOCK RANKING (Sorted by Upside) ---")
            print(display_df.to_string(index=False))
            
            # Save to CSV
            output_file = "valuation_results.csv"
            df_results.to_csv(output_file, index=False)
            print(f"\nResults saved to {output_file}")
            
            # Save to JSON for GitHub Pages
            json_file = "data.json"
            # Replace NaN/Inf with None for JSON
            df_json = df_results.replace([float('inf'), float('-inf')], None)
            df_json = df_json.where(df_json.notnull(), None)
            df_json.to_json(json_file, orient='records', indent=2)
            print(f"Results saved to {json_file}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
