"""
Standalone runner that mimics `libya_manager_wb_gas_recovery.ipynb` so we
can iterate on the INEN energy demand without the notebook UI.

Supports:
  --strategies "0,6003,6004,6005"
  --electricity  (if passed, runs NemoMod; otherwise skipped)
"""
import argparse
import logging
import os
import pathlib
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from utils.logger_utils import setup_clean_logger, mute_external_loggers  # noqa: E402

logger = setup_clean_logger("runner", logging.INFO)
mute_external_loggers(["sisepuede"])

import sisepuede as si  # noqa: E402
import sisepuede.core.attribute_table as att  # noqa: E402
import sisepuede.core.support_classes as sc  # noqa: E402
import sisepuede.manager.sisepuede_examples as sxl  # noqa: E402
import sisepuede.manager.sisepuede_file_structure as sfs  # noqa: E402
import sisepuede.manager.sisepuede_models as sm  # noqa: E402
import sisepuede.transformers as trf  # noqa: E402
import sisepuede.utilities._toolbox as sf  # noqa: E402
from ssp_transformations_handler.GeneralUtils import GeneralUtils  # noqa: E402
from ssp_transformations_handler.TransformationUtils import (  # noqa: E402
    TransformationYamlProcessor,
    StrategyCSVHandler,
)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--strategies", default="0,6003,6004,6005")
    p.add_argument("--electricity", action="store_true")
    p.add_argument("--input_csv", default=None)
    p.add_argument("--sim_end_year", type=int, default=2050)
    return p.parse_args()


def get_file_structure(y0=2015, y1=2050):
    file_struct = sfs.SISEPUEDEFileStructure(initialize_directories=False)
    key_tp = file_struct.model_attributes.dim_time_period
    key_year = file_struct.model_attributes.field_dim_year
    years = np.arange(y0, y1 + 1).astype(int)
    attribute_time_period = att.AttributeTable(
        pd.DataFrame({key_tp: range(len(years)), key_year: years}),
        key_tp,
    )
    file_struct.model_attributes.update_dimensional_attribute_table(attribute_time_period)
    return file_struct, attribute_time_period


def main():
    args = parse_args()
    g_utils = GeneralUtils()

    CURR_DIR = HERE
    SSP_MODELING_DIR = CURR_DIR.parent
    DATA_DIR = SSP_MODELING_DIR / "input_data"
    RUN_OUTPUT_DIR = SSP_MODELING_DIR / "ssp_run_output"
    TRANSFORMATIONS_DIR = SSP_MODELING_DIR / "transformations"
    SCENARIO_MAPPING_DIR = SSP_MODELING_DIR / "scenario_mapping"
    MISC_DIR = SSP_MODELING_DIR / "misc"
    CONFIG_DIR = CURR_DIR / "config_files"
    STRATEGIES_DEFINITIONS_FILE = TRANSFORMATIONS_DIR / "strategy_definitions.csv"
    STRATEGY_MAPPING_FILE = MISC_DIR / "strategy_mapping.yaml"

    config = g_utils.read_yaml(CONFIG_DIR / "config.yaml")
    input_csv = args.input_csv or config["ssp_input_file_name"]
    ssp_transformation_cw = config["ssp_transformation_cw"]
    country_name = config["country_name"]

    INPUT_FILE = DATA_DIR / input_csv
    logger.info(f"Input CSV: {INPUT_FILE}")

    _EXAMPLES = sxl.SISEPUEDEExamples()
    file_struct, attr_tp = get_file_structure(y1=args.sim_end_year)
    matt = file_struct.model_attributes

    # Build base inputs
    df_raw = pd.read_csv(INPUT_FILE)
    df_example = _EXAMPLES("input_data_frame")

    if "time_period" not in df_raw.columns:
        df_raw = df_raw.rename(columns={"period": "time_period"})
    df_inputs = g_utils.add_missing_cols(df_example, df_raw.copy())
    df_inputs["region"] = country_name
    df_inputs = df_inputs[df_inputs["year"] <= args.sim_end_year]

    # Setup transformations + strategies
    transformers = trf.transformers.Transformers(
        {},
        attr_time_period=attr_tp,
        df_input=df_inputs,
    )

    if not TRANSFORMATIONS_DIR.exists():
        trf.instantiate_default_strategy_directory(transformers, TRANSFORMATIONS_DIR)

    # Use existing transformation yamls (already generated)
    # Skip regenerating yamls - we use the ones committed to the repo.
    transformations = trf.Transformations(TRANSFORMATIONS_DIR, transformers=transformers)

    t0 = time.time()
    strategies = trf.Strategies(
        transformations,
        export_path="transformations",
        prebuild=True,
    )
    logger.info(f"Strategies built in {sf.get_time_elapsed(t0)}s")

    strategies_to_run = [int(s) for s in args.strategies.split(",")]
    logger.info(f"Strategies to run: {strategies_to_run}")

    # Build templates
    strategies.build_strategies_to_templates(strategies=strategies_to_run)

    ssp = si.SISEPUEDE(
        "calibrated",
        db_type="csv",
        initialize_as_dummy=not args.electricity,
        regions=[country_name],
        strategies=strategies,
        attribute_time_period=attr_tp,
    )

    dict_scens = {
        ssp.key_design: [0],
        ssp.key_future: [0],
        ssp.key_strategy: strategies_to_run,
    }

    t0 = time.time()
    ssp.project_scenarios(
        dict_scens,
        save_inputs=True,
        include_electricity_in_energy=args.electricity,
    )
    logger.info(f"Scenarios ran in {sf.get_time_elapsed(t0)}s")

    df_out = ssp.read_output(None)
    df_in = ssp.read_input(None)

    df_out["year"] = df_out["time_period"].apply(lambda t: 2015 + int(t))

    # Join primary_id to strategy_code so we can report by strategy
    # ssp.id_fs_safe already contains "sisepuede_run_..." prefix
    RUN_BASE = pathlib.Path(
        "/home/user/ssp_venv/lib/python3.11/site-packages/sisepuede/out"
    ) / ssp.id_fs_safe / f"{ssp.id_fs_safe}_output_database"
    att_primary = pd.read_csv(RUN_BASE / "ATTRIBUTE_PRIMARY.csv")
    att_strategy = pd.read_csv(RUN_BASE / "ATTRIBUTE_STRATEGY.csv")
    df_out = df_out.merge(att_primary[["primary_id", "strategy_id"]], on="primary_id", how="left")
    df_out = df_out.merge(att_strategy[["strategy_id", "strategy_code"]], on="strategy_id", how="left")

    # Summarize INEN energy demand per strategy
    inen_cols = [
        c
        for c in df_out.columns
        if c.startswith("energy_demand_inen_") and "subsector_total" not in c
    ]
    chart_cats = [
        "cement",
        "chemicals",
        "electronics",
        "glass",
        "lime_and_carbonite",
        "metals",
        "mining",
        "other_product_manufacturing",
        "paper",
        "plastic",
        "textiles",
        "wood",
    ]
    chart_cols = [
        c for c in inen_cols if any(c == f"energy_demand_inen_{x}" for x in chart_cats)
    ]
    df_out["total_chart_pj"] = df_out[chart_cols].sum(axis=1)
    df_out["total_all_inen_pj"] = df_out[inen_cols].sum(axis=1)

    # Export a summary
    SUM_OUT = RUN_OUTPUT_DIR / f"energy_validation_{ssp.id_fs_safe}.csv"
    cols_for_summary = [
        ssp.key_primary,
        "strategy_id",
        "strategy_code",
        "time_period",
        "year",
        "total_chart_pj",
        "total_all_inen_pj",
    ] + chart_cols
    df_out[[c for c in cols_for_summary if c in df_out.columns]].to_csv(SUM_OUT, index=False)
    logger.info(f"Wrote summary to {SUM_OUT}")

    print("\n===== Summary (total_chart_pj by strategy and year) =====")
    pivot = df_out.pivot_table(
        index="year",
        columns="strategy_code",
        values="total_chart_pj",
        aggfunc="sum",
    )
    sel = [2023, 2025, 2030, 2035, 2040, 2045, 2050]
    print(pivot.loc[pivot.index.isin(sel)].to_string())

    # full outputs
    RUN_ID_OUTPUT_DIR_PATH = RUN_OUTPUT_DIR / f"sisepuede_results_{ssp.id_fs_safe}"
    RUN_ID_OUTPUT_DIR_PATH.mkdir(parents=True, exist_ok=True)
    # Copy attribute tables too
    att_primary.to_csv(RUN_OUTPUT_DIR / "ATTRIBUTE_PRIMARY.csv", index=False)
    att_strategy.to_csv(RUN_OUTPUT_DIR / "ATTRIBUTE_STRATEGY.csv", index=False)
    df_out.to_csv(
        RUN_ID_OUTPUT_DIR_PATH / f"MODEL_OUTPUT_{ssp.id_fs_safe}.csv", index=False
    )
    df_in.to_csv(
        RUN_ID_OUTPUT_DIR_PATH / f"MODEL_INPUT_{ssp.id_fs_safe}.csv", index=False
    )
    print(f"\nRun dir: {RUN_ID_OUTPUT_DIR_PATH}")


if __name__ == "__main__":
    main()
