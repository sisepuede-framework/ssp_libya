
# load packages
library(data.table)
library(reshape2)
library(dplyr)
library(ggplot2)

rm(list=ls())

#ouputfile
dir <- "ssp_modeling/cost-benefits/tornado_plot/data/output/"

tornado <- fread(paste0(dir, '/tornado/tornado_plot.csv'))

tornado$mac_tornado <- tornado$`marginal_total_abatement_cost_(USD/tCO2e)`
 
tornado <- select(tornado, strategy_id,  mac_tornado)



whirlpool <- fread(paste0(dir, '/whirlpool/tornado_plot_whirlpool.csv'))

whirlpool$mac_whirlpool <- whirlpool$`marginal_total_abatement_cost_(USD/tCO2e)`

whirlpool <- select(whirlpool, transformation_name, sector, mac_whirlpool)




mac <- fread('ssp_modeling/cost-benefits/tornado_plot/data/input/map_tornado_to_whirlpool.csv')

mac <- left_join(mac, tornado, by=c('strategy_id'='strategy_id'))

mac <- left_join(mac, whirlpool, by = c('strategy_code' = 'transformation_name', 
                                         'sector' = 'sector'))

fwrite(mac, paste0(dir,'mac_tornado_to_whirlpool.csv'), row.names = F)