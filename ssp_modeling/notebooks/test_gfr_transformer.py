"""
End-to-end test of the new TFR:FGTV:INC_GAS_RECOVERY transformer on Libya.

Workflow:
1. Load sisepuede_raw_inputs_LBY_apr.csv and add the new GFR capture columns.
   Save as a new proposed input file.
2. Run SISEPUEDEModels on the baseline (no GFR active).
3. Apply TFR:FGTV:INC_GAS_RECOVERY via the Transformers class (magnitude=0.5
   applied to fuel_crude) and re-run.
4. Compare FGTV emissions between the two scenarios and report the deltas.

Run from conda env ssp_libya_env:
    conda activate ssp_libya_env
    cd /Users/fabianfuentes/git/ssp_libya/ssp_modeling/notebooks
    python test_gfr_transformer.py
"""

import os
import sys
import pathlib
import warnings
from typing import Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# Paths (mirror libya_manager_wb_apr.ipynb convention)
# -----------------------------------------------------------------------------
CURR_DIR = pathlib.Path(__file__).resolve().parent
SSP_MODELING_DIR = CURR_DIR.parent
DATA_DIR = SSP_MODELING_DIR / "input_data"

INPUT_FILE = DATA_DIR / "sisepuede_raw_inputs_LBY_apr.csv"
OUTPUT_INPUT_FILE = DATA_DIR / "sisepuede_raw_inputs_LBY_apr_with_gfr.csv"
OUTPUT_DIR = SSP_MODELING_DIR / "ssp_run_output" / "test_gfr"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# SISEPUEDE imports
# -----------------------------------------------------------------------------
import sisepuede.core.attribute_table as att
import sisepuede.core.support_classes as sc
import sisepuede.manager.sisepuede_examples as sxl
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm
import sisepuede.transformers.transformers as trfs
import sisepuede.utilities._toolbox as sf


# -----------------------------------------------------------------------------
# Helper: build SISEPUEDE file structure with correct time-period horizon
# -----------------------------------------------------------------------------
def build_file_structure(y0: int = 2015, y1: int = 2050) -> Tuple:
    fstruct = sfs.SISEPUEDEFileStructure(initialize_directories=False)
    key_tp = fstruct.model_attributes.dim_time_period
    key_yr = fstruct.model_attributes.field_dim_year

    years = np.arange(y0, y1 + 1).astype(int)
    attr_tp = att.AttributeTable(
        pd.DataFrame({key_tp: range(len(years)), key_yr: years}),
        key_tp,
    )
    fstruct.model_attributes.update_dimensional_attribute_table(attr_tp)
    return fstruct, attr_tp


def compare_fgtv(df_base: pd.DataFrame, df_gfr: pd.DataFrame, tag: str):
    """Print comparison of FGTV emissions for the two scenarios."""
    cols = [
        c for c in df_base.columns
        if c.startswith("emission_co2e_")
        and "_fgtv_" in c
        and any(s in c for s in ("flaring", "venting", "dtp"))
    ]
    print(f"\n{'='*110}\n{tag}\n{'='*110}")
    print(f"Found {len(cols)} FGTV emission columns\n")

    # Group by fuel and stream (sum CH4+CO2+N2O)
    summary = {}
    for c in cols:
        parts = c.split("_fgtv_")[1]
        stream = parts.split("_fuel_")[0]
        fuel = "fuel_" + parts.split("_fuel_")[1]
        key = (fuel, stream)
        summary.setdefault(key, []).append(c)

    # Print table: per (fuel, stream), baseline vs GFR at key time periods
    tps = [0, 10, 20, 25, 30, 35]
    header = f"  {'(fuel, stream)':28s} │ "
    for t in tps:
        header += f"{f't={t}':>16s}"
    print(header)
    print(f"  {'':28s} │ " + " ".join(f"{'base / gfr':>15s}" for _ in tps))
    print("  " + "─"*(28+3+16*len(tps)))
    for key in sorted(summary):
        fuel, stream = key
        cols_here = summary[key]
        vals_base = [df_base.loc[df_base["time_period"] == t, cols_here].sum(axis=1).iloc[0] for t in tps]
        vals_gfr = [df_gfr.loc[df_gfr["time_period"] == t, cols_here].sum(axis=1).iloc[0] for t in tps]
        row = f"  {fuel+', '+stream:28s} │ "
        for vb, vg in zip(vals_base, vals_gfr):
            row += f"{vb:>7.3g}/{vg:<7.3g}"
        print(row)

    # Totals
    all_cols = [c for group in summary.values() for c in group]
    print("  " + "─"*(28+3+16*len(tps)))
    row_base = f"  {'TOTAL (baseline)':28s} │ "
    row_gfr = f"  {'TOTAL (GFR active)':28s} │ "
    row_delta = f"  {'DELTA':28s} │ "
    row_pct = f"  {'% change':28s} │ "
    for t in tps:
        vb = df_base.loc[df_base["time_period"] == t, all_cols].sum(axis=1).iloc[0]
        vg = df_gfr.loc[df_gfr["time_period"] == t, all_cols].sum(axis=1).iloc[0]
        row_base += f"{vb:>16.2f}"
        row_gfr += f"{vg:>16.2f}"
        row_delta += f"{vg-vb:>+16.2f}"
        row_pct += f"{((vg/vb-1)*100 if vb>0 else 0):>+15.1f}%"
    print(row_base)
    print(row_gfr)
    print(row_delta)
    print(row_pct)

    # Cumulative reduction for NDC target comparison
    # Libya NDC target: -85 MtCO2e cumulative FGTV reduction over 2026-2035 (Conditional)
    # In time_periods: 2026 = t=11, 2035 = t=20 (if y0=2015)
    t_ndc_range = list(range(11, 21))
    cum_base = sum(df_base.loc[df_base["time_period"] == t, all_cols].sum(axis=1).iloc[0] for t in t_ndc_range)
    cum_gfr = sum(df_gfr.loc[df_gfr["time_period"] == t, all_cols].sum(axis=1).iloc[0] for t in t_ndc_range)
    cum_delta = cum_base - cum_gfr
    print(f"\n  ─── NDC target comparison ───")
    print(f"  Cumulative FGTV 2026-2035 (baseline):    {cum_base:>8.2f}  MtCO2e")
    print(f"  Cumulative FGTV 2026-2035 (GFR):         {cum_gfr:>8.2f}  MtCO2e")
    print(f"  Cumulative REDUCTION from GFR:           {cum_delta:>8.2f}  MtCO2e")
    print(f"  Libya NDC target (Conditional):             85.00  MtCO2e")
    ratio = cum_delta / 85.0 if cum_delta > 0 else 0
    print(f"  Ratio (achieved / target):               {ratio:>8.2f}x")
    if ratio > 1.2:
        print(f"  → magnitude=0.5 is TOO HIGH for Conditional; calibrate DOWN (try ~{0.5/ratio:.2f})")
    elif ratio < 0.8:
        print(f"  → magnitude=0.5 is too low for Conditional; calibrate UP (try ~{0.5/ratio:.2f})")
    else:
        print(f"  → magnitude=0.5 is roughly in range for Conditional")


# -----------------------------------------------------------------------------
# Step 1: Load apr input and add GFR capture columns
# -----------------------------------------------------------------------------
print("="*80)
print("STEP 1: Propose new input file with GFR capture columns")
print("="*80)

df_raw = pd.read_csv(INPUT_FILE)
print(f"Loaded {INPUT_FILE.name}: {df_raw.shape}")

# Ensure region / nation fields present
if "region" not in df_raw.columns:
    df_raw["region"] = "libya"

# Add the 3 new GFR capture columns (default = 0 for baseline)
new_cols = [
    "frac_fgtv_capture_associated_gas_fuel_coal",
    "frac_fgtv_capture_associated_gas_fuel_crude",
    "frac_fgtv_capture_associated_gas_fuel_oil",
]
for c in new_cols:
    if c not in df_raw.columns:
        df_raw[c] = 0.0
        print(f"  Added column: {c} (zeros)")
    else:
        print(f"  Column already present: {c}")

df_raw.to_csv(OUTPUT_INPUT_FILE, index=False)
print(f"\nWrote proposed input: {OUTPUT_INPUT_FILE.name}  ({df_raw.shape})")

# -----------------------------------------------------------------------------
# Step 2: Setup SISEPUEDE
# -----------------------------------------------------------------------------
print(f"\n{'='*80}\nSTEP 2: Setup SISEPUEDE\n{'='*80}")

fstruct, attr_tp = build_file_structure(y0=2015, y1=2050)
matt = fstruct.model_attributes

# add missing columns (pattern from libya_manager_wb_apr.ipynb)
examples = sxl.SISEPUEDEExamples()
df_example = examples("input_data_frame")

# Missing fields from apr input
all_fields = set(matt.all_variable_fields_input)
present = set(df_raw.columns)
missing = sorted(all_fields - present)
print(f"Missing input fields vs schema: {len(missing)}")
if missing:
    print("  First 10:", missing[:10])

# Fill missing cols from example df (zeros or example defaults)
for c in missing:
    if c in df_example.columns:
        # broadcast example t=0 value to all periods
        df_raw[c] = df_example[c].iloc[0] if len(df_example) > 0 else 0.0
    else:
        df_raw[c] = 0.0
print(f"Filled {len(missing)} missing columns from example defaults")

# Instantiate models (electricity enabled — FGTV depends on fuel production
# which comes from NemoMod/EnergyProduction)
models = sm.SISEPUEDEModels(
    matt,
    allow_electricity_run=True,
    fp_julia=fstruct.dir_jl,
    fp_nemomod_reference_files=fstruct.dir_ref_nemo,
    initialize_julia=True,  # Spin up Julia + NemoMod for fuel production → FGTV
)
print("SISEPUEDEModels initialized (electricity + Julia enabled)")

# -----------------------------------------------------------------------------
# Step 3: Run BASELINE (no GFR) and GFR-ACTIVE scenarios
# -----------------------------------------------------------------------------
print(f"\n{'='*80}\nSTEP 3: Run baseline + GFR scenarios\n{'='*80}")

# Instantiate Transformers (needed to apply GFR to the input)
transformers = trfs.Transformers(
    {},
    attr_time_period=attr_tp,
    df_input=df_raw,
)

# --- BASELINE run: no transformations applied ---
df_base_input = df_raw.copy()
print("\nRunning BASELINE (no GFR)...")
try:
    df_base_out = models.project(
        df_base_input,
        include_electricity_in_energy=True,
    )
    print(f"  Baseline run OK: output shape {df_base_out.shape}")
except Exception as e:
    print(f"  Baseline run FAILED: {type(e).__name__}: {e}")
    sys.exit(1)

# --- GFR-ACTIVE run: apply TFR:FGTV:INC_GAS_RECOVERY ---
# Build implementation ramp: zero for first 10 years, then linear 2025→2050
n_tp = len(attr_tp.key_values)
vec_ramp = np.concatenate([
    np.zeros(10),                                    # 2015-2024: no GFR
    sf.ramp_vector(n_tp - 10),                       # 2025-2050: ramp
])
print(f"\nImplementation ramp: vec_ramp[0:12]={vec_ramp[:12]}")
print(f"                     vec_ramp[-3:]={vec_ramp[-3:]}")

transformer_gfr = transformers.get_transformer("TFR:FGTV:INC_GAS_RECOVERY")
print(f"Transformer retrieved: {transformer_gfr.code}")

# Apply transformer: magnitude=0.5 (50% capture) at final time period
df_gfr_input = transformer_gfr(
    df_input=df_raw,
    magnitude=0.5,
    vec_implementation_ramp=vec_ramp,
)

# Verify the transformer did modify the GFR columns
print("\nGFR columns AFTER transformer application (sample):")
for c in new_cols:
    vals = df_gfr_input[c].values
    print(f"  {c}: t0={vals[0]:.3f}  t10={vals[10]:.3f}  t20={vals[20]:.3f}  t35={vals[35]:.3f}")

print("\nRunning GFR-ACTIVE scenario...")
try:
    df_gfr_out = models.project(
        df_gfr_input,
        include_electricity_in_energy=True,
    )
    print(f"  GFR run OK: output shape {df_gfr_out.shape}")
except Exception as e:
    print(f"  GFR run FAILED: {type(e).__name__}: {e}")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Step 4: Compare FGTV emissions
# -----------------------------------------------------------------------------
print(f"\n{'='*80}\nSTEP 4: Compare FGTV emissions\n{'='*80}")
compare_fgtv(df_base_out, df_gfr_out, "FGTV EMISSIONS (MtCO2e): baseline vs GFR@0.5 crude+coal+oil")

# Save outputs for post-analysis
df_base_out.to_csv(OUTPUT_DIR / "libya_output_baseline.csv", index=False)
df_gfr_out.to_csv(OUTPUT_DIR / "libya_output_gfr.csv", index=False)
print(f"\nOutputs saved in: {OUTPUT_DIR}")
print("  libya_output_baseline.csv  (no GFR)")
print("  libya_output_gfr.csv       (GFR at 0.5 all upstream fuels)")

print(f"\n{'='*80}\nDONE\n{'='*80}")
