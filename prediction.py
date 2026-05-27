import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import time

from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

warnings.filterwarnings('ignore')

# Import opcionais com fallback gracioso
try:
    from lightgbm import LGBMRegressor
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("[AVISO] LightGBM não encontrado. Pulando.")

try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_ARIMA = True
except ImportError:
    HAS_ARIMA = False
    print("[AVISO] statsmodels não encontrado. ARIMA indisponível.")


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários compartilhados
# ─────────────────────────────────────────────────────────────────────────────

def _safe_r2(y_true, y_pred):
    try:
        score = r2_score(y_true, y_pred)
        return float(score) if not (np.isnan(score) or np.isinf(score)) else -99.0
    except Exception:
        return -99.0

def _safe_mae(y_true, y_pred):
    try:
        return float(mean_absolute_error(y_true, y_pred))
    except Exception:
        return 999.0


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR 1 — Modelos Fundamentalistas (cross-sectional)
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_COLS = ['p_e', 'p_b', 'roe', 'dividend_yield', 'net_margin', 'debt_equity']


class FundamentalsEngine:
    """
    Treina modelos de ML em dados fundamentalistas de múltiplos ativos
    para prever o retorno percentual nos próximos 6 meses.
    """

    MODELS = {}  # populado em __init__

    def __init__(self):
        self.MODELS = {
            "Random Forest":    RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42, n_jobs=-1),
            "XGBoost":          XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42, verbosity=0),
            "SVR":              SVR(kernel='rbf', C=10, epsilon=0.1),
            "KNN":              KNeighborsRegressor(n_neighbors=5, weights='distance'),
            "MLP":              MLPRegressor(hidden_layer_sizes=(128, 64, 32), max_iter=500, random_state=42, early_stopping=True),
        }
        if HAS_LIGHTGBM:
            self.MODELS["LightGBM"] = LGBMRegressor(n_estimators=200, learning_rate=0.05, random_state=42, verbose=-1)

        self.scaler = StandardScaler()
        self.results = {}  # {model_name: {"r2": ..., "mae": ..., "model": ...}}

    def _prepare(self, X: pd.DataFrame) -> np.ndarray:
        return self.scaler.transform(X.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0))

    def train(self, df: pd.DataFrame, y: pd.Series):
        X = df[FEATURE_COLS].copy().replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        valid = ~X.isna().any(axis=1) & ~y.isna()
        X, y = X[valid], y[valid]

        if len(X) < 6:
            print("  [Fundamentals] Dados insuficientes para treinamento.")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.scaler.fit(X_train)
        Xtr = self.scaler.transform(X_train)
        Xts = self.scaler.transform(X_test)

        for name, model in self.MODELS.items():
            try:
                model.fit(Xtr, y_train)
                preds = model.predict(Xts)
                self.results[name] = {
                    "r2":  _safe_r2(y_test, preds),
                    "mae": _safe_mae(y_test, preds),
                    "model": model,
                    "type": "fundamentalista"
                }
                print(f"  [{name}] R2: {self.results[name]['r2']:.4f} | MAE: {self.results[name]['mae']:.2f}%")
            except Exception as e:
                print(f"  [{name}] ERRO: {e}")

    def predict_all(self, df: pd.DataFrame) -> dict:
        """Retorna {model_name: array_de_predicoes} para todos os tickers."""
        X = df[FEATURE_COLS].copy().replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        Xs = self.scaler.transform(X)
        preds = {}
        for name, info in self.results.items():
            try:
                preds[name] = info["model"].predict(Xs).tolist()
            except Exception:
                preds[name] = [0.0] * len(df)
        return preds

    def best(self):
        if not self.results:
            return None, None
        name = max(self.results, key=lambda k: self.results[k]["r2"])
        return name, self.results[name]


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR 2 — Modelos de Séries Temporais (por ticker)
# ─────────────────────────────────────────────────────────────────────────────

class TimeSeriesEngine:
    """
    Treina modelos de série temporal individualmente por ticker
    e prevê o retorno para os próximos ~3 meses (90 dias).
    """

    FORECAST_DAYS = 90

    def __init__(self):
        self.ts_results = {}  # {ticker: {model: retorno_previsto_%}}
        self.model_scores = {}  # {model_name: {r2, mae, n_samples}}

    def _fetch_history(self, ticker: str) -> pd.Series | None:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2y")
            if len(hist) < 120:
                return None
            return hist['Close']
        except Exception:
            return None

    # ── ARIMA ──────────────────────────────────────────────────────────────
    def _arima_return(self, series: pd.Series) -> float | None:
        if not HAS_ARIMA:
            return None
        try:
            train = series[:-90]
            test  = series[-90:]
            model = ARIMA(train, order=(2, 1, 2))
            fit   = model.fit()
            forecast = fit.forecast(steps=90)
            r2  = _safe_r2(test.values, forecast.values)
            mae = _safe_mae(test.values, forecast.values)
            self._accumulate_score("ARIMA", r2, mae)

            # Projeção futura: ARIMA sobre série completa
            full_fit = ARIMA(series, order=(2, 1, 2)).fit()
            future   = full_fit.forecast(steps=self.FORECAST_DAYS)
            pct = ((future.iloc[-1] - series.iloc[-1]) / series.iloc[-1]) * 100
            return float(pct)
        except Exception as e:
            return None

    def _accumulate_score(self, name: str, r2: float, mae: float):
        if name not in self.model_scores:
            self.model_scores[name] = {"r2_sum": 0, "mae_sum": 0, "n": 0}
        self.model_scores[name]["r2_sum"]  += r2
        self.model_scores[name]["mae_sum"] += mae
        self.model_scores[name]["n"]       += 1

    def run_for_ticker(self, ticker: str) -> dict:
        """Retorna {model_name: retorno_pct} para um ticker."""
        series = self._fetch_history(ticker)
        if series is None:
            return {}

        results = {}
        arima_pct  = self._arima_return(series)

        if arima_pct is not None:   results["ARIMA"] = round(arima_pct, 2)
        return results

    def avg_scores(self) -> dict:
        scores = {}
        for name, data in self.model_scores.items():
            n = max(data["n"], 1)
            scores[name] = {
                "r2":  round(data["r2_sum"] / n, 4),
                "mae": round(data["mae_sum"] / n, 2),
                "type": "serie_temporal" if name == "ARIMA" else "hibrido"
            }
        return scores


# ─────────────────────────────────────────────────────────────────────────────
# ORQUESTRADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class PredictionEngine:
    """
    Orquestra os dois motores de ML (Fundamentalista + Série Temporal)
    e agrega os resultados em um dicionário padronizado para o frontend.
    """

    def __init__(self):
        self.fund_engine = FundamentalsEngine()
        self.ts_engine   = TimeSeriesEngine()
        self.metrics = self._empty_metrics()

    def _empty_metrics(self) -> dict:
        return {
            "chosen_model": "N/A",
            "r2": 0, "mae": 0,
            "rf_r2": 0, "rf_mae": 0,
            "xgb_r2": 0, "xgb_mae": 0,
            "all_models": [],
            "per_ticker_predictions": {}
        }

    def get_historical_return(self, ticker: str, lookback_days: int = 180) -> float | None:
        """Retorno real dos últimos N dias (target para treinamento fundamentalista)."""
        try:
            hist = yf.Ticker(ticker).history(period="2y")
            if len(hist) < lookback_days + 10:
                return None
            preco_atual   = hist['Close'].iloc[-1]
            data_passado  = hist.index[-1] - pd.Timedelta(days=lookback_days)
            hist_passado  = hist[hist.index <= data_passado]
            if len(hist_passado) == 0:
                return None
            preco_passado = hist_passado['Close'].iloc[-1]
            return ((preco_atual - preco_passado) / preco_passado) * 100
        except Exception:
            return None

    def train_and_predict(self, df_fundamentals: pd.DataFrame):
        print("\n══════════════════════════════════════════════")
        print("  MOTOR DE IA PREDITIVA — Múltiplos Modelos")
        print("══════════════════════════════════════════════")

        df = df_fundamentals.copy()

        # ── 1. Retornos históricos para treino fundamentalista (6 meses) ────
        print("\n[1/3] Coletando retornos históricos de 6 meses para treinamento...")
        df['retorno_real'] = df['ticker'].apply(
            lambda x: self.get_historical_return(f"{x}.SA", lookback_days=90)
        )
        train_df = df.dropna(subset=['retorno_real'])
        print(f"      → {len(train_df)}/{len(df)} ativos com dados de retorno suficientes.")

        # ── 2. Treinar motor fundamentalista ─────────────────────────────────
        print("\n[2/3] Treinando modelos fundamentalistas...")
        self.fund_engine.train(train_df, train_df['retorno_real'])
        fund_preds = self.fund_engine.predict_all(df)

        # Melhor modelo fundamentalista
        best_fund_name, best_fund_info = self.fund_engine.best()
        if best_fund_name and best_fund_info:
            df['expected_return'] = fund_preds.get(best_fund_name, [0.0] * len(df))
        else:
            df['expected_return'] = 0.0

        # ── 3. Treinar motor de séries temporais por ticker ──────────────────
        print("\n[3/3] Executando modelos de série temporal por ticker...")
        ts_per_ticker = {}
        for i, row in df.iterrows():
            tkr = f"{row['ticker']}.SA"
            print(f"  → Série temporal: {row['ticker']}...", end=" ", flush=True)
            ts_preds = self.ts_engine.run_for_ticker(tkr)
            ts_per_ticker[row['ticker']] = ts_preds
            label = ", ".join([f"{k}: {v:.1f}%" for k, v in ts_preds.items()]) or "sem dados"
            print(label)

        # ── 4. Montar per_ticker_predictions (fundamentalistas + TS) ─────────
        tickers = df['ticker'].tolist()
        per_ticker = {}
        for i, tkr in enumerate(tickers):
            per_ticker[tkr] = {}
            # fundamentalistas
            for mname, plist in fund_preds.items():
                per_ticker[tkr][mname] = round(float(plist[i]), 2)
            # séries temporais
            for mname, pval in ts_per_ticker.get(tkr, {}).items():
                per_ticker[tkr][mname] = pval

        # ── 5. Montar all_models[] ────────────────────────────────────────────
        all_models = []
        for name, info in self.fund_engine.results.items():
            all_models.append({
                "name": name,
                "r2":   round(info["r2"], 4),
                "mae":  round(info["mae"], 2),
                "type": "fundamentalista"
            })
        for name, info in self.ts_engine.avg_scores().items():
            all_models.append({
                "name": name,
                "r2":   info["r2"],
                "mae":  info["mae"],
                "type": info["type"]
            })
        all_models.sort(key=lambda x: x["r2"], reverse=True)

        # Melhor global
        best_global = all_models[0] if all_models else {"name": "N/A", "r2": 0, "mae": 0}

        # ── 6. Métricas de legado para backward-compat ────────────────────────
        rf_info  = self.fund_engine.results.get("Random Forest", {"r2": 0, "mae": 0})
        xgb_info = self.fund_engine.results.get("XGBoost",       {"r2": 0, "mae": 0})

        self.metrics = {
            "chosen_model": best_global["name"],
            "r2":    best_global["r2"],
            "mae":   best_global["mae"],
            "rf_r2":  rf_info["r2"],
            "rf_mae": rf_info["mae"],
            "xgb_r2":  xgb_info["r2"],
            "xgb_mae": xgb_info["mae"],
            "all_models": all_models,
            "per_ticker_predictions": per_ticker
        }

        print(f"\n✅ Modelo vencedor: {best_global['name']} (R²={best_global['r2']:.4f})")
        return df, self.metrics
