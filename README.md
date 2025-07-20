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

