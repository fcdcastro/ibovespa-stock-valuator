class StockAnalyzer:
    @staticmethod
    def extract_metrics(data):
        """
        Extracts key financial metrics from Brapi JSON response.
        """
        if not data:
            return None

        summary = {
            "ticker": data.get("symbol"),
            "price": data.get("regularMarketPrice"),
            "market_cap": data.get("marketCap"),
            "dividend_yield": data.get("dividendYield", 0) * 100 if data.get("dividendYield") else 0,
        }

        # Fundamental Data from modules
        fundamental = {}
        
        def clean_val(v):
            return v if v is not None else 0

        # Get latest data from Income Statement
        if "incomeStatementHistory" in data:
            statements = data["incomeStatementHistory"]
            if isinstance(statements, list) and statements:
                latest = statements[0]
                fundamental["net_income"] = clean_val(latest.get("netIncome"))
                fundamental["ebitda"] = clean_val(latest.get("ebitda"))
                fundamental["revenue"] = clean_val(latest.get("totalRevenue"))
        
        # Get latest data from Balance Sheet
        if "balanceSheetHistory" in data:
            statements = data["balanceSheetHistory"]
            if isinstance(statements, list) and statements:
                latest = statements[0]
                fundamental["total_assets"] = clean_val(latest.get("totalAssets"))
                fundamental["total_equity"] = clean_val(latest.get("totalStockholderEquity"))
                fundamental["total_debt"] = clean_val(latest.get("totalDebt"))
                fundamental["total_liabilities"] = clean_val(latest.get("totalLiab"))
                
                # Fallback for Equity
                if fundamental["total_equity"] == 0 and fundamental["total_assets"] > 0:
                    fundamental["total_equity"] = fundamental["total_assets"] - fundamental["total_liabilities"]

        summary.update(fundamental)

        # Derived Ratios
        price = summary.get("price", 0)
        market_cap = summary.get("market_cap", 0)
        
        # Estimate shares outstanding
        shares_outstanding = 0
        if market_cap > 0 and price > 0:
            shares_outstanding = market_cap / price
            
        # EPS (Prefer API provided EPS if available)
        summary["eps"] = data.get("earningsPerShare", 0)
        if summary["eps"] == 0 and shares_outstanding > 0:
            summary["eps"] = fundamental.get("net_income", 0) / shares_outstanding
            
        # BVPS (Book Value Per Share)
        summary["bvps"] = 0
        if shares_outstanding > 0:
            summary["bvps"] = fundamental.get("total_equity", 0) / shares_outstanding

        # Ratio Calculations
        if summary.get("eps", 0) != 0:
            summary["p_e"] = summary["price"] / summary["eps"]
        else:
            summary["p_e"] = data.get("priceEarnings", float('inf'))

        if summary.get("bvps", 0) != 0:
            summary["p_b"] = summary["price"] / summary["bvps"]
        else:
            summary["p_b"] = float('inf')

        if summary.get("total_equity", 0) != 0:
            summary["roe"] = (summary.get("net_income", 0) / summary["total_equity"]) * 100
        else:
            summary["roe"] = 0

        if summary.get("revenue", 0) != 0:
            summary["ebitda_margin"] = (summary.get("ebitda", 0) / summary["revenue"]) * 100
        else:
            summary["ebitda_margin"] = 0

        if summary.get("total_equity", 0) != 0:
            summary["debt_equity"] = summary.get("total_debt", 0) / summary["total_equity"]
        else:
            summary["debt_equity"] = float('inf')

        return summary
