"""
tableau_postprocessing.py
-------------------------
Python port of the R post-processing pipeline that produces Tableau-ready
CSVs from a SISEPUEDE run output. Replaces:

  - ssp_modeling/output_postprocessing/scr/invent/data_prep_new_mapping.r
  - ssp_modeling/output_postprocessing/scr/invent/data_prep_drivers.r
  - ssp_modeling/output_postprocessing/scr/levers_table/#create levers table.r
  - ssp_modeling/output_postprocessing/scr/levers_table/#create jobs table.r

Usage from a manager notebook:

    from shared_scripts.tableau_postprocessing import run_tableau_postprocessing

    run_tableau_postprocessing(
        run_dir         = RUN_ID_OUTPUT_DIR_PATH,
        project_dir     = PROJECT_DIR,
        region          = "libya",
        iso_code3       = "LBY",
        year_ref        = 2023,
    )

Outputs land in `<project_dir>/ssp_modeling/tableau/data/`:
  - decomposed_emissions_<region>_<year_ref>.csv   (HP-smoothed, EDGAR + SISEPUEDE)
  - drivers_<region>.csv                            (driver variables + GDP history)
  - fgtv_volumes_<region>.csv                       (oil/gas production + flaring/venting/fugitive volumes, m^3)
  - tableau_levers_table_complete.csv               (levers + stakeholder merge)
  - jobs_demand_<region>.csv                        (employment subset)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from statsmodels.tsa.filters.hp_filter import hpfilter


# ---------------------------------------------------------------------------
# HP filter (port of R hp_filter_subsec)
# ---------------------------------------------------------------------------

def _hp_smooth_series(values: np.ndarray, lambda_hp: float) -> np.ndarray:
    """Anchored, non-negative HP trend matching the R hp_filter_subsec output."""
    if len(values) < 2:
        return values.copy()
    _, trend = hpfilter(values.astype(float), lamb=lambda_hp)
    sm = np.maximum(trend, 0.0)
    sm = np.maximum(sm + (values[0] - sm[0]), 0.0)
    sm[0] = values[0]
    return sm


def _apply_hp_to_subsec_gas(
    df: pd.DataFrame,
    subsec: str,
    gases,
    lambda_hp: float,
    by_cols=("primary_id", "strategy_id", "design_id", "future_id", "Code"),
    time_col: str = "Year",
    value_col: str = "value",
) -> pd.DataFrame:
    """Apply HP smoothing per group for matching (subsector, gas) rows.

    Updates `value_hp` in place and replaces `value` with the smooth where set.
    Mirrors hp_filter_subsec(replace_original=TRUE) from data_prep_new_mapping.r,
    including the side-effect that the R helper re-snapshots `value_original`
    from the *current* value column at the start of every call (so HP-filtered
    rows end up with their own smoothed value in `value_original` after the
    final call). We replicate that for byte-level parity with the R output.
    """
    if isinstance(gases, str):
        gases = [gases]
    # R's hp_filter_subsec resets value_original = value for all rows on every call.
    df["value_original"] = df["value"].astype(float)
    mask = (
        (df["subsector"] == subsec)
        & (df["Gas"].isin(gases))
        & df["strategy_id"].notna()
    )
    if not mask.any():
        return df

    sub = df.loc[mask]
    smoothed = pd.Series(np.nan, index=sub.index, dtype=float, name="value_hp")
    for _, idx in sub.groupby(list(by_cols), dropna=False).indices.items():
        ordered = sub.iloc[idx].sort_values(time_col)
        v = ordered[value_col].astype(float).to_numpy()
        sm = _hp_smooth_series(v, lambda_hp)
        smoothed.loc[ordered.index] = sm

    df.loc[smoothed.index, "value_hp"] = smoothed.values
    valid = smoothed.notna()
    if valid.any():
        df.loc[smoothed.index[valid], value_col] = smoothed[valid].values
    return df


# Default smoothing schedule used by data_prep_new_mapping.r
HP_SCHEDULE = [
    ("1.A.1 - Fuel Production",                                          ["CO2"],  200),
    ("1.A.1 - Fuel Production",                                          ["CH4"],  200),
    ("1.B - Fugitive emissions from fuels",                              ["CO2"], 1600),
    ("1.B - Fugitive emissions from fuels",                              ["CH4"], 1600),
    ("1.B - Fugitive emissions from fuels",                              ["N2O"], 1600),
    ("3.C.4 - Direct N2O Emissions from managed soils",                  ["N2O"],  200),
    ("3.A.1 - Enteric Fermentation",                                     ["CH4"],  200),
    ("3.A.2 - Manure Management",                                        ["CH4"],  200),
    ("2.B - Chemical Industry",                                          ["HFCS"], 200),
    ("2.C - Metal Industry",                                             ["HFCS"], 200),
    ("2.D - Non-Energy Products from Fuels and Solvent Use",             ["CO2"],  600),
    ("4.A - Solid Waste Disposal",                                       ["CH4"],  400),
    ("4.D - Wastewater Treatment and Discharge",                         ["CH4"],  400),
    ("2.F - Product Uses as Substitutes for Ozone Depleting Substances", ["PFCS"], 600),
]


# ---------------------------------------------------------------------------
# Emissions table (data_prep_new_mapping.r)
# ---------------------------------------------------------------------------

def build_emissions_table(
    run_dir: Path,
    targets_path: Path,
    edgar_path: Path,
    iso_code3: str,
    region: str,
    year_ref: int,
    out_path: Path,
    hp_schedule: Iterable[tuple] = HP_SCHEDULE,
) -> pd.DataFrame:
    """Port of data_prep_new_mapping.r."""

    # 1 — load mapping
    mapping = pd.read_csv(targets_path)
    mapping = mapping.drop(columns=[c for c in ("id", "ids", iso_code3) if c in mapping.columns])
    mapping = mapping.reset_index().rename(columns={"index": "_row"})
    mapping["ids"] = (
        mapping["_row"].astype(str)
        + "_" + mapping["subsector_ssp"].astype(str)
        + "_" + mapping["gas"].astype(str)
    )

    # 2 — load EDGAR historical, filter to country
    edgar = pd.read_csv(edgar_path)
    edgar = edgar[edgar["Code"] == iso_code3].copy()
    edgar["ID"] = edgar["subsector"].astype(str) + ":" + edgar["Gas"].astype(str)

    # 3 — load decomposed_ssp_output, filter to region, sort
    data = pd.read_csv(run_dir / "decomposed_ssp_output.csv")
    data = data[data["region"] == region].copy()
    data = data.sort_values(["primary_id", "time_period", "region"]).reset_index(drop=True)

    # 4 — build mapped (rowSum) columns according to mapping$vars (colon-separated)
    id_vars = ["region", "time_period", "primary_id"]
    data_cols = set(data.columns)

    for _, row in mapping.iterrows():
        vars_list = [v.strip() for v in str(row["vars"]).split(":") if v.strip()]
        present = [v for v in vars_list if v in data_cols]
        if len(present) > 1:
            data[row["ids"]] = data[present].sum(axis=1)
        elif len(present) == 1:
            data[row["ids"]] = data[present[0]]
        else:
            data[row["ids"]] = 0.0

    data_new = data[id_vars + mapping["ids"].tolist()].copy()

    # 5 — wide → long
    data_new = data_new.melt(id_vars=id_vars, var_name="ids", value_name="value")

    # 6 — merge with mapping; rename CSC sector/subsector
    map_keep = mapping.drop(columns=["vars"]).rename(
        columns={"sector": "CSC.Sector", "subsector": "CSC.Subsector"}
    )
    data_new = data_new.merge(map_keep, on="ids", how="left")

    # 7 — aggregate to inventory level
    data_new = (
        data_new.groupby(
            ["primary_id", "time_period", "ID", "CSC.Sector", "CSC.Subsector"],
            dropna=False,
            as_index=False,
        )["value"]
        .sum()
        .rename(columns={"CSC.Sector": "sector", "CSC.Subsector": "subsector"})
    )

    data_new["Year"] = data_new["time_period"] + 2015
    data_new["Gas"] = data_new["ID"].astype(str).str.split(":").str[1]

    # 8 — merge with primary + strategy attributes
    att_primary = pd.read_csv(run_dir / "ATTRIBUTE_PRIMARY.csv")
    data_new = data_new.merge(att_primary, on="primary_id", how="left")

    att_strategy = pd.read_csv(run_dir / "ATTRIBUTE_STRATEGY.csv")[["strategy_id", "strategy"]]
    data_new = data_new.merge(att_strategy, on="strategy_id", how="left")

    # 9 — melt EDGAR wide to long
    id_vars_edgar = ["Code", "sector", "subsector", "Gas", "ID"]
    measure_cols = [c for c in edgar.columns if re.fullmatch(r"X?\d{4}", str(c))]
    edgar_long = edgar.melt(
        id_vars=id_vars_edgar,
        value_vars=measure_cols,
        var_name="variable",
        value_name="value",
    )
    edgar_long["Year"] = edgar_long["variable"].astype(str).str.lstrip("X").astype(int)
    edgar_long = edgar_long.drop(columns=["variable"])
    edgar_long["strategy_id"] = np.nan
    edgar_long["primary_id"]  = np.nan
    edgar_long["design_id"]   = np.nan
    edgar_long["future_id"]   = np.nan
    edgar_long["Contry"]      = region
    edgar_long["strategy"]    = "Historical"
    edgar_long["source"]      = "EDGAR"

    # 10 — prepare data_new for rbind
    data_new = data_new.drop(columns=["time_period"])
    data_new["Code"]   = iso_code3
    data_new["Contry"] = region
    data_new["source"] = "SISEPUEDE"
    edgar_max_year = int(edgar_long["Year"].max())
    data_new = data_new[data_new["Year"] >= edgar_max_year].copy()

    combined = pd.concat([data_new, edgar_long], ignore_index=True, sort=False)
    combined = combined.sort_values(
        ["strategy_id", "sector", "subsector", "Gas", "Year"], na_position="last"
    ).reset_index(drop=True)

    # 11 — HP filter (note: _apply_hp_to_subsec_gas re-snapshots value_original on
    #       every call, matching the R hp_filter_subsec side-effect)
    combined["value_hp"] = np.nan
    for subsec, gases, lam in hp_schedule:
        combined = _apply_hp_to_subsec_gas(combined, subsec, gases, lam)

    # 12 — write CSV with the column order expected by Tableau
    final_cols = [
        "strategy_id", "primary_id", "ID", "sector", "subsector", "value",
        "Year", "Gas", "design_id", "future_id", "strategy", "Code",
        "Contry", "source", "value_original", "value_hp",
    ]
    final_cols = [c for c in final_cols if c in combined.columns]
    out = combined[final_cols].copy()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"[emissions] {out_path}  ({len(out):,} rows)")
    return out


# ---------------------------------------------------------------------------
# Drivers table (data_prep_drivers.r)
# ---------------------------------------------------------------------------

def build_drivers_table(
    run_dir: Path,
    drivers_taxonomy_path: Path,
    wide_inputs_outputs_path: Path,
    iso_code3: str,
    region: str,
    year_ref: int,
    out_path: Path,
) -> pd.DataFrame:
    """Port of data_prep_drivers.r."""

    data = pd.read_csv(run_dir / "decomposed_ssp_output.csv")
    id_vars = ["region", "time_period", "primary_id"]
    measure_cols = [c for c in data.columns if c not in id_vars]
    long_df = data.melt(id_vars=id_vars, value_vars=measure_cols,
                        var_name="variable", value_name="value")

    drivers = pd.read_csv(drivers_taxonomy_path).rename(columns={"field": "variable"})

    long_df = long_df[long_df["variable"].isin(drivers["variable"].unique())].copy()
    long_df = long_df.merge(drivers, on="variable", how="left")

    long_df["Year"] = long_df["time_period"] + 2015
    long_df = long_df.drop(columns=["time_period"])
    long_df = long_df[long_df["Year"] >= year_ref].copy()

    att_primary = pd.read_csv(run_dir / "ATTRIBUTE_PRIMARY.csv")
    long_df = long_df.merge(att_primary, on="primary_id", how="left")

    att_strategy = pd.read_csv(run_dir / "ATTRIBUTE_STRATEGY.csv")[["strategy_id", "strategy"]]
    long_df = long_df.merge(att_strategy, on="strategy_id", how="left")

    long_df["Units"]           = "NA"
    long_df["Data_Type"]       = "sisepuede simulation"
    long_df["iso_code3"]       = iso_code3
    long_df["Country"]         = region
    long_df["output_type"]     = "drivers"
    long_df["gas"]             = np.nan
    long_df = long_df.drop(columns=[c for c in ("region", "subsector_total_field",
                                                "model_variable_information") if c in long_df.columns])

    # energy_subsector classification
    energy_keywords = {
        "ccsq": "Carbon Capture and Sequestration",
        "inen": "Industrial Energy",
        "entc": "Power(electricity/heat)",
        "trns": "Transportation",
        "scoe": "Buildings",
    }
    long_df["energy_subsector"] = pd.Series(pd.NA, index=long_df.index, dtype=object)
    energy_mask = long_df["variable"].str.contains("energy", regex=False, na=False)
    es = pd.Series("TBD", index=long_df.index, dtype=object)
    for kw, label in energy_keywords.items():
        es = es.where(~long_df["variable"].str.contains(kw, regex=False, na=False), label)
    long_df.loc[energy_mask, "energy_subsector"] = es[energy_mask]

    # GDP history
    gdp = pd.read_csv(wide_inputs_outputs_path, usecols=["primary_id", "time_period", "gdp_mmm_usd"])
    gdp = gdp[gdp["primary_id"] == 0].copy()
    gdp["year"] = gdp["time_period"] + 2015
    gdp = gdp[gdp["year"] <= year_ref][["year", "gdp_mmm_usd"]]

    strategies_df = (
        long_df[["strategy_id", "design_id", "future_id", "strategy"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # cross join (all strategies × all GDP history years)
    gdp = gdp.assign(_k=1).rename(columns={"year": "Year", "gdp_mmm_usd": "value"})
    strategies_df = strategies_df.assign(_k=1)
    drivers_hist = strategies_df.merge(gdp, on="_k").drop(columns="_k")
    drivers_hist["variable"]         = "gdp_mmm_usd"
    drivers_hist["primary_id"]       = 0
    drivers_hist["sector"]           = "Socioeconomic"
    drivers_hist["subsector"]        = "Economy"
    drivers_hist["model_variable"]   = "GDP"
    drivers_hist["category_value"]   = "('', '')"
    drivers_hist["category_name"]    = "cat_economy"
    drivers_hist["gas"]              = np.nan
    drivers_hist["gas_name"]         = ""
    drivers_hist["Units"]            = "NA"
    drivers_hist["Data_Type"]        = "historical"
    drivers_hist["iso_code3"]        = iso_code3
    drivers_hist["Country"]          = region
    drivers_hist["output_type"]      = "drivers"
    drivers_hist["energy_subsector"] = np.nan

    years_in_sim = long_df.loc[long_df["variable"] == "gdp_mmm_usd", "Year"].dropna().unique()
    if len(years_in_sim):
        last_year_in_sim = int(min(years_in_sim))
        drivers_hist = drivers_hist[drivers_hist["Year"] < last_year_in_sim].copy()

    out_cols = [
        "variable", "strategy_id", "primary_id", "value", "sector", "subsector",
        "model_variable", "category_value", "category_name", "gas", "gas_name",
        "Year", "design_id", "future_id", "strategy", "Units", "Data_Type",
        "iso_code3", "Country", "output_type", "energy_subsector",
    ]
    for c in out_cols:
        if c not in long_df.columns:
            long_df[c] = np.nan
        if c not in drivers_hist.columns:
            drivers_hist[c] = np.nan

    final = pd.concat([long_df[out_cols], drivers_hist[out_cols]], ignore_index=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_path, index=False)
    print(f"[drivers]   {out_path}  ({len(final):,} rows)")
    return final


# ---------------------------------------------------------------------------
# FGTV volumes table (oil/gas production + flaring/venting/fugitive volumes)
# ---------------------------------------------------------------------------

# IPCC AR6 100-year GWP for CH4 (matches sisepuede/attributes/attribute_gas.csv).
# Needed to convert emission_co2e_ch4_* (Mt CO2eq) into raw CH4 mass before
# converting to gas volume.
GWP_CH4_AR6_100Y = 27.9

# Standard-condition densities (15 degC, 1 atm) for converting emission mass
# to fuel volume. These mirror the World Bank GGFR / IEA convention used to
# report flaring/venting volumes.
#
# Flaring: associated gas at Libyan oil wells is heavier than pure NG (it
# carries C2-C5 hydrocarbons in addition to CH4). The Libya CCD report
# (March 2026) states 6.3 Bcm flared in 2024 produced ~16 Mt CO2 — implying
# 2.54 kg CO2 / m^3 of flared gas. We use this composition-weighted factor
# so the post-processed flaring Bcm matches the report's stated volumes.
#
# Venting / fugitive: the escaping stream is CH4-dominated, so we treat
# vented/leaked gas as 95% CH4 by volume (1 m^3 pure CH4 = 0.717 kg).
KG_CO2_PER_M3_FLARED_GAS = 2.54
KG_CH4_PER_M3_PURE       = 0.717
NG_CH4_VOLUME_FRACTION   = 0.95

# Fuels in the FGTV pathway that we report volumes for. "crude" and "oil"
# both flag oil-side fugitive streams in the SISEPUEDE schema; we report
# both so downstream users can pick the relevant one for their dashboard.
FGTV_FUELS = ("natural_gas", "crude", "oil")

# Pathway -> (emission process tag in SISEPUEDE column names, gas to use for
# the volume back-conversion). Flaring is dominated by CO2 (combustion of
# associated gas to CO2 is the dominant signal), while venting and fugitive
# leaks are CH4-dominated since the gas escapes uncombusted.
FGTV_PATHWAYS = {
    "flaring":  ("flaring", "co2"),
    "venting":  ("venting", "ch4"),
    "fugitive": ("dtp",     "ch4"),
}

# Postprocessing-side calibration scalars that bring the back-derived volumes
# to the absolute level reported in the World Bank Libya Climate Diagnostic
# (Oil & Gas Sector, March 2026). The SISEPUEDE input EFs are conservative
# relative to the empirical 2024 values in that report; rather than rewrite
# the model inputs, we apply a flat multiplier per (fuel, pathway) here so
# the Bcm series we ship to Tableau matches the report's stated levels in
# 2024.
#
# The report's quoted figures are for oil-side operations (associated gas
# from crude production), so calibration is applied only to fuel='crude' —
# the dominant upstream oil stream in SISEPUEDE. Other fuels (natural_gas,
# oil) keep their native physical-density derivation (factor 1.0).
#
# Calibration anchor (2024 BAU crude-only model -> report target):
#   (crude, flaring):  2.234 Bcm -> 6.30 Bcm  (x2.820); 5.67 Mt CO2 -> 16 Mt
#   (crude, venting):  0.753 Bcm -> 0.98 Bcm  (x1.303); 14.31 -> 18.65 Mt CO2e CH4
#   (crude, fugitive): 0.185 Bcm -> 0.33 Bcm  (x1.802);  3.52 ->  6.34 Mt CO2e CH4
#
# Trends and scenario contrasts (BAU vs ZRF, year-on-year change) are
# unaffected by these constants - they shift absolute levels only.
PATHWAY_CALIBRATION_FACTORS: dict[tuple[str, str], float] = {
    ("crude", "flaring"):  2.820,
    ("crude", "venting"):  1.303,
    ("crude", "fugitive"): 1.802,
}


def _gas_volume_from_co2_emissions_m3(emission_co2eq_mt: pd.Series) -> pd.Series:
    """Convert tonnes-CO2eq of CO2 (= tonnes CO2, since GWP_CO2 = 1) emitted
    from flaring into volume of associated gas combusted, in m^3 at standard
    conditions. emission_co2eq_mt is in Mt; output is m^3."""
    emission_kg = emission_co2eq_mt * 1e9
    return emission_kg / KG_CO2_PER_M3_FLARED_GAS


def _gas_volume_from_ch4_emissions_m3(emission_co2eq_mt: pd.Series) -> pd.Series:
    """Convert tonnes-CO2eq of CH4 emitted (vented or leaked) into volume of
    natural gas escaped, in m^3 at standard conditions. The CO2eq is divided
    by GWP_CH4 to recover CH4 mass, by CH4 density to get pure-CH4 volume,
    then divided by the natural-gas CH4 volume fraction so the answer is
    expressed as 'natural gas equivalent' rather than pure CH4."""
    emission_kg = emission_co2eq_mt * 1e9
    mass_ch4_kg = emission_kg / GWP_CH4_AR6_100Y
    volume_pure_ch4_m3 = mass_ch4_kg / KG_CH4_PER_M3_PURE
    return volume_pure_ch4_m3 / NG_CH4_VOLUME_FRACTION


def build_fgtv_volumes_table(
    run_dir: Path,
    iso_code3: str,
    region: str,
    out_path: Path,
) -> pd.DataFrame:
    """Produce a long-format CSV of oil/gas production volumes and the
    flaring/venting/fugitive plus gas_recovery natural-gas-equivalent
    volumes implied by the SISEPUEDE FGTV emissions outputs.

    Methodology (World Bank GGFR / IEA convention)
    ----------------------------------------------
    SISEPUEDE does not export pathway volumes natively. We derive them from
    the model's CO2eq emissions outputs using standard-condition densities:

      * Production volume (m^3) = prod_enfu_fuel_X_pj * 1e6 / density_MJ_per_L
        where density is ``energydensity_enfu_mj_per_litre_fuel_X``.

      * Flaring volume (m^3 of associated gas combusted)
            = (emission_co2e_co2_fgtv_flaring_fuel_X * 1e9 kg/Mt) / 2.54 kg/m^3
        (full combustion of associated gas with composition-weighted CO2
         yield matching the Libya CCD March 2026 report).

      * Venting and fugitive (DTP) volume (m^3 of natural gas escaped)
            = (emission_co2e_ch4_fgtv_PROCESS_fuel_X * 1e9 / GWP_CH4)
              / 0.717 kg/m^3 / 0.95
        (CO2eq -> CH4 mass via GWP, mass -> pure-CH4 volume via density,
         then expressed as natural-gas equivalent at 95% CH4).

    Each pathway volume is then multiplied by the per-(fuel, pathway)
    scalar in PATHWAY_CALIBRATION_FACTORS to align the absolute level with
    the World Bank Libya CCD (March 2026) figures. The report's flaring
    chart (607 MMcfd in 2024) is for oil-associated gas only, so only
    fuel='crude' rows are calibrated; natural_gas and oil keep their
    native physical-density derivation.

      * gas_recovery volume (m^3, simple counterfactual diff)
            = BAU_(flaring+venting+fugitive)(Year, fuel)
              - scenario_(flaring+venting+fugitive)(Year, fuel)
        i.e. the gas the scenario stops emitting through the three FGTV
        streams relative to its BAU twin in the same run. Zero for BAU
        rows by construction. Sign is preserved so the metric is auditable.

    Pathway volumes are reported in cubic metres (m^3) and Bcm (1 Bcm = 1e9 m^3).
    """
    data = pd.read_csv(run_dir / "decomposed_ssp_output.csv")
    data = data[data["region"] == region].copy()
    data = data.sort_values(["primary_id", "time_period"]).reset_index(drop=True)

    id_cols = ["primary_id", "time_period"]
    per_fuel_frames: list[pd.DataFrame] = []

    for fuel in FGTV_FUELS:
        frame = data[id_cols].copy()
        frame["fuel"] = fuel

        # Production volume (m^3): PJ * 1e6 / (MJ/L)
        prod_col = f"prod_enfu_fuel_{fuel}_pj"
        dens_col = f"energydensity_enfu_mj_per_litre_fuel_{fuel}"
        if prod_col in data.columns and dens_col in data.columns:
            density = data[dens_col].replace(0, np.nan)
            frame["production_m3"] = (data[prod_col] * 1e6 / density).fillna(0.0)
        else:
            frame["production_m3"] = 0.0

        # Three FGTV components. Calibration applies only to the (fuel,
        # pathway) tuples explicitly listed in PATHWAY_CALIBRATION_FACTORS;
        # everything else passes through at its native physical value.
        for pathway_label, (process_tag, gas_kind) in FGTV_PATHWAYS.items():
            em_col = f"emission_co2e_{gas_kind}_fgtv_{process_tag}_fuel_{fuel}"
            cal = PATHWAY_CALIBRATION_FACTORS.get((fuel, pathway_label), 1.0)
            if em_col not in data.columns:
                frame[f"{pathway_label}_m3"] = 0.0
                continue
            if gas_kind == "co2":
                vol = _gas_volume_from_co2_emissions_m3(data[em_col])
            else:
                vol = _gas_volume_from_ch4_emissions_m3(data[em_col])
            frame[f"{pathway_label}_m3"] = vol.fillna(0.0) * cal

        per_fuel_frames.append(frame)

    if not per_fuel_frames:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            columns=["Year", "primary_id", "strategy_id", "design_id",
                     "future_id", "strategy", "iso_code3", "Country",
                     "fuel", "pathway", "value_m3", "value_bcm"]
        ).to_csv(out_path, index=False)
        print(f"[fgtv_vol]  {out_path}  (no FGTV columns found)")
        return pd.DataFrame()

    # Compute gas_recovery in wide form first, then melt.
    wide = pd.concat(per_fuel_frames, ignore_index=True)
    wide["Year"] = wide["time_period"] + 2015

    att_primary  = pd.read_csv(run_dir / "ATTRIBUTE_PRIMARY.csv")
    wide         = wide.merge(att_primary, on="primary_id", how="left")
    att_strategy = pd.read_csv(run_dir / "ATTRIBUTE_STRATEGY.csv")[["strategy_id", "strategy"]]
    wide         = wide.merge(att_strategy, on="strategy_id", how="left")

    # gas_recovery = BAU(flaring+venting+fugitive) - scenario(flaring+venting+fugitive)
    fgtv_components = ("flaring", "venting", "fugitive")
    wide["_fgtv_total_m3"] = sum(wide[f"{c}_m3"] for c in fgtv_components)

    bau_total = (
        wide[wide["strategy"] == "BAU"]
        .groupby(["Year", "fuel"], as_index=False)["_fgtv_total_m3"]
        .first()
        .rename(columns={"_fgtv_total_m3": "_bau_fgtv_total_m3"})
    )
    if not bau_total.empty:
        wide = wide.merge(bau_total, on=["Year", "fuel"], how="left")
        wide["_bau_fgtv_total_m3"] = wide["_bau_fgtv_total_m3"].fillna(0.0)
        wide["gas_recovery_m3"] = wide["_bau_fgtv_total_m3"] - wide["_fgtv_total_m3"]
    else:
        wide["gas_recovery_m3"] = 0.0

    wide = wide.drop(columns=[c for c in ("_fgtv_total_m3","_bau_fgtv_total_m3") if c in wide.columns])

    wide["iso_code3"] = iso_code3
    wide["Country"]   = region

    # Melt to long format: one row per (Year, primary_id, fuel, pathway)
    pathway_cols = ["production_m3", "flaring_m3", "venting_m3",
                    "fugitive_m3", "gas_recovery_m3"]
    id_vars = ["Year", "primary_id", "strategy_id", "design_id", "future_id",
               "strategy", "iso_code3", "Country", "fuel"]
    id_vars = [c for c in id_vars if c in wide.columns]
    long_df = wide.melt(
        id_vars   = id_vars,
        value_vars = pathway_cols,
        var_name  = "pathway",
        value_name = "value_m3",
    )
    long_df["pathway"]   = long_df["pathway"].str.removesuffix("_m3")
    long_df["value_bcm"] = long_df["value_m3"] / 1e9

    out_cols = id_vars + ["pathway", "value_m3", "value_bcm"]
    final = long_df[out_cols].sort_values(
        ["strategy_id", "fuel", "pathway", "Year"]
    ).reset_index(drop=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_path, index=False)
    print(f"[fgtv_vol]  {out_path}  ({len(final):,} rows)")
    return final


# ---------------------------------------------------------------------------
# Levers table (#create levers table.r)
# ---------------------------------------------------------------------------

# R make.names() converts spaces and parentheses to dots.
_R_MAKE_NAMES_RENAME = {
    "Sector (output)":            "Sector..output.",
    "Subsector (output)":         "Subsector..output.",
    "Example government policies": "Example.government.policies",
}


def build_levers_table(
    run_dir: Path,
    descriptions_path: Path,
    stakeholder_codes_path: Path,
    out_path: Path,
) -> pd.DataFrame:
    """Port of #create levers table.r — merges levers_implementation_libya.csv
    (already produced by the manager notebook) with descriptions and stakeholder codes."""

    ssp_table = pd.read_csv(run_dir / "levers_implementation_libya.csv")
    ssp_table["transformation_code"] = ssp_table["transformer_code"].str.replace("TFR:", "", regex=False)

    desp = pd.read_csv(descriptions_path)
    scodes = pd.read_csv(stakeholder_codes_path).rename(columns=_R_MAKE_NAMES_RENAME)
    scodes["transformation_code"] = scodes["transformation_code"].str.replace("TX:", "", regex=False)

    merged = ssp_table.merge(desp, on="transformation_code", how="inner")
    merged = merged.merge(
        scodes[["transformation_code", "transformation_name_stakeholder",
                "Sector..output.", "Subsector..output.", "Example.government.policies"]],
        on="transformation_code",
        how="inner",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    print(f"[levers]    {out_path}  ({len(merged):,} rows)")
    return merged


# ---------------------------------------------------------------------------
# Jobs table (#create jobs table.r)
# ---------------------------------------------------------------------------

def build_jobs_table(
    employment_path: Path,
    iso_code3: str,
    out_path: Path,
) -> pd.DataFrame:
    """Port of #create jobs table.r — splits the ":"-encoded Strategy column."""

    jobs = pd.read_csv(employment_path)
    parts = jobs["Strategy"].astype(str).str.split(":", n=1, expand=True)
    jobs["ssp_sector"]                 = parts[0]
    jobs["ssp_transformation_name"]    = parts[1] if parts.shape[1] > 1 else ""
    jobs = jobs[jobs["Country"] == iso_code3].copy()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    jobs.to_csv(out_path, index=False)
    print(f"[jobs]      {out_path}  ({len(jobs):,} rows)")
    return jobs


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_tableau_postprocessing(
    run_dir: str | Path,
    project_dir: str | Path,
    region: str,
    iso_code3: str,
    year_ref: int,
    wide_inputs_outputs_filename: str | None = None,
    out_dir: str | Path | None = None,
) -> dict:
    """Generate every Tableau-ready CSV in one call.

    Parameters
    ----------
    run_dir : run output directory (must contain decomposed_ssp_output.csv,
        ATTRIBUTE_PRIMARY.csv, ATTRIBUTE_STRATEGY.csv, levers_implementation_libya.csv,
        and the WIDE_INPUTS_OUTPUTS.csv).
    project_dir : repo root (used to locate post-processing data files).
    region : region label inside the model output, e.g. "libya".
    iso_code3 : ISO 3-letter country code, e.g. "LBY".
    year_ref : reference / calibration year.
    wide_inputs_outputs_filename : explicit filename of the WIDE_INPUTS_OUTPUTS file
        inside run_dir; if None, auto-detected as the single matching pattern.
    out_dir : where to write the Tableau CSVs (defaults to
        <project_dir>/ssp_modeling/tableau/data).
    """
    run_dir = Path(run_dir)
    project_dir = Path(project_dir)
    out_dir = Path(out_dir) if out_dir else project_dir / "ssp_modeling" / "tableau" / "data"

    # Locate the wide inputs/outputs file
    if wide_inputs_outputs_filename is None:
        candidates = sorted(run_dir.glob("*WIDE_INPUTS_OUTPUTS.csv"))
        if not candidates:
            raise FileNotFoundError(f"No *WIDE_INPUTS_OUTPUTS.csv found in {run_dir}")
        wide_path = candidates[-1]
    else:
        wide_path = run_dir / wide_inputs_outputs_filename

    pp_data = project_dir / "ssp_modeling" / "output_postprocessing" / "data"

    targets_path           = pp_data / "invent" / f"emission_targets_{iso_code3.lower()}_{year_ref}.csv"
    edgar_path             = pp_data / "invent" / f"invent_historic_{iso_code3.lower()}.csv"
    drivers_taxonomy_path  = pp_data / "driver_variables_taxonomy_20251013.csv"
    descriptions_path      = pp_data / "levers" / "ssp_descriptions.csv"
    stakeholder_codes_path = pp_data / "levers" / "stakeholder_codes.csv"
    employment_path        = pp_data / "levers" / "Sisepuede - Employment Results - WB (SECTOR).csv"

    emissions = build_emissions_table(
        run_dir       = run_dir,
        targets_path  = targets_path,
        edgar_path    = edgar_path,
        iso_code3     = iso_code3,
        region        = region,
        year_ref      = year_ref,
        out_path      = out_dir / f"decomposed_emissions_{region}_{year_ref}.csv",
    )
    drivers = build_drivers_table(
        run_dir                 = run_dir,
        drivers_taxonomy_path   = drivers_taxonomy_path,
        wide_inputs_outputs_path = wide_path,
        iso_code3               = iso_code3,
        region                  = region,
        year_ref                = year_ref,
        out_path                = out_dir / f"drivers_{region}.csv",
    )
    fgtv_volumes = build_fgtv_volumes_table(
        run_dir   = run_dir,
        iso_code3 = iso_code3,
        region    = region,
        out_path  = out_dir / f"fgtv_volumes_{region}.csv",
    )
    levers = build_levers_table(
        run_dir                = run_dir,
        descriptions_path      = descriptions_path,
        stakeholder_codes_path = stakeholder_codes_path,
        out_path               = out_dir / "tableau_levers_table_complete.csv",
    )
    jobs = build_jobs_table(
        employment_path = employment_path,
        iso_code3       = iso_code3,
        out_path        = out_dir / f"jobs_demand_{region}.csv",
    )

    return {
        "emissions":    emissions,
        "drivers":      drivers,
        "fgtv_volumes": fgtv_volumes,
        "levers":       levers,
        "jobs":         jobs,
    }
