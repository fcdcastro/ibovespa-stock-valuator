class StockAnalyzer:
    @staticmethod
    def extract_metrics(data):
        """
        Extrai métricas financeiras chave do yfinance (info) com tratamento inteligente.
        Segue a abordagem robusta para lidar com dados ausentes em Small/Mid Caps.
        """
        if not data:
            return None

        def clean_val(v, default=0):
            # Se for None ou string vazia, retorna o default
            if v is None or v == "":
                return default
            # Tenta converter para float se possível
            try:
                return float(v)
            except (ValueError, TypeError):
                return default

        # Identificação
        raw_symbol = data.get("symbol", "")
        ticker = raw_symbol.replace(".SA", "")

        # Validação de Preço (Critério de exclusão sugerido)
        price = data.get('currentPrice') or data.get('regularMarketPrice')
        if price is None:
            return None

        # Dicionário de métricas baseado na sugestão do usuário
        summary = {
            "ticker": ticker,
            "name": data.get("longName") or data.get("shortName") or ticker,
            "price": clean_val(price),
            "p_e": clean_val(data.get('trailingPE')),
            "p_b": clean_val(data.get('priceToBook')),
            "dividend_yield": clean_val(data.get('dividendYield'), 0) * 100,
            "roe": clean_val(data.get('returnOnEquity'), 0) * 100,
            "roa": clean_val(data.get('returnOnAssets'), 0) * 100,
            "net_margin": clean_val(data.get('profitMargins'), 0) * 100,
            "debt_equity": clean_val(data.get('debtToEquity'), 0) / 100,
            "revenue": clean_val(data.get('totalRevenue')),
            "net_income": clean_val(data.get('netIncomeToCommon')),
            "volume": clean_val(data.get('averageVolume')),
            "sector": data.get('sector', 'N/A'),
            "industry": data.get('industry', 'N/A'),
            "market_cap": clean_val(data.get('marketCap')),
            "eps": clean_val(data.get('trailingEps')),
            "total_assets": clean_val(data.get('totalAssets')),
            "total_equity": clean_val(data.get('totalStockholderEquity')),
        }

        # Cálculos Derivados (Necessários para os modelos de Valuation)
        
        # BVPS (Book Value Per Share)
        summary["bvps"] = clean_val(data.get("bookValue"))
        if summary["bvps"] == 0 and summary["p_b"] != 0:
            summary["bvps"] = summary["price"] / summary["p_b"]
            
        # EBITDA (Importante para Magic Formula)
        summary["ebitda"] = clean_val(data.get("ebitda"))

        return summary
