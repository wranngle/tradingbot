from AlgorithmImports import *
import variables as v


def _portfolio_items(portfolio):
    if hasattr(portfolio, "items"):
        return portfolio.items()
    return ((symbol, portfolio[symbol]) for symbol in portfolio.Keys)


def _sector_for_symbol(algorithm, symbol):
    security = algorithm.Securities[symbol]
    return security.Fundamentals.AssetClassification.MorningstarSectorCode


class SectorAnalysis:
    @staticmethod
    def getUniquePortfolioSectors(algorithm):
        try:
            sectors = set()
            for symbol, holding in _portfolio_items(algorithm.Portfolio):
                if holding.Invested:
                    v.symbol_sector[symbol] = _sector_for_symbol(algorithm, symbol)
                    sectors.add(v.symbol_sector[symbol])
            v.unique_portfolio_sectors = sectors
            return sectors
        except Exception as e:
            algorithm.Error(f"Error on getUniquePortfolioSectors: {str(e)}")
            return set()

    @staticmethod
    def calculatePortfolioValueForSector(algorithm, sector):
        try:
            total = 0
            for symbol, holding in _portfolio_items(algorithm.Portfolio):
                if holding.Invested and _sector_for_symbol(algorithm, symbol) == sector:
                    total += holding.HoldingsValue
            v.sector_portfolio_value[sector] = total
            return total
        except Exception as e:
            algorithm.Error(f"Error on calculatePortfolioValueForSector: {str(e)}")
            return 0

    @staticmethod
    def calculateSymbolCountsPerSector(algorithm):
        try:
            counts = {}
            for symbol, holding in _portfolio_items(algorithm.Portfolio):
                if holding.Invested:
                    sector = _sector_for_symbol(algorithm, symbol)
                    v.symbol_sector[symbol] = sector
                    counts[sector] = counts.get(sector, 0) + 1
            v.symbol_counts_per_sector = counts
            return counts
        except Exception as e:
            algorithm.Error(f"Error on calculateSymbolCountsPerSector: {str(e)}")
            return {}


sectorAnalysis = SectorAnalysis
