import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
import time

warnings.filterwarnings('ignore')

class PredictionEngine:
    def __init__(self, lookback_period='3mo', historical_period='1y'):
        self.lookback_period = lookback_period
        self.historical_period = historical_period
        self.model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        self.metrics = {"mae": 0, "r2": 0}

    def get_historical_return(self, ticker):
        """
        Calcula o retorno real de X meses atrás até hoje.
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=self.historical_period)
            
            if len(hist) < 60:
                return None
            
            preco_atual = hist['Close'].iloc[-1]
            
            # Aproximadamente 3 meses (90 dias)
            data_passado = hist.index[-1] - pd.Timedelta(days=90)
            historical_data = hist[hist.index <= data_passado]
            
            if len(historical_data) == 0:
                return None
            
            preco_passado = historical_data['Close'].iloc[-1]
            retorno_real = ((preco_atual - preco_passado) / preco_passado) * 100
            return retorno_real
        except Exception as e:
            print(f"Erro ao calcular retorno histórico para {ticker}: {e}")
            return None

    def train_and_predict(self, df_fundamentals):
        """
        Treina o modelo com os fundamentos e retornos históricos, depois prevê retornos futuros.
        """
        print("\n--- Iniciando Inteligencia Preditiva (Regressao) ---")
        
        # Preparar dados de treino
        # Precisamos dos fundamentos e do retorno real (target)
        # Vamos usar as colunas que o usuário sugeriu
        features_map = {
            'p_e': 'P_L',
            'p_b': 'P_VP',
            'roe': 'ROE',
            'dividend_yield': 'DivYield',
            'net_margin': 'MargemLiq',
            'debt_equity': 'DyDivida'
        }
        
        # Criar uma cópia para o modelo
        model_data = df_fundamentals.copy()
        
        # Obter retornos reais para treino (Isso demora um pouco)
        print("... Coletando retornos historicos para treinamento ...")
        model_data['retorno_real'] = model_data['ticker'].apply(lambda x: self.get_historical_return(f"{x}.SA"))
        
        # Remover linhas sem retorno histórico
        train_df = model_data.dropna(subset=['retorno_real'])
        
        if len(train_df) < 5:
            print("[AVISO] Dados insuficientes para treinar o modelo de regressao.")
            return df_fundamentals, {"mae": 0, "r2": 0}

        # Features (X) e Target (y)
        X = train_df[['p_e', 'p_b', 'roe', 'dividend_yield', 'net_margin', 'debt_equity']].copy()
        y = train_df['retorno_real']

        # Tratamento de dados (preencher NaNs, Infinitos e valores negativos)
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.mask(X < 0, 0)
        X = X.fillna(0)
        
        y = y.replace([np.inf, -np.inf], np.nan).fillna(0)

        # Garantir que não há NaNs remanescentes antes do split
        indices_to_keep = ~X.isna().any(axis=1) & ~y.isna()
        X = X[indices_to_keep]
        y = y[indices_to_keep]

        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Treinar
        self.model.fit(X_train, y_train)

        # Avaliar
        y_pred = self.model.predict(X_test)
        self.metrics["mae"] = mean_absolute_error(y_test, y_pred)
        self.metrics["r2"] = r2_score(y_test, y_pred)

        print(f"[OK] Modelo Treinado. MAE: {self.metrics['mae']:.2f}% | R2: {self.metrics['r2']:.4f}")

        # Prever para todos
        full_X = df_fundamentals[['p_e', 'p_b', 'roe', 'dividend_yield', 'net_margin', 'debt_equity']].copy()
        full_X = full_X.replace([np.inf, -np.inf], np.nan)
        full_X = full_X.mask(full_X < 0, 0)
        full_X = full_X.fillna(0)
        
        df_fundamentals['expected_return'] = self.model.predict(full_X)
        
        return df_fundamentals, self.metrics
