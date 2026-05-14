import yfinance as yf
import time

class YahooFinanceProvider:
    def get_stock_data(self, ticker):
        """
        Busca dados fundamentais e de mercado para um ticker usando yfinance.
        """
        # Garante que o ticker tenha o sufixo .SA para o mercado brasileiro
        if not ticker.endswith(".SA"):
            yf_ticker = f"{ticker}.SA"
        else:
            yf_ticker = ticker
            
        try:
            stock = yf.Ticker(yf_ticker)
            # O yfinance.info retorna um dicionário com os dados fundamentais
            info = stock.info
            
            if not info or len(info) <= 5: # Se retornar quase nada
                print(f"Dados insuficientes para o ticker: {yf_ticker}")
                return None
                
            return info
        except Exception as e:
            print(f"Erro ao buscar dados para {yf_ticker} no Yahoo Finance: {e}")
            return None

if __name__ == "__main__":
    # Teste rápido com VALE3
    provider = YahooFinanceProvider()
    data = provider.get_stock_data("VALE3")
    if data:
        print(f"Sucesso ao buscar dados para {data.get('symbol')}")
        print(f"Preço Atual: {data.get('currentPrice')}")
        print(f"P/L: {data.get('trailingPE')}")
