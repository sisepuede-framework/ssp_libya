#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)

rm(list=ls())

source('ssp_modeling/output_postprocessing/scr/run_script_baseline_run_new.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_new_mapping_mongolia.r')

source('ssp_modeling/output_postprocessing/scr/data_prep_drivers.r')