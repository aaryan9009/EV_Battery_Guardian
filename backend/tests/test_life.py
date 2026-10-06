"""Regression tests for the interpolated life-to-80 % calculation.
Only the life calculation changed in Stage 6: SOH curves, physics SOH and EFC are pinned to the Stage 5 values."""
import numpy as np, pytest
from app.physics.constants import preset_as_dict
from app.physics.model import VehicleParams, SimResult, life_to_80, simulate
from app.services.prediction import analyze

def _res(yrs, soh):
    z = np.zeros(len(yrs))
    return SimResult(np.array(yrs, float), np.array(soh, float), z, z, {}, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

def test_interpolates_between_grid_points():
    y, reached = life_to_80(_res([0, .25, .5], [82, 80.5, 79]))          # crosses a third of the way from .25 to .5
    assert reached and y == pytest.approx(0.25 + 0.25 * 0.5 / 1.5)

def test_exact_hit_and_already_below():
    assert life_to_80(_res([0, 1, 2], [90, 80, 70])) == (1.0, True)
    assert life_to_80(_res([0, 1], [79, 70])) == (0.0, True)

def test_not_reached_uses_horizon_or_fallback():
    assert life_to_80(_res([0, 1, 2], [95, 94, 93])) == (2.0, False)
    assert life_to_80(_res([0, 1, 2], [95, 94, 93]), fallback=15) == (15.0, False)

def test_taxi_no_longer_quantised():
    r = analyze(VehicleParams(**preset_as_dict(3)), use_ml=False)        # 82.3 % -> crosses 80 % within the first year
    assert r["life_years"] % 0.25 != 0 and 0 < r["life_years"] < 0.5
    assert r["life_gained_years"] == pytest.approx(r["life_optimized_years"] - r["life_years"], abs=0.011)

# SOH, EFC and forecast end-points exactly as produced by Stage 5 (physics unchanged)
STAGE5 = {0: (91.14, 163.3, 32.7915, 58.7632), 1: (95.0, 342.9, 69.3336, 78.7505), 2: (92.62, 96.0, 73.5223, 76.9661),
          3: (82.33, 450.0, 30.0, 30.0), 4: (92.71, 733.3, 66.0552, 73.0397)}
@pytest.mark.parametrize("i", range(5))
def test_physics_unchanged(i):
    soh, efc, end_c, end_o = STAGE5[i]
    r = analyze(VehicleParams(**preset_as_dict(i)), use_ml=False)
    assert r["current_soh"] == soh and r["physics_soh"] == soh and r["efc"] == efc
    assert r["forecast"]["current"][-1] == pytest.approx(end_c, abs=1e-4) and r["forecast"]["optimized"][-1] == pytest.approx(end_o, abs=1e-4)

@pytest.mark.parametrize("i", range(5))
def test_life_within_one_grid_step_of_old_value(i):
    r = analyze(VehicleParams(**preset_as_dict(i)), use_ml=False)
    old = np.where(simulate(VehicleParams(**preset_as_dict(i))).soh <= 80)[0]
    grid = float(simulate(VehicleParams(**preset_as_dict(i))).yrs[old[0]])
    assert grid - 0.25 <= r["life_years"] <= grid
