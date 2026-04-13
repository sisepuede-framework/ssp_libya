"""
config.py
---------
All configuration constants and derived paths for the whirlpool experiment.
Edit RUN_ID and the experiment parameters here; everything else is derived.
"""

import pathlib

# ── Directory layout (derived from this file's location) ─────────────────────
SCRIPTS_DIR       = pathlib.Path(__file__).parent.resolve()
RUNNER_DIR        = SCRIPTS_DIR.parent                      # whirlpool_runner/
NOTEBOOKS_DIR     = RUNNER_DIR.parent                       # notebooks/
SSP_MODELING_DIR  = NOTEBOOKS_DIR.parent                    # ssp_modeling/
PROJECT_DIR       = SSP_MODELING_DIR.parent                 # repo root

DATA_DIR          = SSP_MODELING_DIR / "input_data"
RUN_OUTPUT_DIR    = SSP_MODELING_DIR / "ssp_run_output"

# ── Run to analyze ────────────────────────────────────────────────────────────
RUN_ID            = "sisepuede_results_sisepuede_run_2026-04-09T19;31;17.019336"
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
OUTPUT_DECOMPOSED  = RUN_ID_OUTPUT_DIR / "decomposed_ssp_output_whirlpool.csv"
OUTPUT_CB_DATA     = RUN_ID_OUTPUT_DIR / "cost_benefits_data_whirlpool.csv"
OUTPUT_MAC         = RUN_ID_OUTPUT_DIR / "marginal_abatement_costs_whirlpool.csv"

# ── Tableau output ─────────────────────────────────────────────────────────────
TABLEAU_DIR                     = SSP_MODELING_DIR / "Tableau/data"
OUTPUT_TABLEAU_WHIRLPOOL        = TABLEAU_DIR / "tableau_whirlpool.csv"
OUTPUT_MAC_TORNADO_TO_WHIRLPOOL = TABLEAU_DIR / "mac_tornado_to_whirlpool.csv"

# ── Tornado run reference (for tornado vs whirlpool comparison) ───────────────
TORNADO_RUN_ID  = "sisepuede_results_sisepuede_run_2026-04-10T10;27;13.004973"
TORNADO_MAC_PATH = RUN_OUTPUT_DIR / TORNADO_RUN_ID / "marginal_abatement_costs_tornado.csv"

# ── Cost-benefits parameters ──────────────────────────────────────────────────
CB_CONFIG_PATH = SSP_MODELING_DIR / "cost-benefits/cb_config_files/cb_config_params.xlsx"
CB_OUTPUT_PATH = SSP_MODELING_DIR / "cost-benefits/out"

# ── Strategy codes ────────────────────────────────────────────────────────────
STRATEGY_CODE_BASE      = "BASE"       # used by CostBenefits as reference
STRATEGY_CODE_PFLO_HBLE = "PFLO:ALL"  # full portfolio baseline used in MAC

# ── Primary IDs to analyze — read dynamically from the run's attribute table ──
import pandas as _pd
PRIMARY_IDS_FILTER = sorted(
    _pd.read_csv(RUN_ID_OUTPUT_DIR / "ATTRIBUTE_PRIMARY.csv")["primary_id"].tolist()
)
