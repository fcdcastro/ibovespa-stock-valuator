import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

IBOV_COMPONENTS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA", "B3SA3.SA",
    "WEGE3.SA", "SUZB3.SA", "RENT3.SA", "LREN3.SA", "JBSS3.SA", "RADL3.SA", "EQTL3.SA",
    "ELET3.SA", "ELET6.SA", "HAPV3.SA", "PRIO3.SA", "RDOR3.SA", "RAIL3.SA", "SBSP3.SA",
    "VIVT3.SA", "BBSE3.SA", "CPLE6.SA", "CMIG4.SA", "CCRO3.SA", "CSNA3.SA", "GGBR4.SA",
    "USIM5.SA", "BRFS3.SA", "TOTS3.SA", "ASAI3.SA", "NTCO3.SA", "KLBN11.SA", "TIMS3.SA",
    "BPAC11.SA", "CSAN3.SA", "MGLU3.SA", "EGIE3.SA", "CPFE3.SA", "CYRE3.SA", "MULT3.SA",
    "VBBR3.SA", "CRFB3.SA", "ENGI11.SA", "TAEE11.SA", "TRPL4.SA", "ALOS3.SA", "IGTI11.SA"
]

TICKERS = [
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

IBOV_INDEX = "^BVSP"

def classify_ticker(ticker):
    return "IBOVESPA" if ticker in IBOV_COMPONENTS else "SMALL_CAP"

class CorrelationEngine:
    def __init__(self):
        self._cache = {}
        self._cache_timestamp = 0
        self.CACHE_TTL = 3600

    def _is_cache_valid(self):
        return (time.time() - self._cache_timestamp) < self.CACHE_TTL

    def _fetch_prices(self, tickers, start_date, end_date):
        prices = {}
        ibov = yf.download(IBOV_INDEX, start=start_date, end=end_date, auto_adjust=True, progress=False)
        if not ibov.empty and len(ibov) > 1:
            close_col = 'Close' if 'Close' in ibov.columns else ibov.columns[0]
            s = ibov[close_col].dropna()
            prices[IBOV_INDEX] = s if isinstance(s, pd.Series) else s.squeeze()

        batch_size = 20
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            try:
                data = yf.download(batch, start=start_date, end=end_date, auto_adjust=True, progress=False, group_by='ticker')
                if data.empty:
                    continue
                for t in batch:
                    try:
                        if isinstance(data.columns, pd.MultiIndex):
                            prices[t] = data[t]['Close'].dropna()
                        else:
                            prices[t] = data['Close'].dropna()
                    except Exception:
                        prices[t] = pd.Series(dtype=float)
            except Exception:
                for t in batch:
                    prices[t] = pd.Series(dtype=float)
        return prices

    def calculate(self, start_date, end_date):
        cache_key = f"{start_date}_{end_date}"
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]

        print(f"Buscando dados de {start_date} a {end_date}...")
        prices = self._fetch_prices(TICKERS, start_date, end_date)

        if IBOV_INDEX not in prices or prices[IBOV_INDEX].empty:
            return {"error": "Não foi possível obter dados do Ibovespa.", "results": [], "total_tickers": 0}

        ibov_returns = prices[IBOV_INDEX].pct_change().dropna()
        results = []

        for ticker in TICKERS:
            if ticker not in prices or prices[ticker].empty:
                continue

            stock_returns = prices[ticker].pct_change().dropna()
            common_dates = ibov_returns.index.intersection(stock_returns.index)
            if len(common_dates) < 30:
                continue

            r1 = ibov_returns.loc[common_dates]
            r2 = stock_returns.loc[common_dates]
            corr = r1.corr(r2)
            beta_val = r1.cov(r2) / r1.var() if r1.var() > 0 else 0
            covariance_val = r1.cov(r2)

            results.append({
                "ticker": ticker.replace(".SA", ""),
                "category": classify_ticker(ticker),
                "correlation": round(float(corr), 4),
                "beta": round(float(beta_val), 4),
                "covariance": round(float(covariance_val), 6),
                "data_points": len(common_dates),
                "stock_volatility": round(float(r2.std() * 100), 2),
                "ibov_volatility": round(float(r1.std() * 100), 2)
            })

        results.sort(key=lambda x: x["correlation"], reverse=True)

        ibov_first = float(prices[IBOV_INDEX].iloc[0]) if hasattr(prices[IBOV_INDEX], 'iloc') else 0
        ibov_last = float(prices[IBOV_INDEX].iloc[-1])
        ibov_ret = round((ibov_last / ibov_first - 1) * 100, 2) if ibov_first else 0

        output = {
            "results": results,
            "period": {"start": start_date, "end": end_date},
            "ibov_ticker": "^BVSP",
            "total_tickers": len(results),
            "ibov_total_return": ibov_ret
        }

        self._cache[cache_key] = output
        self._cache_timestamp = time.time()
        return output

if __name__ == "__main__":
    engine = CorrelationEngine()
    end = datetime.now()
    start = end - timedelta(days=365)
    data = engine.calculate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    if "results" in data:
        print(f"Correlações calculadas para {data['total_tickers']} ativos (último ano)")
        for r in data["results"][:5]:
            print(f"  {r['ticker']:8s} | {r['category']:10s} | Corr: {r['correlation']:.4f} | Beta: {r['beta']:.4f}")
    else:
        print(f"Erro: {data.get('error')}")
