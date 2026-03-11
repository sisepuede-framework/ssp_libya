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
run <- 'sisepuede_results_sisepuede_run_2026-03-10T22;51;32.350715'

dir.output  <- paste0("ssp_modeling/ssp_run_output/",run,"/")
output.file <- paste0(run, "_WIDE_INPUTS_OUTPUTS.csv")

att <- "ATTRIBUTE_STRATEGY.csv"

# load full data
whirlpool <- fread(paste0(dir.output, output.file))
dim(whirlpool)

att <- read.csv(paste0(dir.output,"ATTRIBUTE_PRIMARY.csv"))
dim(att)
att <- att[att$strategy_id==0 | (att$strategy_id >= 6004 & att$strategy_id <= 6045), ]
dim(att)
head(att)

atts <- read.csv(paste0(dir.output,"ATTRIBUTE_STRATEGY.csv"))
dim(atts)
atts <- atts[att$strategy_id==0 | (atts$strategy_id >= 6004 & atts$strategy_id <= 6045), ]
dim(atts)
head(atts)


whirlpool <- merge(whirlpool,att,by="primary_id")
dim(whirlpool)

#filter for the strategies we want to include in the whirlpool
whirlpool <- whirlpool[whirlpool$strategy_id==0 | (whirlpool$strategy_id >= 6004 & whirlpool$strategy_id <= 6045), ]

dim(whirlpool)
whirlpool[, c('design_id','strategy_id','future_id') := NULL]
dim(whirlpool)

# replace fail runs
# dir.output  <- "ssp_modeling/ssp_run_output/sisepuede_results_sisepuede_run_2026-03-06T16;13;19.208759/"
# output.file <- "sisepuede_results_sisepuede_run_2026-03-06T16;13;19.208759_WIDE_INPUTS_OUTPUTS.csv"

# error <- fread(paste0(dir.output, output.file))
# error <- error[error$primary_id == 86086 | error$primary_id == 103103, ]
# dim(error)

# dim(whirlpool)
# whirlpool <- whirlpool[!whirlpool$primary_id %in% c(86086, 103103), ]
# dim(whirlpool)

# whirlpool <- rbind(whirlpool,error)
# dim(whirlpool)



#ouputfile
if (!dir.exists(paste0(dir.output, "/whirlpool/"))) {
    dir.create(paste0(dir.output, "/whirlpool/"), recursive = TRUE, showWarnings = FALSE)
}

dir.output.whirlpool  <- paste0(dir.output,"/whirlpool/")

fwrite(whirlpool, paste0(dir.output.whirlpool, "whirlpool_data_raw.csv"))
fwrite(att, paste0(dir.output.whirlpool, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.output.whirlpool, "ATTRIBUTE_STRATEGY.csv"))

dir.input.whirlpool <- 'ssp_modeling/cost-benefits/tornado_plot/data/input/whirlpool/'

fwrite(att, paste0(dir.input.whirlpool, "ATTRIBUTE_PRIMARY.csv"))
fwrite(atts, paste0(dir.input.whirlpool, "ATTRIBUTE_STRATEGY.csv"))



################################################################################


dir.output  <- dir.output.whirlpool
output.file <- "whirlpool_data_raw.csv"

region <- "libya" 
iso_code3 <- "LBY"


# set year_ref for this run
year_ref <- 2022
message(sprintf("=== Running post-processing for year_ref = %d ===", year_ref))

# run the original steps (they read year_ref from the env)
source('ssp_modeling/output_postprocessing/scr/whirlpool/run_script_baseline_run_new.r')
source('ssp_modeling/output_postprocessing/scr/whirlpool/data_prep_new_mapping.r')
