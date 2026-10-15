import pytest

from surfline.units import circular_mean_deg, deg_to_compass, m_to_ft, ms_to_mph


def test_wave_height_conversion():
    assert m_to_ft(1.4) == pytest.approx(4.6, abs=0.05)


def test_wind_speed_conversion():
    assert ms_to_mph(8.05) == pytest.approx(18, abs=0.1)


@pytest.mark.parametrize("deg,label", [(0, "N"), (225, "SW"), (359, "N"), (11, "N"), (12, "NNE")])
def test_compass(deg, label):
    assert deg_to_compass(deg) == label


def test_circular_mean_wraps():
    assert circular_mean_deg([359, 1]) == pytest.approx(0, abs=0.01) or \
        circular_mean_deg([359, 1]) == pytest.approx(360, abs=0.01)
