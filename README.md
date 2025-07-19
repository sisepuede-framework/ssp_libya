# SSP_Uganda

This repository contains notebooks and supporting files used to run the
**SISEPUEDE** model on Uganda's mitigation scenarios. All modeling resources
reside in the `ssp_modeling` folder described below.

Absolutely! Here’s an updated version of the instructions, emphasizing the use of the `.yml` file and how to set a custom environment name.

---

## Instructions: Setting Up the SISEPUEDE Environment

### 1. **Go to the `environment.yml` file**

Obtain the provided `environment.yml` file for SISEPUEDE.

---

### 2. **Set a Custom Environment Name**

Open the `environment.yml` file in your preferred text editor (such as VS Code, Atom, nano, or even Notepad).
At the very top, you'll see a line like:

```yaml
name: sisepuede
```

**Change `sisepuede` to your preferred environment name, usually related to the region you are working with** (e.g., `ssp-mex`, `ssp-usa`, or whatever you'd like).

For example:

```yaml
name: ssp-mex
```

---

### 3. **Create the Environment from the `.yml` File**

In your terminal, navigate to the directory containing your `environment.yml` file, then run:

```bash
conda env create -f environment.yml
```

This will create a new Conda environment with the name you set in the file.

---

### 4. **Activate the Environment**

After installation, activate your new environment with:

```bash
conda activate <your_env_name>
```

*(Replace `<your_env_name>` with the name you specified in the `.yml` file, e.g., `ssp-mex`)*

---

### 5. **Done!**

Your environment is now ready to use, with all dependencies (including those installed via pip) preconfigured.

---

#### **Tips:**

* If you update the `environment.yml` file later, you can update your environment with:

  ```bash
  conda env update -f environment.yml --prune
  ```
* You can list all your environments with:

  ```bash
  conda env list
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
