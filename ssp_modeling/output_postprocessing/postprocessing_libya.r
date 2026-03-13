#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)
library(mFilter)
library(ggplot2)
library(dplyr)

rm(list=ls())

#ouputfile

run <- 'sisepuede_results_run_sisepuede_run_2026-03-13T07;36;11.592365'
run_id <- 'sisepuede_results_sisepuede_run_2026-03-13T07;36;11.592365'

dir.output  <- paste0("ssp_modeling/ssp_run_output/",run,"/")
output.file <- paste0(run_id, "_WIDE_INPUTS_OUTPUTS.csv")


region <- "libya" 
iso_code3 <- "LBY"

year_ref <- 2023

source('ssp_modeling/output_postprocessing/scr/invent/run_script_baseline_run_new.r')

source('ssp_modeling/output_postprocessing/scr/invent/data_prep_new_mapping.r')

source('ssp_modeling/output_postprocessing/scr/invent/data_prep_drivers.r')

