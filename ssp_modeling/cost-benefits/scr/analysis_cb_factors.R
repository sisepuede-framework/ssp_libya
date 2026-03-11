#################################################
# Post processing process
#################################################

# load packages
library(data.table)
library(RColorBrewer)
library(ggplot2)
library(scales)




#df <- fread('ssp_modeling/ssp_run_output/sisepuede_summary_results_run_sisepuede_run_2025-08-27T20;12;53.345956/WIDE_INPUTS_OUTPUTS.csv')

out <- dir.output

df  <- fread(paste0(out,'/decomposed_ssp_output.csv'))
#df  <- fread(paste0(out, run, "_WIDE_INPUTS_OUTPUTS.csv"))

att <- fread(paste0(out,'/ATTRIBUTE_PRIMARY.csv'))
stt <- fread(paste0(out,'/ATTRIBUTE_STRATEGY.csv'))


df <- merge(df, att, by = "primary_id", all.x = TRUE)


 
exports <- grep("^exports_enfu_pj_fuel", colnames(df), value = TRUE)


prod_enfu <- grep("^prod_enfu_fuel_", colnames(df), value = TRUE)

prod_enfu <- grep("^prod_enfu_fuel_", colnames(df), value = TRUE)

processing_and_refinement <- grep("^emission_co2e_co2_entc_nbmass_processing_and_refinement_fp", colnames(df), value = TRUE)

other_sectors <- c('emission_co2e_ch4_scoe_commercial_municipal','emission_co2e_ch4_scoe_residential','emission_co2e_ch4_inen_agriculture_and_livestock',
                   'emission_co2e_co2_scoe_nbmass_commercial_municipal','emission_co2e_co2_scoe_nbmass_residential','emission_co2e_co2_inen_nbmass_agriculture_and_livestock',
                   'emission_co2e_n2o_scoe_commercial_municipal','emission_co2e_n2o_scoe_residential','emission_co2e_n2o_inen_agriculture_and_livestock')

waso_compost <- c('emission_co2e_n2o_waso_compost_food',
                   'emission_co2e_n2o_waso_compost_sludge',
                   'emission_co2e_n2o_waso_compost_yard')

ch4_agrc <- c('emission_co2e_ch4_agrc_biomass_burning',
                  'emission_co2e_ch4_agrc_anaerobicdom_rice')

co2_agrc <- c(
  "emission_co2e_co2_agrc_biomass_bevs_and_spices",
  "emission_co2e_co2_agrc_biomass_fruits",
  "emission_co2e_co2_agrc_biomass_nuts",
  "emission_co2e_co2_agrc_biomass_other_woody_perennial",
  "emission_co2e_co2_lndu_conversion_croplands_to_croplands",
  "emission_co2e_co2_lndu_drained_organic_soils_croplands",
  "emission_co2e_co2_lndu_drained_organic_soils_pastures",
  "emission_co2e_co2_lndu_conversion_grasslands_to_grasslands",
  "emission_co2e_co2_lndu_conversion_grasslands_to_pastures",
  "emission_co2e_co2_lndu_conversion_pastures_to_grasslands",
  "emission_co2e_co2_lndu_conversion_pastures_to_pastures",
  "emission_co2e_co2_lndu_biomass_sequestration_grasslands",
  "emission_co2e_co2_lndu_biomass_sequestration_pastures",
  "emission_co2e_co2_soil_lime_use",
  "emission_co2e_co2_soil_urea_use"
)


burning <- c('emission_co2e_n2o_agrc_biomass_burning','emission_co2e_ch4_agrc_biomass_burning')


nf3_ippu_production <- c('emission_co2e_nf3_ippu_production_chemicals','emission_co2e_nf3_ippu_production_electronics')



nemomod_entc_discounted_capital <-  grep("^nemomod_entc_discounted_capital", colnames(df), value = TRUE)





df2 <- select(df, time_period, strategy_id,all_of(nemomod_entc_discounted_capital)) 

fwrite(df2, 'ssp_modeling/cost-benefits/output/capital_cost.csv')



nemomod_entc_discounted_capital <-  grep("^nemomod_entc_discounted_capital", colnames(df), value = TRUE)

nemomod_entc_discounted_capital <-  grep("^nemomod_entc_discounted_capital", 
                                         colnames(select(df, nemomod_entc_discounted_capital_investment_pp_gas_ccs,
                                                         nemomod_entc_discounted_capital_investment_pp_gas)), 
                                         value = TRUE)



nemomod_entc_discounted_operating <-  grep("^nemomod_entc_discounted_operating", colnames(df), value = TRUE)

nemomod_entc_discounted_operating <-  grep("^nemomod_entc_discounted_operating", 
                                           colnames(select(df, -nemomod_entc_discounted_operating_costs_pp_waste_incineration)), 
                                           value = TRUE)

prod_enfu_fuel_electricity_pj <-  grep("^prod_enfu_fuel_electricity_pj", colnames(df), value = TRUE)



gasrecovered_trww_biogas_tonne <-  grep("^vol_trww_ww_treated_advanced_aerobic_m3", colnames(df), value = TRUE)





cost_enfu_fuel_ <-  grep("^cost_enfu_fuel_", colnames(df), value = TRUE)


df_long <- melt(df, 
                id.vars = c("primary_id", "strategy_id", "time_period"), 
                measure.vars = cost_enfu_fuel_biomass_usd)

ggplot(df_long, aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy_id, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "",
       x = "Time Period",
       y = "",
       fill = "Variable") +
  theme_dark()






ggplot(subset(df_long, variable=='yield_agrc_other_annual_tonne'), aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "Vehicle Distance Traveled (Public Transport) Over Time",
       x = "Time Period",
       y = "Distance Traveled",
       fill = "Variable") +
  theme_dark()


pop_lvst_ <- grep("^pop_lvst_", colnames(df), value = TRUE)


df_long <- melt(df, 
                id.vars = c("primary_id", "strategy", "time_period"), 
                measure.vars = pop_lvst_)

ggplot(df_long, aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "",
       x = "Time Period",
       y = "",
       fill = "Variable") +
  theme_dark()

ggplot(subset(df_long, variable=='pop_lvst_buffalo'), aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "Vehicle Distance Traveled (Public Transport) Over Time",
       x = "Time Period",
       y = "Distance Traveled",
       fill = "Variable") +
  theme_dark()











vehicle_distance_traveled_trns_public <- grep("^vehicle_distance_traveled_trns_public", colnames(df), value = TRUE)

df_long <- melt(df, 
                id.vars = c("primary_id", "strategy", "time_period"), 
                measure.vars = vehicle_distance_traveled_trns_public)


ggplot(df_long, aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "Vehicle Distance Traveled (Public Transport) Over Time",
       x = "Time Period",
       y = "Distance Traveled",
       fill = "Variable") +
  theme_dark()


vehicle_distance_traveled_trns_road_light <- grep("^vehicle_distance_traveled_trns_road_light", colnames(df), value = TRUE)

df_long <- melt(df, 
                id.vars = c("primary_id", "strategy", "time_period"), 
                measure.vars = vehicle_distance_traveled_trns_road_light)


ggplot(df_long, aes(x = time_period, y = value, fill = variable)) +
  geom_area(position = "stack") +
  facet_wrap(~ strategy, scales = "fixed") +
  scale_fill_viridis_d(option = "turbo") +
  scale_y_continuous(labels = label_number()) +
  scale_x_continuous(labels = label_number()) +
  labs(title = "",
       x = "Time Period",
       y = "Distance Traveled",
       fill = "Variable") +
  theme_dark()




vehicle_distance_traveled_trns_road_light