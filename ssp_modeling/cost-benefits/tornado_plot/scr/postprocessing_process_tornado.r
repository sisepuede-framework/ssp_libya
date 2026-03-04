#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(reshape2)
library(dplyr)
library(ggplot2)

rm(list=ls())

#ouputfile
run <- 'sisepuede_results_sisepuede_run_2026-03-03T12;32;13.541786'

dir.output  <- paste0("ssp_modeling/ssp_run_output/",run,"/")
output.file <- paste0(run, "_WIDE_INPUTS_OUTPUTS.csv")

att <- "ATTRIBUTE_STRATEGY.csv"


sttrategy_ids <- c(0,1000,1001,1002,1003,1004,1005,1006,1007,1008,1009,1010,1011,1012,1013,1014,1015,1016,1017,1018,
                   2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,
                   3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3011,3012,3013,3014,3015,3016,3017,3018,3019,3020,3021,3022,3023,
                   4000,4001,4002,4003,4004,4005,6000,6001)

# load full data
tornado <- fread(paste0(dir.output, output.file))
dim(tornado)

att <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
dim(att)
att <- att[att$strategy_id %in% sttrategy_ids, ]
dim(att)
head(att)

atts <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))
dim(atts)
atts <- atts[atts$strategy_id %in% sttrategy_ids, ]
dim(atts)
head(atts)


tornado <- merge(tornado,att,by="primary_id")
dim(tornado)

#filter for the strategies we want to include in the tornado
tornado <- tornado[tornado$strategy_id %in% sttrategy_ids, ]

dim(tornado)
tornado[, c('design_id','strategy_id','future_id') := NULL]
dim(tornado)

#ouputfile
if (!dir.exists(paste0(dir.output, "/tornado/"))) {
    dir.create(paste0(dir.output, "/tornado/"), recursive = TRUE, showWarnings = FALSE)
}

dir.output.tornado  <- paste0(dir.output,"/tornado/")

fwrite(tornado, paste0(dir.output.tornado, "tornado_data_raw.csv"))
fwrite(att, paste0(dir.output.tornado, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output.tornado, "ATTRIBUTE_STRATEGY.csv"))

dir.input.tornado <- 'ssp_modeling/cost-benefits/tornado_plot/data/input/tornado/'

fwrite(att, paste0(dir.input.tornado, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.input.tornado, "ATTRIBUTE_STRATEGY.csv"))



################################################################################


dir.output  <-dir.output.tornado
output.file <- "tornado_data_raw.csv"

region <- "libya" 
iso_code3 <- "LBY"


# set year_ref for this run
year_ref <- 2022
message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))

# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/scr/tornado/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/scr/tornado/data_prep_new_mapping.r')
