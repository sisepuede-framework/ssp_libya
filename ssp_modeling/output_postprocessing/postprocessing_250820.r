#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)
library(mFilter)
library(ggplot2)

rm(list=ls())

# Create data directory in case it doesn't exist
dir.create("ssp_modeling/tableau/data", recursive = TRUE, showWarnings = FALSE)

#ouputfile
dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_results_run_sisepuede_run_2026-03-09T17;13;41.063042/"
output.file <- "sisepuede_results_sisepuede_run_2026-03-09T17;13;41.063042_WIDE_INPUTS_OUTPUTS.csv"

region <- "libya" 
iso_code3 <- "LBY"

year_ref <- 2022

source('ssp_modeling/output_postprocessing/scr/run_script_baseline_run_new.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_new_mapping.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')

