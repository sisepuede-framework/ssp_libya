#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(RColorBrewer)
library(ggplot2)
library(scales)


df  <- fread(paste0(dir.output,'/decomposed_ssp_output.csv'))
#df  <- fread(paste0(out, run, "_WIDE_INPUTS_OUTPUTS.csv"))

att <- fread(paste0(dir.output,'/ATTRIBUTE_PRIMARY.csv'))
stt <- fread(paste0(dir.output,'/ATTRIBUTE_STRATEGY.csv'))


df <- merge(df, att, by = "primary_id", all.x = TRUE)

nemomod_entc_capital <-  grep("^nemomod_entc_discounted_capital", colnames(df), value = TRUE)
nemomod_entc_operating <-  grep("^nemomod_entc_discounted_operating", colnames(df), value = TRUE)

vars <- c(nemomod_entc_capital, nemomod_entc_operating)


capex <- df[, lapply(.SD, sum, na.rm = TRUE),  
            by = list(strategy_id,time_period),  
            .SDcols =vars]

fwrite(capex, 'ssp_modeling/cost-benefits/output/nemomod_entc_capex_opex_time.csv')


capex <- df[, lapply(.SD, sum, na.rm = TRUE),  
             by = strategy_id,  
             .SDcols =vars]

capex <-melt(
  capex,
  id.vars = "strategy_id",
  variable.name = "var",
  value.name = "value"
)

capex <- dcast(
  capex,
  var ~ strategy_id,
  value.var = "value"
)
  

fwrite(capex, 'ssp_modeling/cost-benefits/output/nemomod_entc_capex_opex.csv')













