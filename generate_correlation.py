from correlation import CorrelationEngine
from datetime import datetime
import json

PERIODS = [1, 3, 5]
end = datetime.now()

engine = CorrelationEngine()
all_periods = {}

for years in PERIODS:
    start = end.replace(year=end.year - years)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    print(f"Calculando correlação para {years} ano(s)...")
    data = engine.calculate(start_str, end_str)
    if "error" in data:
        print(f"  ERRO: {data['error']}")
        continue
    print(f"  {data['total_tickers']} ativos processados.")
    all_periods[str(years)] = data

with open("correlation_data.js", "w", encoding="utf-8") as f:
    f.write("window.__CORRELATION_DATA__ = ")
    json.dump(all_periods, f)
    f.write(";\n")

print(f"\nArquivo correlation_data.js gerado com {len(all_periods)} períodos.")
