"""Tests for sector aggregation helpers."""

from unittest.mock import MagicMock


def _security(sector):
    return MagicMock(
        Fundamentals=MagicMock(
            AssetClassification=MagicMock(MorningstarSectorCode=sector),
        ),
    )


def _holding(invested, value):
    return MagicMock(Invested=invested, HoldingsValue=value)


def test_calculate_portfolio_value_for_sector_recomputes(reset_variables):
    import variables as v
    from sectorAnalysis import sectorAnalysis

    algo = MagicMock()
    tech = MagicMock(name="tech_symbol")
    health = MagicMock(name="health_symbol")
    algo.Portfolio = {
        tech: _holding(True, 300),
        health: _holding(True, 200),
    }
    algo.Securities = {
        tech: _security(101),
        health: _security(102),
    }

    assert sectorAnalysis.calculatePortfolioValueForSector(algo, 101) == 300
    assert sectorAnalysis.calculatePortfolioValueForSector(algo, 101) == 300
    assert v.sector_portfolio_value[101] == 300


def test_unique_portfolio_sectors_uses_security_fundamentals(reset_variables):
    from sectorAnalysis import sectorAnalysis

    algo = MagicMock()
    invested = MagicMock(name="invested_symbol")
    not_invested = MagicMock(name="not_invested_symbol")
    algo.Portfolio = {
        invested: _holding(True, 300),
        not_invested: _holding(False, 200),
    }
    algo.Securities = {
        invested: _security(101),
        not_invested: _security(102),
    }

    assert sectorAnalysis.getUniquePortfolioSectors(algo) == {101}
