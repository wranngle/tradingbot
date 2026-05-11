from AlgorithmImports import *
import variables as v


class OnWarmupFinishedHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def OnWarmupFinished(self):
        self.algorithm.Debug(f"-------- Universe filtering and warmup complete. Symbol count: {len(v.active_symbols)}")

        for symbol in v.active_symbols:
            price = self.algorithm.Securities[symbol].Fundamentals.Price
            dollar_volume = self.algorithm.Securities[symbol].Fundamentals.DollarVolume
            pe_ratio = self.algorithm.Securities[symbol].Fundamentals.ValuationRatios.PERatio
            revenue_growth = self.algorithm.Securities[symbol].Fundamentals.OperationRatios.RevenueGrowth.OneYear
            market_cap = self.algorithm.Securities[symbol].Fundamentals.MarketCap
            sector = self.algorithm.Securities[symbol].Fundamentals.AssetClassification.MorningstarSectorCode
            industry = self.algorithm.Securities[symbol].Fundamentals.AssetClassification.MorningstarIndustryCode
            short_name = self.algorithm.Securities[symbol].Fundamentals.CompanyReference.ShortName

            self.algorithm.Debug(
                f"-------- {symbol}, Price: ${price}, Dollar Volume: ${dollar_volume}, "
                f"P/E Ratio:{pe_ratio}, Revenue Growth: {revenue_growth}%, "
                f"MarketCap: {market_cap}, Sector: {sector}, "
                f"Industry: {industry} - {short_name}"
            )
