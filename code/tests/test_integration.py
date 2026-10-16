"""
Synthetic-data integration test.

Generates a fake panel, runs index construction, and verifies the
output has expected properties. Catches integration bugs that
unit tests miss (column-naming mismatches, merge failures, etc.).
"""

import numpy as np
import pandas as pd
import pytest

from src.construct.fintech_index import construct_fintech_index, COMPONENT_MAP
from src.construct.ai_index import construct_ai_index, PILLAR_COLUMN_MAP


@pytest.fixture
def synthetic_findex():
    """5 countries x 4 years x 4 indicators (in percentage units 0-100)."""
    rng = np.random.default_rng(42)
    countries = ["USA", "GBR", "IND", "KEN", "BRA"]
    years = [2017, 2020, 2021, 2024]
    rows = []
    for c in countries:
        # country-specific intercept
        base = rng.uniform(20, 80)
        for y in years:
            # year trend
            trend = (y - 2017) * 2
            rows.append({
                "iso3": c,
                "year": y,
                "wave": y if y in (2017, 2021, 2024) else np.nan,
                "findex_dp": base + trend + rng.normal(scale=3),
                "findex_ma": base * 0.5 + trend + rng.normal(scale=3),
                "findex_mp": base * 0.7 + trend + rng.normal(scale=3),
                "findex_da": base + trend + rng.normal(scale=3),
            })
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic_ai_components():
    """5 countries x 4 years x 11 AI components across 3 pillars."""
    rng = np.random.default_rng(123)
    countries = ["USA", "GBR", "IND", "KEN", "BRA"]
    years = [2018, 2020, 2022, 2024]
    rows = []
    # Latent country AI capability
    capability = {c: rng.uniform(0, 100) for c in countries}
    for c in countries:
        for y in years:
            trend = (y - 2018) * 5
            base = capability[c] + trend
            rows.append({
                "iso3": c,
                "year": y,
                # GARI pillar
                "gari_government": base + rng.normal(scale=5),
                "gari_tech_sector": base + rng.normal(scale=5),
                "gari_data_infra": base + rng.normal(scale=5),
                # Stanford pillar (already log-transformed in real loader)
                "ai_pubs_pc": np.log1p(base / 10 + rng.normal(scale=1)),
                "ai_patents_pc": np.log1p(base / 15 + rng.normal(scale=1)),
                "ai_investment": np.log1p(base * 1e6 + rng.normal(scale=1e5)),
                "ai_workforce": base / 100 + rng.normal(scale=0.02),
                # IMF AIPI pillar
                "aipi_digital_infra": base + rng.normal(scale=5),
                "aipi_human_capital": base + rng.normal(scale=5),
                "aipi_innovation": base + rng.normal(scale=5),
                "aipi_regulation": base + rng.normal(scale=5),
            })
    return pd.DataFrame(rows)


def test_fintech_index_runs(synthetic_findex):
    F = construct_fintech_index(synthetic_findex)
    assert "F" in F.columns
    assert "F_pca" in F.columns
    assert "F_access" in F.columns
    assert "F_usage" in F.columns
    # F should be roughly mean-zero (z-score average)
    assert abs(F["F"].mean()) < 0.1
    # Should have one row per country-year
    assert len(F) == len(synthetic_findex)


def test_ai_index_runs(synthetic_ai_components):
    G = construct_ai_index(synthetic_ai_components)
    assert "G" in G.columns
    assert "G_pca" in G.columns
    assert "G_pillar_readiness" in G.columns
    assert "G_pillar_activity" in G.columns
    assert "G_pillar_adoption" in G.columns
    # G should be approximately mean-zero
    assert abs(G["G"].mean()) < 0.2
    # Pillars should be highly correlated with G
    for pillar in PILLAR_COLUMN_MAP.keys():
        corr = G[f"G_pillar_{pillar}"].corr(G["G"])
        assert corr > 0.7, f"pillar {pillar} corr with G: {corr}"


def test_ai_index_handles_missing_pillar(synthetic_ai_components):
    """If Stanford data is unavailable, G should still construct from GARI+AIPI."""
    df = synthetic_ai_components.drop(
        columns=["ai_pubs_pc", "ai_patents_pc", "ai_investment", "ai_workforce"]
    )
    G = construct_ai_index(df)
    # Activity pillar should be NA but composite should still build
    assert G["G_pillar_activity"].isna().all()
    assert G["G"].notna().any()
