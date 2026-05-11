# AVALIAÇÃO SUPPLIERS - Ibovespa Stock Valuation Algorithm

An automated fundamental analysis tool for Brazilian stocks (B3) using the Brapi API. This project implements multiple valuation models and provides a premium web dashboard for data visualization.

## 🚀 Features
- **Automated Ingestion**: Fetches real-time quotes and financial history from Brapi.
- **Valuation Models**:
  - **Graham Formula**: Calculates intrinsic value based on EPS and BVPS.
  - **Bazin Model**: Valuation based on dividend yield (minimum 6%).
  - **Magic Formula**: Rankings based on Return on Capital (ROC) and Earnings Yield.
  - **Simplified DCF**: Projections based on growth and discount rates.
- **Modern Dashboard**: A clean, responsive light-themed dashboard built with Flask and Vanilla JS.
- **Data Export**: Saves all analysis results to a `valuation_results.csv` file.

## 🛠️ Tech Stack
- **Backend**: Python, Flask, Pandas, Requests.
- **Frontend**: Vanilla HTML5, CSS3, JavaScript.
- **Data Source**: [Brapi.dev](https://brapi.dev/)

## 📦 Installation
1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your API token in a `.env` file:
   ```env
   BRAPI_TOKEN=your_token_here
   ```
4. Run the server:
   ```bash
   python server.py
   ```
5. Open your browser at `http://localhost:5000`.

## 📄 License
MIT
