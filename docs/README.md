# Joint Digital Transformation and the Middle-Income Trap

Replication package for "FinTech, AI, and the Middle-Income Trap: Joint Digital
Transformation as an Escape Mechanism."

## What this package does

Constructs a country-year panel covering:

- **F**: FinTech penetration index (Global Findex, following Chhetri-Koirala 2026)
- **G**: AI penetration index (Oxford GARI + Stanford AI Index + IMF AIPI)
- **rho**: ILO occupational AI exposure (time-invariant, ILO WP 140)
- **sigma_KIS**: Knowledge-intensive services employment share (GGDC + ILOSTAT)
- **H**: Human capital (Penn World Tables + Barro-Lee)
- **I**: Institutional quality (Worldwide Governance Indicators)
- **MI**: Middle-income indicator (World Bank income classifications)
- **g, X**: Growth and macro controls (WDI + PWT)

## Pipeline

```
01_download_raw.py     ->  data/raw/      (one file per source)
02_clean_sources.py    ->  data/interim/  (harmonized country-year)
03_construct_indices.py->  data/interim/  (F, G with PCA robustness)
04_merge_panel.py      ->  data/processed/panel.parquet
05_run_analysis.py     ->  output/        (tables, figures, logs)
```

## Reproducibility

- All raw downloads timestamped and checksummed
- Country names harmonized to ISO 3166-1 alpha-3 codes
- Missing-data rules documented per variable in `config/variable_specs.yaml`
- Random seeds fixed where applicable
- Package versions pinned in `requirements.txt`

## Authors

[Three-author team — TBD]

## Status

Draft pipeline. Not yet executed end-to-end pending data downloads.
