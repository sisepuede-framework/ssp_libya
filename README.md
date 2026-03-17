# SSP_Libya

This repository contains notebooks and supporting files used to run the
**SISEPUEDE** model on Libya's mitigation scenarios. All modeling resources
reside in the `ssp_modeling` folder described below.

---

## Visualization

Explore the public visualization of Libya's case study here:  
[Libya Case Study – (Tableau)](https://public.tableau.com/app/profile/carlos.fabian.fuentes.rivas/viz/Libya_CaseStudy_v0/GHGsectorlayers)

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

---

## Workflow: Running the Model and Post-Processing

### 6. **Define the Configuration**

Edit the configuration file to specify the database and the strategies (scenarios) to run:

```
ssp_modeling/notebooks/config_files/config.yaml
```

This file controls which input data, transformations, and scenarios will be used in the model run.

---

### 7. **Run the Model**

With the configuration file set, execute the model using the following notebook:

```
ssp_modeling/notebooks/libya_manager_mar.ipynb
```

At the end of the notebook, the output directory path is exposed as `RUN_ID_OUTPUT_DIR_PATH`. This folder contains:

- The SISEPUEDE input/output files.
- A table with the transformations activated in each strategy.

---

### 8. **Run the Post-Processing**

Take the run ID from the previous step and open the post-processing script:

```
ssp_modeling/output_postprocessing/postprocessing_libya.r
```

> **Note:** Update the `run` object at the top of the script with the run ID of interest before executing.

```r
run <- 'sisepuede_results_sisepuede_run_<your_run_id>'
```

The script executes the following four routines in sequence:

#### 8.1 `run_script_baseline_run_new`

Computes intertemporal variations and rewrites the model output rescaled to the inventory values for each country. This produces a corrected output file aligned with national inventory baselines.

#### 8.2 `data_prep_new_mapping`

Takes the rescaled output and aggregates results into the new sector categories required for Tableau visualization.

#### 8.3 `data_prep_drivers`

Processes the aggregated outputs and generates the **drivers table** used for Tableau visualization.

#### 8.4 `#create levers table`

Generates the **levers (actions) table** used for Tableau visualization.

#### 8.5 `#create jobs table`

Generates the **jobs table** used for Tableau visualization.

---

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

