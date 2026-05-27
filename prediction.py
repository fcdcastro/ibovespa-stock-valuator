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

try:
    from lightgbm import LGBMRegressor
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_ARIMA = True
except ImportError:
    HAS_ARIMA = False


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


FEATURE_COLS = ['p_e', 'p_b', 'roe', 'dividend_yield', 'net_margin', 'debt_equity']


class FundamentalsEngine:
    MODELS = {}

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
        self.results = {}

    def _prepare(self, X):
        return self.scaler.transform(X.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0))

    def train(self, df, y):
        X = df[FEATURE_COLS].copy().replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        valid = ~X.isna().any(axis=1) & ~y.isna()
        X, y = X[valid], y[valid]
        if len(X) < 6:
            print("  [Fundamentals] Dados insuficientes.")
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
                    "r2": _safe_r2(y_test, preds),
                    "mae": _safe_mae(y_test, preds),
                    "model": model,
                    "type": "fundamentalista"
                }
                print(f"  [{name}] R2: {self.results[name]['r2']:.4f} | MAE: {self.results[name]['mae']:.2f}%")
            except Exception as e:
                print(f"  [{name}] ERRO: {e}")

    def predict_all(self, df):
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


class TimeSeriesEngine:
    def __init__(self):
        self.ts_results = {}
        self.model_scores = {}

    def _fetch_history(self, ticker):
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2y")
            if len(hist) < 120:
                return None
            return hist['Close']
        except Exception:
            return None

    def _arima_return(self, series, forecast_days):
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
            full_fit = ARIMA(series, order=(2, 1, 2)).fit()
            future = full_fit.forecast(steps=forecast_days)
            pct = ((future.iloc[-1] - series.iloc[-1]) / series.iloc[-1]) * 100
            return float(pct)
        except Exception:
            return None

    def _accumulate_score(self, name, r2, mae):
        if name not in self.model_scores:
            self.model_scores[name] = {"r2_sum": 0, "mae_sum": 0, "n": 0}
        self.model_scores[name]["r2_sum"]  += r2
        self.model_scores[name]["mae_sum"] += mae
        self.model_scores[name]["n"]       += 1

    def run_for_ticker(self, ticker, forecast_days=90):
        series = self._fetch_history(ticker)
        if series is None:
            return {}
        results = {}
        arima_pct = self._arima_return(series, forecast_days)
        if arima_pct is not None:
            results["ARIMA"] = round(arima_pct, 2)
        return results

    def avg_scores(self):
        scores = {}
        for name, data in self.model_scores.items():
            n = max(data["n"], 1)
            scores[name] = {
                "r2": round(data["r2_sum"] / n, 4),
                "mae": round(data["mae_sum"] / n, 2),
                "type": "serie_temporal"
            }
        return scores


class PredictionEngine:
    HORIZONS = {
        "3m": 90,
        "6m": 180,
        "12m": 360
    }

    def __init__(self):
        self.metrics = self._empty_metrics()

    def _empty_metrics(self):
        return {
            "chosen_model": "N/A",
            "r2": 0, "mae": 0,
            "all_models": {},
            "horizons": {},
            "per_ticker_predictions": {}
        }

    def get_historical_return(self, ticker, lookback_days=180):
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

    def train_and_predict(self, df_fundamentals):
        print("\n" + "="*50)
        print("  MOTOR DE IA PREDITIVA - Multiplos Horizontes")
        print("="*50)

        df = df_fundamentals.copy()
        all_per_ticker = {}
        all_models_by_horizon = {}
        horizon_best = {}
        ts_engines = {}

        for horizon_label, horizon_days in self.HORIZONS.items():
            print(f"\n--- Horizonte {horizon_label} ({horizon_days} dias) ---")

            # 1. Retornos historicos
            print(f"[1/4] Coletando retornos historicos de {horizon_days} dias...")
            df[f'retorno_real_{horizon_label}'] = df['ticker'].apply(
                lambda x: self.get_historical_return(f"{x}.SA", lookback_days=horizon_days)
            )
            train_df = df.dropna(subset=[f'retorno_real_{horizon_label}'])
            print(f"      -> {len(train_df)}/{len(df)} ativos com dados.")

            # 2. Treinar fundamentalistas
            print("[2/4] Treinando modelos fundamentalistas...")
            fund_engine = FundamentalsEngine()
            fund_engine.train(train_df, train_df[f'retorno_real_{horizon_label}'])
            fund_preds = fund_engine.predict_all(df)

            best_name, best_info = fund_engine.best()
            if best_name and best_info:
                df[f'expected_return_{horizon_label}'] = fund_preds.get(best_name, [0.0] * len(df))
                print(f"      Melhor modelo: {best_name} (R²={best_info['r2']:.4f})")
            else:
                df[f'expected_return_{horizon_label}'] = 0.0
                print("      Nenhum modelo convergiu.")

            # 3. Per-ticker predictions
            tickers = df['ticker'].tolist()
            horizon_per_ticker = {}
            for i, tkr in enumerate(tickers):
                horizon_per_ticker[tkr] = {}
                for mname, plist in fund_preds.items():
                    horizon_per_ticker[tkr][mname] = round(float(plist[i]), 2)
            all_per_ticker[horizon_label] = horizon_per_ticker

            # 4. Model metrics per horizon
            horizon_models = []
            for name, info in fund_engine.results.items():
                horizon_models.append({
                    "name": name,
                    "r2": round(info["r2"], 4),
                    "mae": round(info["mae"], 2),
                    "type": "fundamentalista"
                })
            horizon_models.sort(key=lambda x: x["r2"], reverse=True)
            all_models_by_horizon[horizon_label] = horizon_models
            horizon_best[horizon_label] = horizon_models[0]["name"] if horizon_models else "N/A"

            # TimeSeries (ARIMA) so para 3m
            if horizon_label == "3m":
                print("[3/4] Executando modelos de serie temporal por ticker...")
                ts_engine = TimeSeriesEngine()
                ts_per_ticker = {}
                for i, row in df.iterrows():
                    tkr = f"{row['ticker']}.SA"
                    ts_preds = ts_engine.run_for_ticker(tkr, forecast_days=horizon_days)
                    ts_per_ticker[row['ticker']] = ts_preds
                    if ts_preds:
                        for mname, pval in ts_preds.items():
                            all_per_ticker[horizon_label][row['ticker']][mname] = pval
                ts_scores = ts_engine.avg_scores()
                for name, info in ts_scores.items():
                    all_models_by_horizon[horizon_label].append({
                        "name": name,
                        "r2": info["r2"],
                        "mae": info["mae"],
                        "type": info["type"]
                    })
                all_models_by_horizon[horizon_label].sort(key=lambda x: x["r2"], reverse=True)

        # Sort final da tabela pelo retorno 3m (padr�o)
        df = df.sort_values(by="expected_return_3m", ascending=False)

        # Montar m�tricas
        best_global_name = horizon_best.get("3m", "N/A")
        best_global_r2 = 0
        for m in all_models_by_horizon.get("3m", []):
            if m["name"] == best_global_name:
                best_global_r2 = m["r2"]
                break

        self.metrics = {
            "chosen_model": best_global_name,
            "r2": best_global_r2,
            "mae": 0,
            "horizons": list(self.HORIZONS.keys()),
            "horizon_best": horizon_best,
            "all_models": all_models_by_horizon,
            "per_ticker_predictions": all_per_ticker
        }

        print(f"\nOK Melhores modelos por horizonte: {horizon_best}")
        return df, self.metrics
