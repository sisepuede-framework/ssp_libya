# Replicate the Libya SISEPUEDE setup on a new machine

End-to-end install recipe for the **Libya NDC** modeling stack, including:

- SISEPUEDE core **with the `TFR:FGTV:INC_GAS_RECOVERY` (Gas Flaring Recovery) transformer** we added
- `costs_benefits_ssp` with the new **GFR cost + benefit** entries
- `ssp_libya` with the Libya-specific input data, YAML transformations, and the strategies `BASE / Unconditional / Conditional`

This repo (`ssp_libya`) is the entry point; the other two are dependencies installed in editable mode.

---

## 1. Prerequisites

- **macOS or Linux** (Windows should work via WSL; paths below use macOS)
- **git** ≥ 2.30
- **Miniconda or Anaconda** (for Python env management)
- **GitHub CLI `gh`** (optional, for PR workflow)
- Internet access (Julia + NemoMod download the first time `EnergyProduction` runs; ~1 GB)
- A working Python toolchain for native extensions (on macOS: `xcode-select --install`)

No Gurobi license is needed — the NemoMod solver uses open-source HiGHS by default (unless explicitly configured otherwise in the notebook).

---

## 2. Clone the three repositories

Pick a parent directory (example: `~/git`) and clone all three:

```bash
mkdir -p ~/git && cd ~/git

# SISEPUEDE core (our fork, with the GFR transformer)
git clone https://github.com/sisepuede-framework/sisepuede.git
cd sisepuede
git checkout feature/fgtv-gas-recovery
cd ..

# Costs & Benefits (GFR cost + benefit rows registered)
git clone https://github.com/sisepuede-framework/costs_benefits_ssp.git
cd costs_benefits_ssp
git checkout feature/fgtv-gas-recovery-costs   # until PR #5 is merged; then `main`
cd ..

# Libya-specific inputs, YAMLs, notebooks (this repo)
git clone https://github.com/sisepuede-framework/ssp_libya.git
cd ssp_libya
git checkout tornado_update
cd ..
```

Verify you're on the right branches:

```bash
(cd sisepuede            && git log --oneline -2)
# expected top commit: "Register TFR:FGTV:INC_GAS_RECOVERY in strategy attribute tables"

(cd costs_benefits_ssp   && git log --oneline -2)
# expected top commit: "merge origin/main resolviendo conflictos..."
#                 or:  "renombra benefit GFR a categoría propia..."

(cd ssp_libya            && git log --oneline -2)
# expected top commit: "gas recovery fgtv fix"
```

---

## 3. Create the conda environment

```bash
conda create -n ssp_libya_env python=3.11 -y
conda activate ssp_libya_env
```

Install Python deps (pandas 2.x, numpy, openpyxl, ruamel.yaml, juliacall, etc.):

```bash
# From the sisepuede repo — includes all runtime deps except cb and libya specifics
pip install -r ~/git/sisepuede/requirements.txt

# If sisepuede/requirements.txt is missing or incomplete, install manually:
pip install numpy pandas openpyxl ruamel.yaml juliacall pyDOE2 sqlalchemy polars matplotlib seaborn jupyterlab

# Libya notebook extras
pip install geopandas  # only if plots use mapping; otherwise skip
```

---

## 4. Editable installs

The core idea: install both SISEPUEDE and costs_benefits_ssp in **editable mode** (`pip install -e`) so any future code changes in the git worktrees are picked up automatically without reinstalling.

```bash
# SISEPUEDE core
pip install -e ~/git/sisepuede

# Costs & Benefits
pip install -e ~/git/costs_benefits_ssp
```

Verify both:

```bash
python -c "import sisepuede, costs_benefits_ssp; print(sisepuede.__file__); print(costs_benefits_ssp.__file__)"
```

Both paths must point to `~/git/...`, **not** to `site-packages/`. If they point to site-packages, remove the orphan directory there and re-install (see **Known pitfalls** below).

---

## 5. Verify the GFR transformer is installed

```bash
python <<'PY'
import sisepuede
import sisepuede.transformers as trf

# Check the transformer registration
transformers = trf.transformers.Transformers({}, df_input=None)
has_gfr = hasattr(transformers, "fgtv_increase_gas_recovery")
print(f"GFR transformer present in sisepuede.Transformers: {has_gfr}")

# Check the attribute CSV has the code
import pathlib
attr = pathlib.Path(sisepuede.__file__).parent / "attributes" / "attribute_transformer_code.csv"
with open(attr) as f:
    text = f.read()
print(f"TFR:FGTV:INC_GAS_RECOVERY in attribute table: {'TFR:FGTV:INC_GAS_RECOVERY' in text}")
PY
```

Both should print `True`.

---

## 6. Verify the GFR cost + benefit entries are installed

```bash
python <<'PY'
import sqlite3, costs_benefits_ssp, pathlib
db = pathlib.Path(costs_benefits_ssp.__file__).parent / "database" / "backup" / "cb_data.db"
conn = sqlite3.connect(db)
for q, label in [
    ("SELECT COUNT(*) FROM attribute_transformation_code WHERE transformation_code='TX:FGTV:INC_GAS_RECOVERY'", "GFR transformation code"),
    ("SELECT COUNT(*) FROM transformation_costs WHERE transformation_code='TX:FGTV:INC_GAS_RECOVERY'", "GFR cost + benefit rows"),
    ("SELECT COUNT(*) FROM tx_table WHERE output_variable_name='cb:fgtv:gas_recovery_savings:X:X'", "GFR benefit in its own category"),
]:
    print(f"{label}: {conn.execute(q).fetchone()[0]} (expected: 1, 2, 1)")
conn.close()
PY
```

---

## 7. Run the Libya notebook

The canonical entry point is:

```
ssp_libya/ssp_modeling/notebooks/libya_manager_wb_gas_recovery.ipynb
```

1. Launch Jupyter: `jupyter lab` from `~/git/ssp_libya`
2. Open the notebook above
3. **Kernel → Restart** (forces fresh imports)
4. Run all cells

Key cells:

| Cell | What it does |
|---|---|
| ~20 | Instantiates `Transformers(...)` — GFR transformer must be registered here |
| ~29 | Registers strategies `Unconditional`, `Conditional` (we dropped `BAU` in our setup; see cell 44) |
| ~44 | `strategies_to_run = [0, 6004, 6005]` — BASE, Unconditional, Conditional only |
| ~51 | `ssp.project_scenarios(...)` with `save_inputs=True` — generates `MODEL_OUTPUT` CSVs |

The run takes **~20–40 minutes** on a laptop (the bottleneck is NemoMod LP solving electricity dispatch per strategy).

---

## 8. Where outputs land

After a successful run, outputs appear under:

```
ssp_libya/ssp_modeling/ssp_run_output/
├── ATTRIBUTE_PRIMARY.csv
├── ATTRIBUTE_STRATEGY.csv
└── sisepuede_results_sisepuede_run_<timestamp>/
    ├── MODEL_INPUT_*.csv          (because save_inputs=True)
    ├── MODEL_OUTPUT_*.csv
    └── WIDE_INPUTS_OUTPUTS_*.csv   (inputs + outputs joined, used by the CBA)
```

To visualize, open the Tableau workbook at `ssp_modeling/Tableau/` or the plotting notebook `emissions_intensity.ipynb`.

---

## 9. Run the CBA

From the notebook or a standalone script:

```python
from costs_benefits_ssp.cb_calculate import CostBenefits
import pandas as pd, os

RESULTS = "~/git/ssp_libya/ssp_modeling/ssp_run_output/<latest_run_dir>/"
ssp_data = pd.read_csv(os.path.join(RESULTS, "WIDE_INPUTS_OUTPUTS_<...>.csv"))
att_primary = pd.read_csv(os.path.join(RESULTS, "..", "ATTRIBUTE_PRIMARY.csv"))
att_strategy = pd.read_csv(os.path.join(RESULTS, "..", "ATTRIBUTE_STRATEGY.csv"))

cb = CostBenefits(ssp_data, att_primary, att_strategy, strategy_code_base="BASE")

# Load Libya-specific cost config
cb.load_cb_parameters(os.path.expanduser(
    "~/git/ssp_libya/ssp_modeling/cost-benefits/cb_config_files/cb_config_params.xlsx"
))

results = cb.compute_technical_cost_for_all_strategies()

# Filter GFR-specific cost + benefit
gfr = results[results["variable"].str.contains("gas_recovery")]
print(gfr.groupby(["strategy_code", "variable"])["value"].sum())
```

Expected for `Conditional` cumulative 2026–2035 (GFR magnitude ≈ 0.75):

- `cb:fgtv:technical_cost:gas_recovery:X`    ≈ **+$1.0 B** (CAPEX)
- `cb:fgtv:gas_recovery_savings:X:X`         ≈ **−$0.17 B** (conservative placeholder; user-calibrated)

---

## 10. Known pitfalls

### **10.1 `sisepuede.__file__ = None`** after `pip install`

Happens when there's an orphan `sisepuede/` directory in `site-packages` from a prior wheel install without an `__init__.py`. Python creates a namespace-package that conflicts with the editable install.

Fix:
```bash
# Find the orphan
find $(python -c "import site; print(site.getsitepackages()[0])") -type d -name sisepuede
# If you see one that does NOT point to ~/git/sisepuede, remove it:
rm -rf <path>
```
Then `pip install -e ~/git/sisepuede` again.

### **10.2 `tmp_cb_data.db` out of sync**

The `costs_benefits_ssp` runtime sometimes caches into `tmp_cb_data.db`. If you just updated `cb_data.db` (backup) but results look stale:

```bash
rm -f ~/git/costs_benefits_ssp/costs_benefits_ssp/database/tmp_cb_data.db
```

It regenerates on the next `CostBenefits(...)` instantiation.

### **10.3 NumPy 2.x / pandas 2.x warnings**

You may see warnings like `AttributeError: _ARRAY_API not found` at import time. Safe to ignore if followed by working pandas calls. If pandas actually breaks:

```bash
pip install --upgrade pandas numpy
# or pin if a specific version is required
```

### **10.4 Jupyter kernel has stale modules**

After any `pip install -e` or edit to the git repos: **Kernel → Restart**. Otherwise old modules stay cached and you'll see phantom `AttributeError`s.

### **10.5 Julia slow on first run**

First call to `EnergyProduction.project(...)` triggers Julia package download and precompilation (~5 minutes one-time). Second run uses the cached Julia env under `sisepuede/julia/`.

---

## 11. What's on each branch

| Repo | Branch | Why |
|---|---|---|
| `sisepuede-framework/sisepuede` | `feature/fgtv-gas-recovery` | adds `TFR:FGTV:INC_GAS_RECOVERY` transformer + its attribute registrations |
| `sisepuede-framework/costs_benefits_ssp` | `feature/fgtv-gas-recovery-costs` | adds GFR cost ($14.5/tCO₂e) + benefit (category `gas_recovery_savings`) — PR #5 |
| `sisepuede-framework/ssp_libya` | `tornado_update` | Libya inputs with GFR column, YAMLs for Unconditional/Conditional, notebook `libya_manager_wb_gas_recovery.ipynb` |

When the upstream PRs land (PR #5 on costs_benefits_ssp; and eventually a PR to `jcsyme/sisepuede`), switch to `main` on those repos.

---

## 12. Reference docs

- **GFR transformer technical memo** (English, for James): `sisepuede/TFR_FGTV_INC_GAS_RECOVERY.md` on the `feature/fgtv-gas-recovery` branch
- **CBA README**: `costs_benefits_ssp/README.md`
- **Libya strategy definitions**: `ssp_libya/ssp_modeling/transformations/strategy_definitions.csv` (rows 77–78 for Unconditional/Conditional; 76 for BAU which we skip)
- **CBA config for Libya**: `ssp_libya/ssp_modeling/cost-benefits/cb_config_files/cb_config_params.xlsx`
