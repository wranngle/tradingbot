# Begin OnWarmupFinished.py

from AlgorithmImports import *
import config as c
import variables as v


class OnWarmupFinishedHandler:
    def __init__(self, algorithm):
        self.algorithm = algorithm
    
    def OnWarmupFinished(self):
        # Runs after the warmup period, regardless of static or dynamic universe.
    
        self.algorithm.Debug(f"-------- Universe filtering and warmup complete. Symbol count: {len(v.active_symbols)}")
        
        for symbol in v.active_symbols:
            
            # Extract the required attributes from the symbol data
            price = self.algorithm.Securities[symbol].Fundamentals.Price
            dollar_volume = self.algorithm.Securities[symbol].Fundamentals.DollarVolume
            pe_ratio = self.algorithm.Securities[symbol].Fundamentals.ValuationRatios.PERatio
            revenue_growth = self.algorithm.Securities[symbol].Fundamentals.OperationRatios.RevenueGrowth.OneYear
            market_cap = self.algorithm.Securities[symbol].Fundamentals.MarketCap
            sector = self.algorithm.Securities[symbol].Fundamentals.AssetClassification.MorningstarSectorCode
            industry = self.algorithm.Securities[symbol].Fundamentals.AssetClassification.MorningstarIndustryCode
            short_name = self.algorithm.Securities[symbol].Fundamentals.CompanyReference.ShortName
            
            self.algorithm.Debug(f"-------- {symbol}, Price: ${price}, Dollar Volume: ${dollar_volume}, P/E Ratio:{pe_ratio}, Revenue Growth: {revenue_growth}%, MarketCap: {market_cap}, Sector: {sector}, Industry: {industry} - {short_name}")

# End OnWarmupFinished.py
