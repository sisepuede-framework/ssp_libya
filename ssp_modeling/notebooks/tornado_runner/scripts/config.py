"""
config.py  (tornado)
---------------------
All configuration constants for the tornado experiment.
Edit RUN_ID and experiment parameters here; everything else is derived.

Key differences vs whirlpool:
  - PRIMARY_IDS_FILTER  : tornado strategy set (0, 760076 … 1340134)
  - CB_CONFIG_PATH      : cb_cost_factors/ subfolder
  - STRATEGY_CODE_BASE  : 'BASE'  (used as emission AND cost baseline in MAC)
  - Output suffix       : _tornado
"""

import pathlib

# ── Directory layout (derived from this file's location) ─────────────────────
SCRIPTS_DIR       = pathlib.Path(__file__).parent.resolve()
RUNNER_DIR        = SCRIPTS_DIR.parent                      # tornado_runner/
NOTEBOOKS_DIR     = RUNNER_DIR.parent                       # notebooks/
SSP_MODELING_DIR  = NOTEBOOKS_DIR.parent                    # ssp_modeling/
PROJECT_DIR       = SSP_MODELING_DIR.parent                 # repo root

DATA_DIR          = SSP_MODELING_DIR / "input_data"
RUN_OUTPUT_DIR    = SSP_MODELING_DIR / "ssp_run_output"

# ── Run to analyze ────────────────────────────────────────────────────────────
RUN_ID            = "sisepuede_results_sisepuede_run_2026-04-10T10;27;13.004973"
RUN_ID_OUTPUT_DIR = RUN_OUTPUT_DIR / RUN_ID

# ── Model time range ──────────────────────────────────────────────────────────
YEAR_START = 2015
YEAR_END   = 2070

# ── Post-processing parameters ────────────────────────────────────────────────
ISO_CODE3    = "LBY"
YEAR_REF     = 2023
REGION       = "libya"
TARGETS_PATH = SSP_MODELING_DIR / "output_postprocessing/data/invent/emission_targets_lby_2023.csv"
INVENT_DIR   = SSP_MODELING_DIR / "output_postprocessing/data/invent"

# Output paths for intermediate results
OUTPUT_DECOMPOSED      = RUN_ID_OUTPUT_DIR / "decomposed_ssp_output_tornado.csv"
OUTPUT_CB_DATA         = RUN_ID_OUTPUT_DIR / "cost_benefits_data_tornado.csv"
OUTPUT_MAC             = RUN_ID_OUTPUT_DIR / "marginal_abatement_costs_tornado.csv"

# ── Tableau output ─────────────────────────────────────────────────────────────
TABLEAU_DIR            = SSP_MODELING_DIR / "Tableau/data"
OUTPUT_TABLEAU_TORNADO = TABLEAU_DIR / "tableau_tornado.csv"

# ── Cost-benefits parameters ──────────────────────────────────────────────────
# Tornado uses cb_cost_factors/ (different subfolder than whirlpool)
CB_CONFIG_PATH = SSP_MODELING_DIR / "cost-benefits/cb_config_files/cb_config_params.xlsx"
CB_OUTPUT_PATH = SSP_MODELING_DIR / "cost-benefits/out"

# ── Strategy codes ────────────────────────────────────────────────────────────
# In tornado, 'BASE' serves as the reference for both emissions AND costs in MAC
STRATEGY_CODE_BASE     = "BASE"
STRATEGY_CODE_BASELINE = "BASE"   # alias used by mac_pipeline

# ── Primary IDs to analyze (tornado strategy set) ─────────────────────────────
import pandas as _pd
PRIMARY_IDS_FILTER = sorted(
    _pd.read_csv(RUN_ID_OUTPUT_DIR / "ATTRIBUTE_PRIMARY.csv")["primary_id"].tolist()
)

