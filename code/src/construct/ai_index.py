"""
AI penetration index G construction.

Extends Chhetri-Koirala's FinTech methodology to a three-pillar AI index:

  Pillar 1 (Readiness):   GARI subindices (Government, Tech Sector, Data/Infra)
  Pillar 2 (Activity):    Stanford AI Index (publications, patents, investment, talent)
  Pillar 3 (Adoption):    IMF AIPI subindices (Digital infra, HC, Innovation, Regulation)

Composite formula (analogue of Chhetri-Koirala eq. 11, this paper's eq. 36):

  G_it = (1/3) * (Z^Readiness + Z^Activity + Z^Adoption)

Each pillar is itself an equally-weighted average of standardized components.

Access/Usage decomposition (this paper's eqs. 37 and 38):

  G_access_it = (1/2) * (Z_GARI_data_infra + Z_AIPI_digital_infra)
  G_usage_it  = (1/4) * (Z_AI_pubs + Z_AI_patents + Z_AI_workforce + Z_AIPI_innovation)

Robustness: first principal component across all underlying inputs.
"""

from typing import Dict, List

import numpy as np
import pandas as pd

from config.settings import DATA_INTERIM, INDEX_PARAMS
from src.utils.data_helpers import equal_weighted_index, pca_index, zscore
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


# Map config pillar names to actual data columns
PILLAR_COLUMN_MAP: Dict[str, List[str]] = {
    "readiness": [
        "gari_government",
        "gari_tech_sector",
        "gari_data_infra",
    ],
    "activity": [
        "ai_pubs_pc",
        "ai_patents_pc",
        "ai_investment",
        "ai_workforce",
    ],
    "adoption": [
        "aipi_digital_infra",
        "aipi_human_capital",
        "aipi_innovation",
        "aipi_regulation",
    ],
}


def _safe_zscore_components(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """
    Z-score available columns; warn on missing.
    """
    out = pd.DataFrame(index=df.index)
    available = [c for c in cols if c in df.columns]
    missing = set(cols) - set(available)
    if missing:
        logger.warning(f"AI index: missing columns {missing}; pillar will use available only")
    for c in available:
        out[f"Z_{c}"] = zscore(df[c])
    return out


def construct_ai_index(merged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build G index from a merged frame containing GARI, Stanford, and AIPI columns.

    Parameters
    ----------
    merged_df : DataFrame
        Country-year panel with all upstream AI source columns merged in.

    Returns
    -------
    DataFrame with G, G_pca, G_access, G_usage, and pillar sub-scores.
    """
    df = merged_df.copy()

    # Standardize components within each pillar; ensure pillar key exists
    # even when no underlying components are available.
    z_components = {pillar: [] for pillar in PILLAR_COLUMN_MAP.keys()}
    for pillar, cols in PILLAR_COLUMN_MAP.items():
        zs = _safe_zscore_components(df, cols)
        for col in zs.columns:
            df[col] = zs[col]
            z_components[pillar].append(col)

    # Pillar scores: equal-weighted average of available standardized components
    for pillar, z_cols in z_components.items():
        if z_cols:
            df[f"G_pillar_{pillar}"] = df[z_cols].mean(axis=1)
        else:
            df[f"G_pillar_{pillar}"] = np.nan  # float NA so column dtype is set
            logger.error(f"pillar {pillar} has no components; G will be biased")

    # Composite G: equal weight across pillars
    pillar_cols = [f"G_pillar_{p}" for p in PILLAR_COLUMN_MAP.keys()]
    df["G"] = df[pillar_cols].mean(axis=1)

    # PCA robustness across all underlying standardized components
    all_z_cols = [c for cs in z_components.values() for c in cs]
    if len(all_z_cols) >= 3:
        df["G_pca"], pca_diag = pca_index(df, components=[c[2:] for c in all_z_cols])
        # Note: pca_index re-standardizes; passing raw column names back
        logger.info(f"AI index PCA diagnostics: {pca_diag}")
    else:
        df["G_pca"] = pd.NA
        logger.error(f"AI index: only {len(all_z_cols)} components available; skipping PCA")

    # Access vs. Usage decomposition (this paper's eqs. 37, 38)
    access_components = ["gari_data_infra", "aipi_digital_infra"]
    usage_components = ["ai_pubs_pc", "ai_patents_pc", "ai_workforce", "aipi_innovation"]

    df["G_access"] = equal_weighted_index(
        df,
        components=[c for c in access_components if c in df.columns],
        standardize=True,
    )
    df["G_usage"] = equal_weighted_index(
        df,
        components=[c for c in usage_components if c in df.columns],
        standardize=True,
    )

    return df


def main():
    # Merge sources into a single AI-component frame
    gari = pd.read_parquet(DATA_INTERIM / "gari_clean.parquet")
    stanford = pd.read_parquet(DATA_INTERIM / "stanford_ai_index_clean.parquet")
    aipi = pd.read_parquet(DATA_INTERIM / "imf_aipi_clean.parquet")

    merged = gari.merge(stanford, on=["iso3", "year"], how="outer")
    merged = merged.merge(aipi, on=["iso3", "year"], how="outer")

    G = construct_ai_index(merged)
    G.to_parquet(DATA_INTERIM / "ai_index.parquet", index=False)
    logger.info(f"AI index: {G['G'].notna().sum()} country-year obs with G")


if __name__ == "__main__":
    main()
