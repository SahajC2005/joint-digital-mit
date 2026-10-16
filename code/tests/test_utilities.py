"""
Smoke tests for utilities and index construction.

These run on synthetic data so they don't depend on raw downloads.
Verify with: python -m pytest tests/ -v
"""

import numpy as np
import pandas as pd

from src.utils.country_codes import to_iso3, validate_panel_coverage
from src.utils.data_helpers import (
    zscore,
    winsorize,
    equal_weighted_index,
    pca_index,
    interpolate_within_country,
    build_balanced_skeleton,
)


def test_iso3_mapping_handles_common_names():
    names = pd.Series([
        "United States", "USA", "us", "Korea, Rep.",
        "Cote d'Ivoire", "Ivory Coast", "Czechia", "Czech Republic",
        "Eswatini", "Swaziland", "Turkiye", "Turkey",
        "Kosovo", "Taiwan, Province of China",
    ])
    result = to_iso3(names, source="test")
    assert (result.iloc[0:3] == "USA").all()
    assert (result.iloc[3] == "KOR")
    assert (result.iloc[4:6] == "CIV").all()
    assert (result.iloc[6:8] == "CZE").all()
    assert (result.iloc[8:10] == "SWZ").all()
    assert (result.iloc[10:12] == "TUR").all()
    assert result.iloc[12] == "XKX"
    assert result.iloc[13] == "TWN"


def test_aggregates_dropped():
    names = pd.Series(["World", "European Union", "USA", "OECD members"])
    result = to_iso3(names, source="test")
    assert result.iloc[0:2].isna().all()
    assert result.iloc[2] == "USA"
    assert pd.isna(result.iloc[3])


def test_zscore_properties():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    z = zscore(s)
    assert abs(z.mean()) < 1e-10
    assert abs(z.std(ddof=1) - 1.0) < 1e-10


def test_equal_weighted_index_matches_chhetri_koirala():
    df = pd.DataFrame({
        "a": [10, 20, 30, 40],
        "b": [5, 10, 15, 20],
        "c": [1, 2, 3, 4],
    })
    idx = equal_weighted_index(df, components=["a", "b", "c"])
    # Should be average of z-scores
    expected = pd.concat([zscore(df["a"]), zscore(df["b"]), zscore(df["c"])], axis=1).mean(axis=1)
    pd.testing.assert_series_equal(idx, expected, check_names=False)


def test_pca_index_extracts_common_factor():
    # Build data where a, b, c share a common factor
    rng = np.random.default_rng(42)
    f = rng.normal(size=100)
    df = pd.DataFrame({
        "a": f + rng.normal(scale=0.1, size=100),
        "b": f + rng.normal(scale=0.1, size=100),
        "c": f + rng.normal(scale=0.1, size=100),
    })
    pc, diag = pca_index(df, components=["a", "b", "c"])
    # First PC should explain most variance when components are highly correlated
    assert diag["variance_explained"] > 0.85
    # Should correlate strongly with the latent factor
    assert abs(np.corrcoef(pc.dropna(), f[: pc.notna().sum()])[0, 1]) > 0.95


def test_interpolate_within_country():
    df = pd.DataFrame({
        "iso3": ["AAA"] * 5 + ["BBB"] * 5,
        "year": list(range(2020, 2025)) * 2,
        "x": [1.0, np.nan, 3.0, np.nan, 5.0, 10.0, np.nan, np.nan, np.nan, 50.0],
    })
    out = interpolate_within_country(df, "x")
    assert out.loc[(out["iso3"] == "AAA") & (out["year"] == 2021), "x"].iloc[0] == 2.0
    assert out.loc[(out["iso3"] == "AAA") & (out["year"] == 2023), "x"].iloc[0] == 4.0
    # BBB should also interpolate linearly
    assert abs(out.loc[(out["iso3"] == "BBB") & (out["year"] == 2022), "x"].iloc[0] - 30.0) < 1e-9


def test_skeleton_builder():
    sk = build_balanced_skeleton(["USA", "GBR"], [2020, 2021])
    assert len(sk) == 4
    assert set(sk["iso3"]) == {"USA", "GBR"}
    assert set(sk["year"]) == {2020, 2021}


def test_panel_validation_flags_duplicates():
    df = pd.DataFrame({
        "iso3": ["USA", "USA", "GBR"],
        "year": [2020, 2020, 2020],
        "x": [1, 2, 3],
    })
    diag = validate_panel_coverage(df)
    assert diag["duplicates"] == 1
