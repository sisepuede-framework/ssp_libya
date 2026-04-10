"""
mac_pipeline.py
---------------
Marginal Abatement Cost (MAC) computation for the whirlpool experiment.

Inputs : df_decomposed, cb_data, att_primary, att_strategy, inventory files.
Outputs: mac_df DataFrame (USD / tCO2e) + marginal_abatement_costs_whirlpool.csv.
"""

import numpy as np
import pandas as pd
from pathlib import Path


def run_mac_analysis(
    df_decomposed: pd.DataFrame,
    cb_data: pd.DataFrame,
    att_primary: pd.DataFrame,
    att_strategy: pd.DataFrame,
    iso_code3: str,
    region: str,
    invent_dir: Path,
    run_output_dir: Path,
    targets_path: Path,
    strategy_code_pflo_hble: str = "PFLO:HBLE",
    output_filename: str = "marginal_abatement_costs_whirlpool.csv",
) -> pd.DataFrame:
    """
    Compute MAC curves and export CSV.

    Steps
    -----
    1. Load inventory mapping and EDGAR historical data.
    2. Map SSP variables to inventory categories; aggregate to data_inv.
    3. Compute cumulative emissions by strategy vs. PFLO:HBLE baseline.
    4. Compute cumulative technical costs by strategy.
    5. Merge, normalise to baseline, and calculate MAC (USD/tCO2e).
    6. Export to CSV.

    Returns
    -------
    mac_df : pd.DataFrame
    """

    # ── 1. Inventory mapping ──────────────────────────────────────────────────
    mapping = pd.read_csv(targets_path)
    mapping = (
        mapping
        .drop(columns=[iso_code3, "est_from_sisepuede"], errors="ignore")
        .reset_index(drop=False)
        .rename(columns={"index": "row_idx"})
    )
    mapping["ids"] = (
        mapping["row_idx"].astype(str) + ":" +
        mapping["subsector_ssp"].astype(str) + ":" +
        mapping["gas"].astype(str)
    )

    # ── 2. EDGAR historical ───────────────────────────────────────────────────
    edgar = pd.read_csv(invent_dir / "invent_historic_lby.csv")
    edgar = edgar[edgar["Code"] == iso_code3].copy()

    year_cols   = [c for c in edgar.columns if str(c).isdigit()]
    edgar_long  = edgar.melt(
        id_vars=["Code", "sector", "subsector", "Gas", "ID"],
        value_vars=year_cols, var_name="year_str", value_name="value",
    )
    edgar_long["Year"] = edgar_long["year_str"].astype(int)
    edgar_long = edgar_long.drop(columns=["year_str"])
    for col in ["strategy_id", "primary_id", "design_id", "future_id"]:
        edgar_long[col] = float("nan")
    edgar_long["strategy"] = "Historical"
    edgar_long["source"]   = "EDGAR"
    edgar_long["Contry"]   = region
    edgar_max_year = int(edgar_long["Year"].max())

    # ── 3. Map SSP vars → inventory categories ────────────────────────────────
    id_vars = ["region", "time_period", "primary_id"]
    data    = df_decomposed[df_decomposed["region"] == region].copy()

    rows_agg = []
    for _, row in mapping.iterrows():
        tvars = [v.strip() for v in str(row["vars"]).split(":") if v.strip() in data.columns]
        if len(tvars) > 1:
            agg_col = data[tvars].sum(axis=1)
        elif len(tvars) == 1:
            agg_col = data[tvars[0]]
        else:
            agg_col = pd.Series(0.0, index=data.index)
        tmp          = data[id_vars].copy()
        tmp["ids"]   = row["ids"]
        tmp["value"] = agg_col.values
        rows_agg.append(tmp)

    data_long = pd.concat(rows_agg, ignore_index=True)
    meta      = mapping[["ids", "sector", "subsector", "gas", "ID"]].copy()
    data_long = data_long.merge(meta, on="ids", how="left")

    data_inv = (
        data_long
        .groupby(["primary_id", "time_period", "ID", "sector", "subsector"], dropna=False)["value"]
        .sum()
        .reset_index()
    )
    data_inv["Year"]   = data_inv["time_period"] + 2015
    data_inv["Gas"]    = data_inv["ID"].str.split(":").str[-1]
    data_inv["Code"]   = iso_code3
    data_inv["Contry"] = region
    data_inv["source"] = "SISEPUEDE"

    data_inv = data_inv.merge(
        att_primary[["primary_id", "strategy_id", "design_id", "future_id"]],
        on="primary_id", how="left",
    )
    data_inv = data_inv.merge(
        att_strategy[["strategy_id", "strategy"]], on="strategy_id", how="left"
    )
    data_inv = data_inv[data_inv["Year"] >= edgar_max_year].copy()

    shared = [
        "primary_id", "strategy_id", "design_id", "future_id",
        "sector", "subsector", "Gas", "ID", "Year", "value",
        "Code", "Contry", "strategy", "source",
    ]
    emissions = pd.concat(
        [
            data_inv[[c for c in shared if c in data_inv.columns]],
            edgar_long[[c for c in shared if c in edgar_long.columns]],
        ],
        ignore_index=True,
    )
    emissions = (
        emissions
        .sort_values(["strategy_id", "sector", "subsector", "Gas", "Year"])
        .reset_index(drop=True)
    )

    # ── 4. Cumulative emissions by strategy ───────────────────────────────────
    em_ssp = emissions[emissions["source"] == "SISEPUEDE"].copy()
    cumul  = (
        em_ssp
        .groupby(["strategy_id", "primary_id"], dropna=False)["value"]
        .sum()
        .reset_index()
        .rename(columns={"value": "emission_total"})
        .sort_values("strategy_id")
    )

    base_sid = att_strategy.loc[
        att_strategy["strategy_code"] == strategy_code_pflo_hble, "strategy_id"
    ].iloc[0]
    base_emission_val = cumul.loc[cumul["strategy_id"] == base_sid, "emission_total"].values[0]

    cumul["base_emission_total"] = base_emission_val
    cumul["emission_diff"]       = cumul["emission_total"] - base_emission_val

    # ── 5. Cumulative technical costs ─────────────────────────────────────────
    tc = (
        cb_data[cb_data["cb_type"] == "technical_cost"]
        .groupby(["strategy_id", "primary_id"], dropna=False)["value"]
        .sum()
        .reset_index()
        .rename(columns={"value": "technical_cost"})
        .sort_values("strategy_id")
    )
    tc["technical_cost"] = tc["technical_cost"] * -1

    # ── 6. Merge, normalise, compute MAC ─────────────────────────────────────
    mac_df = cumul.merge(tc, on=["strategy_id", "primary_id"], how="left")
    mac_df = mac_df.merge(
        att_strategy[["strategy_id", "sector", "transformation_code"]],
        on="strategy_id", how="left",
    )

    base_tc_val              = mac_df.loc[mac_df["strategy_id"] == base_sid, "technical_cost"].values[0]
    mac_df["technical_cost"] = mac_df["technical_cost"] - base_tc_val

    # Exclude strategy_id == 0 placeholder
    mac_df = mac_df[mac_df["strategy_id"] != 0]

    # MAC = B USD / MtCO2e → USD / tCO2e
    # Compute on unrounded values to avoid division-by-zero from rounding
    raw_mac = (
        (mac_df["technical_cost"] * -1e9)   # B USD → USD
        / (mac_df["emission_diff"] * 1e6)   # MtCO2e → tCO2e
    )
    mac_df["marginal_abatement_cost"] = raw_mac

    # Round display columns after MAC is computed
    mac_df["emission_diff"]  = mac_df["emission_diff"].round(4)
    mac_df["technical_cost"] = mac_df["technical_cost"].round(4)

    # Replace inf with NaN (no rows dropped)
    mac_df["marginal_abatement_cost"] = mac_df["marginal_abatement_cost"].replace(
        [float("inf"), float("-inf")], float("nan")
    )

    # Reorder columns
    first_cols = ["strategy_id", "primary_id", "sector", "transformation_code"]
    rest_cols  = [c for c in mac_df.columns if c not in first_cols]
    mac_df = mac_df[first_cols + rest_cols]

    # ── 7. Export ─────────────────────────────────────────────────────────────
    run_output_dir.mkdir(parents=True, exist_ok=True)
    mac_df.to_csv(
        run_output_dir / output_filename,
        index=False, encoding="UTF-8",
    )

    return mac_df


def build_attribute_map(
    att_primary: pd.DataFrame,
    att_strategy: pd.DataFrame,
    run_output_dir: Path,
    tornado_att_map_path: Path,
) -> pd.DataFrame:
    """
    Build ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv for the whirlpool run.

    Steps
    -----
    1. Extract (primary_id_whirlpool, transformation_code, sector) from
       the whirlpool attribute tables — one row per singleton strategy.
    2. Merge with the tornado's ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv on
       (transformation_code, sector) to pull in all tornado metadata
       (primary_id_tornado, strategy_id, strategy_code, strategy,
        transformation_name, transformation_name_sector).
    3. Write and return the combined table.

    The dual key (transformation_code + sector) is required because the
    same transformation_code can appear in more than one sector.

    Parameters
    ----------
    att_primary          : ATTRIBUTE_PRIMARY.csv loaded as DataFrame
    att_strategy         : ATTRIBUTE_STRATEGY.csv loaded and enriched by
                           parse_strategy_metadata()
    run_output_dir       : directory where the CSV will be written
    tornado_att_map_path : full path to the tornado run's
                           ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv
    """
    # ── 1. Whirlpool side: only id columns ────────────────────────────────────
    whirlpool_cols = [c for c in ["strategy_id", "transformation_code", "sector"]
                      if c in att_strategy.columns]

    whirlpool_map = (
        att_primary[["primary_id", "strategy_id"]]
        .merge(att_strategy[whirlpool_cols], on="strategy_id", how="left")
        .rename(columns={"primary_id": "primary_id_whirlpool"})
        .query("strategy_id != 0")
        [["primary_id_whirlpool", "transformation_code", "sector"]]
        .sort_values("primary_id_whirlpool")
        .reset_index(drop=True)
    )

    # ── 2. Merge with tornado map to get full metadata ────────────────────────
    tornado_map = pd.read_csv(tornado_att_map_path)

    att_map = whirlpool_map.merge(
        tornado_map,
        on=["transformation_code", "sector"],
        how="left",
    )

    # ── 3. Export ─────────────────────────────────────────────────────────────
    run_output_dir.mkdir(parents=True, exist_ok=True)
    att_map.to_csv(
        run_output_dir / "ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv",
        index=False, encoding="UTF-8",
    )
    return att_map


def build_tableau_whirlpool(
    mac_df: pd.DataFrame,
    run_output_dir: Path,
    tableau_dir: Path,
    tornado_mac_path: Path,
    output_path: Path = None,
) -> pd.DataFrame:
    """
    Build and export the Tableau whirlpool plot data.

    Joins ATTRIBUTE_MAP_TORNADO_WHIRLPOOL with:
      - whirlpool MAC results (suffixed _whirlpool)
      - tornado MAC results   (suffixed _tornado)
    on (transformation_code, sector) so each row has both sets of values
    for direct comparison in Tableau.
    """
    att_map = pd.read_csv(run_output_dir / "ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv")

    mac_cols = [
        "primary_id", "transformation_code", "sector",
        "emission_total", "base_emission_total",
        "emission_diff", "technical_cost", "marginal_abatement_cost",
    ]

    # ── Whirlpool MAC ─────────────────────────────────────────────────────────
    whirlpool = mac_df[[c for c in mac_cols if c in mac_df.columns]].rename(columns={
        "primary_id":            "primary_id_whirlpool",
        "emission_total":        "emission_total_whirlpool",
        "base_emission_total":   "base_emission_total_whirlpool",
        "emission_diff":         "emission_diff_whirlpool",
        "technical_cost":        "technical_cost_whirlpool",
        "marginal_abatement_cost": "marginal_abatement_cost_whirlpool",
    })

    tableau = att_map.merge(
        whirlpool,
        on=["primary_id_whirlpool", "transformation_code", "sector"],
        how="left",
    )

    # ── Tornado MAC ───────────────────────────────────────────────────────────
    tornado_mac = pd.read_csv(tornado_mac_path)
    tornado_cols = [
        "primary_id", "transformation_code", "sector",
        "emission_total", "base_emission_total",
        "emission_diff", "technical_cost", "marginal_abatement_cost",
    ]
    tornado = tornado_mac[[c for c in tornado_cols if c in tornado_mac.columns]].rename(columns={
        "primary_id":            "primary_id_tornado",
        "emission_total":        "emission_total_tornado",
        "base_emission_total":   "base_emission_total_tornado",
        "emission_diff":         "emission_diff_tornado",
        "technical_cost":        "technical_cost_tornado",
        "marginal_abatement_cost": "marginal_abatement_cost_tornado",
    })

    tableau = tableau.merge(
        tornado,
        on=["primary_id_tornado", "transformation_code", "sector"],
        how="left",
    )

    tableau = tableau[tableau["emission_diff_whirlpool"].notna()].reset_index(drop=True)

    tableau_dir.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path is not None else tableau_dir / "tableau_whirlpool.csv"
    tableau.to_csv(out, index=False, encoding="UTF-8")

    return tableau


def build_mac_tornado_to_whirlpool(
    whirlpool_mac_df: pd.DataFrame,
    run_output_dir: Path,
    tableau_dir: Path,
    tornado_mac_path: Path,
    output_path: Path = None,
) -> pd.DataFrame:
    """
    Build and export the combined tornado vs whirlpool MAC comparison table.

    Joins both MACs onto the attribute map via strategy_id and writes to
    mac_tornado_to_whirlpool.csv.

    Parameters
    ----------
    whirlpool_mac_df : output of run_mac_analysis for the whirlpool run
    run_output_dir   : whirlpool run directory (contains ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv)
    tableau_dir      : destination directory for the output CSV
    tornado_mac_path : full path to marginal_abatement_costs_tornado.csv
    """
    att_map = pd.read_csv(run_output_dir / "ATTRIBUTE_MAP_TORNADO_WHIRLPOOL.csv")

    tornado_mac = pd.read_csv(tornado_mac_path)
    tornado_mac = tornado_mac[["transformation_code", "sector", "marginal_abatement_cost"]].rename(
        columns={"marginal_abatement_cost": "mac_tornado"}
    )

    whirlpool_mac = whirlpool_mac_df[["transformation_code", "sector", "marginal_abatement_cost"]].rename(
        columns={"marginal_abatement_cost": "mac_whirlpool"}
    )

    mac = att_map.merge(tornado_mac,   on=["transformation_code", "sector"], how="left")
    mac = mac.merge(whirlpool_mac, on=["transformation_code", "sector"], how="left")

    mac["mac_tornado"]   = pd.to_numeric(mac["mac_tornado"],   errors="coerce")
    mac["mac_whirlpool"] = pd.to_numeric(mac["mac_whirlpool"], errors="coerce")

    tableau_dir.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path is not None else tableau_dir / "mac_tornado_to_whirlpool.csv"
    mac.to_csv(out, index=False, encoding="UTF-8")

    return mac
