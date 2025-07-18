# SSP_Uganda

This repository contains notebooks and supporting files used to run the
**SISEPUEDE** model on Uganda's mitigation scenarios. All modeling resources
reside in the `ssp_modeling` folder described below.

## Get Started

Create a conda environment with Python 3.11 (you can use any name):

```bash
conda create -n sisepuede python=3.11
```

Activate the environment:

```bash
conda activate sisepuede
```

Install the working version of the sisepuede package:

```bash
pip install git+https://github.com/jcsyme/sisepuede.git@working_version
```

Install the cost benefits package:

```bash
pip install git+https://github.com/milocortes/costs_benefits_ssp.git@main
```

Install additional libraries:

```bash
pip install -r requirements.txt
```

## Project Structure

The most relevant files are inside the `ssp_modeling` directory:

- `config_files/` – YAML configuration files used by the notebooks.
- `input_data/` – Raw CSVs for each scenario.
- `notebooks/` – Jupyter notebooks that manage the modeling runs.
- `ssp_run/` – Output folders created after executing a scenario.
- `scenario_mapping/` – Spreadsheets with the mapping between SSP transformations and region-specific measures. This is where the scenarios and transformation intensities are defined.
- `transformations/` – CSVs and YAML files describing the transformations applied by the model.
- `output_postprocessing/` – R scripts used to rescale model results and
    generate processed outputs.

## Uganda Manager Workbooks

Three notebooks drive the modeling process:

- **`uganda_manager_wb_bau.ipynb`** – Runs the Business as Usual scenario using
    `bau_config.yaml`.
- **`uganda_manager_wb_asp.ipynb`** – Runs the ambition scenario defined in
    `asp_config.yaml`.
- **`uganda_manager_wb_bau_w_energy.ipynb`** – Runs a BaU case that also calls
    the energy model with `bau_energy_config.yaml`.

Each notebook loads the appropriate configuration file, prepares the input data
frame, applies the transformations listed in the corresponding workbook, and
produces a CSV in `ssp_run/<scenario>/` with the results.

## Rescaling

After running a scenario, the outputs can be rescaled to match the national
inventory targets. Scripts under
`output_postprocessing/scr/` (for example,
`run_script_baseline_run_new_asp.r`) load the simulation results, apply the
function defined in `rescale_function_baseline_mapping_timeref.r`, and overwrite
the CSV in `ssp_run/<scenario>/` with calibrated values.
