from fractions import Fraction

import hierarchical_flood_zoom as hz


def q(lo, hi=None):
    return hz.QInterval.of(lo, hi)


def test_urban_debt_exact():
    out = hz.urban_debt_step(q("0"), q("203.5"), q("80"))
    assert out.low == Fraction("123.5")
    assert out.high == Fraction("123.5")


def test_urban_debt_interval():
    out = hz.urban_debt_step(q("0", "20"), q("60", "120"), q("70", "90"))
    assert out.low == 0
    assert out.high == 70


def test_toledo_interval_sign():
    delta = hz.toledo_increment_bounds(
        P_m=q("0.10", "0.12"),
        A_m2=q("1000"),
        c=q("0.5", "0.8"),
        Qin_m3s=q("0"),
        tau_s=q("3600"),
        Qout_m3s=q("0.005", "0.01"),
    )
    result = hz.classify_storage_increment(delta)
    assert result["status"] == "OK"
    assert result["state"] == "GUARANTEED_ACCUMULATION_WITHIN_DECLARED_BOUNDS"


def test_point_depth_interval():
    d = hz.point_depth_bounds(q("0.80", "0.90"), q("0.50", "0.60"))
    assert d.low == Fraction("0.20")
    assert d.high == Fraction("0.40")


def test_point_depth_refuses_without_data():
    r = hz.point_depth_bounds(None, q("0.50"))
    assert isinstance(r, hz.Refusal)
