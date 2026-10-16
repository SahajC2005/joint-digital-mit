"""
End-to-end pipeline driver.

Run each stage independently for development, or run this script to
execute the full pipeline. Each stage writes its output and downstream
stages read from disk, so partial runs are possible.

Usage:
    python -m src.run_pipeline                # full pipeline
    python -m src.run_pipeline --stage clean  # only data cleaning
    python -m src.run_pipeline --stage construct
    python -m src.run_pipeline --stage analysis

Stages in order:
  1. clean      - run all data/*.py modules to produce interim files
  2. construct  - run construct/*.py to build indices, MIT vars, panel
  3. analysis   - run analysis/run_specifications.py
"""

import argparse
import sys
from typing import List

from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


def run_clean():
    from src.data import findex, oxford_gari, stanford_ai_index, imf_aipi
    from src.data import ilo_exposure, kis_share, macro_controls, instruments

    modules = [
        ("findex", findex),
        ("oxford_gari", oxford_gari),
        ("stanford_ai_index", stanford_ai_index),
        ("imf_aipi", imf_aipi),
        ("ilo_exposure", ilo_exposure),
        ("kis_share", kis_share),
        ("macro_controls", macro_controls),
        ("instruments", instruments),
    ]
    for name, mod in modules:
        logger.info(f"=== clean: {name} ===")
        try:
            mod.main()
        except FileNotFoundError as e:
            logger.error(f"{name}: missing raw data: {e}")
        except Exception as e:
            logger.exception(f"{name}: failed with {e}")


def run_construct():
    from src.construct import fintech_index, ai_index, mit_variables, panel_merge

    for name, mod in [
        ("fintech_index", fintech_index),
        ("ai_index", ai_index),
        ("mit_variables", mit_variables),
        ("panel_merge", panel_merge),
    ]:
        logger.info(f"=== construct: {name} ===")
        try:
            mod.main()
        except Exception as e:
            logger.exception(f"{name}: failed with {e}")


def run_analysis():
    from src.analysis import run_specifications

    logger.info("=== analysis ===")
    try:
        run_specifications.main()
    except Exception as e:
        logger.exception(f"analysis failed: {e}")


def main(argv: List[str] = None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=["clean", "construct", "analysis", "all"],
        default="all",
    )
    args = parser.parse_args(argv)

    if args.stage in ("clean", "all"):
        run_clean()
    if args.stage in ("construct", "all"):
        run_construct()
    if args.stage in ("analysis", "all"):
        run_analysis()


if __name__ == "__main__":
    main(sys.argv[1:])
