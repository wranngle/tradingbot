import pytest

from config import Config
from risk_gauntlet import RiskGauntlet, RiskGauntletError


def test_defaults_pass_gauntlet():
    RiskGauntlet().validate(Config())


def test_excess_drawdown_blocks_load():
    cfg = Config(max_drawdown_pct=0.31)
    with pytest.raises(RiskGauntletError) as info:
        RiskGauntlet().validate(cfg)
    assert info.value.cap_name == "max_drawdown_cap"
    assert "max_drawdown_cap" in str(info.value)


def test_excess_leverage_blocks_load():
    cfg = Config(leverage=2.5)
    with pytest.raises(RiskGauntletError) as info:
        RiskGauntlet().validate(cfg)
    assert info.value.cap_name == "leverage_cap"
    assert "leverage_cap" in str(info.value)


def test_excess_position_concentration_blocks_load():
    cfg = Config(max_position_pct=0.25)
    with pytest.raises(RiskGauntletError) as info:
        RiskGauntlet().validate(cfg)
    assert info.value.cap_name == "position_concentration_cap"
    assert "position_concentration_cap" in str(info.value)
