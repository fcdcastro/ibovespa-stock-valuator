import math

class ValuationModels:
    @staticmethod
    def graham_value(eps, bvps):
        """
        Calculates Graham's Intrinsic Value.
        V = sqrt(22.5 * EPS * BVPS)
        """
        if eps <= 0 or bvps <= 0:
            return 0
        try:
            return math.sqrt(22.5 * eps * bvps)
        except ValueError:
            return 0

    @staticmethod
    def bazin_value(dividend_yield, price):
        """
        Calculates Bazin Value based on minimum 6% dividend yield.
        V = (Dividend per Share) / 0.06
        """
        if dividend_yield <= 0:
            return 0
        dividend_per_share = (dividend_yield / 100) * price
        return dividend_per_share / 0.06

    @staticmethod
    def magic_formula_score(metrics):
        """
        Calculates a simple score for Magic Formula ranking.
        Using EBITDA/Total Assets as ROC proxy and EBITDA/MarketCap as Yield proxy.
        """
        # Return on Capital Proxy
        total_assets = metrics.get("total_assets", 0)
        roc = metrics.get("ebitda", 0) / total_assets if total_assets and total_assets > 0 else 0
        
        # Earnings Yield Proxy
        market_cap = metrics.get("market_cap", 0)
        earnings_yield = metrics.get("ebitda", 0) / market_cap if market_cap and market_cap > 0 else 0
        
        return roc, earnings_yield

    @staticmethod
    def dcf_valuation(eps, growth_rate=0.05, discount_rate=0.10, years=5, terminal_growth=0.02):
        """
        Simplified DCF based on EPS growth.
        """
        if eps <= 0:
            return 0
            
        value = 0
        current_eps = eps
        
        # Projection phase
        for i in range(1, years + 1):
            current_eps *= (1 + growth_rate)
            value += current_eps / ((1 + discount_rate) ** i)
            
        # Terminal value phase
        terminal_value = (current_eps * (1 + terminal_growth)) / (discount_rate - terminal_growth)
        value += terminal_value / ((1 + discount_rate) ** years)
        
        return value

    @staticmethod
    def apply_all(metrics):
        """
        Applies all valuation models and adds results to metrics.
        """
        if not metrics:
            return None

        # Graham
        metrics["valuation_graham"] = ValuationModels.graham_value(
            metrics.get("eps", 0), metrics.get("bvps", 0)
        )
        
        # Bazin
        metrics["valuation_bazin"] = ValuationModels.bazin_value(
            metrics.get("dividend_yield", 0), metrics.get("price", 0)
        )
        
        # DCF (Conservative: 5% growth, 10% discount)
        metrics["valuation_dcf"] = ValuationModels.dcf_valuation(
            metrics.get("eps", 0)
        )
        
        # Magic Formula
        roc, ey = ValuationModels.magic_formula_score(metrics)
        metrics["magic_roc"] = roc
        metrics["magic_yield"] = ey
        
        # Upside Calculation (Average of Graham and DCF vs Price)
        fair_value = (metrics["valuation_graham"] + metrics["valuation_dcf"]) / 2
        if metrics["price"] > 0:
            metrics["upside"] = ((fair_value / metrics["price"]) - 1) * 100
        else:
            metrics["upside"] = 0
            
        return metrics
