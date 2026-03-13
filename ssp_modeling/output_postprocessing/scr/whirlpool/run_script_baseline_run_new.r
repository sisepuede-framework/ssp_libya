################################################################################
# This script runs the intertemporal decomposition for the baseline run
################################################################################

te_all<-read.csv("ssp_modeling/output_postprocessing/data/invent/emission_targets_lby_2023.csv")
#te_all <- subset(te_all,Subsector%in%c( "lvst","lsmm","agrc","ippu","waso","trww","frst","lndu","soil"))

# Print shape of te_all
dim(te_all)

target_country <- iso_code3
te_all<-te_all[,c("subsector_ssp","gas","vars","ID",target_country)]
te_all[,"tvalue"] <- te_all[,target_country]
te_all[,target_country] <- NULL
target_vars <- unlist(strsplit(te_all$vars,":"))

# data from SiSePuede
data_all<-fread(paste0(dir.output,output.file)) %>% as.data.frame()
dim(data_all)


rall <- unique(data_all$region)

#set params of rescaling function
initial_conditions_id <- "_0"
time_period_ref <- year_ref-2015

dim(data_all)
data_all <- subset(data_all,time_period>=time_period_ref)
dim(data_all)

# Quick pre-flight check of Vars coverage
all_vars <- unique(unlist(strsplit(te_all$vars, ":", fixed = TRUE)))
all_vars <- trimws(all_vars)
all_vars_made <- make.names(all_vars)
missing <- setdiff(all_vars_made, names(data_all))

all_vars <- setdiff(all_vars, c("emission_co2e_co2_ccsq_direct_air_capture","emission_co2e_ch4_ccsq_direct_air_capture","emission_co2e_n2o_ccsq_direct_air_capture"))

for (var in all_vars) {
  mask <- data_all$time_period == time_period_ref & data_all[[var]] == 0
  changed <- sum(mask, na.rm = TRUE)
  data_all[[var]][mask] <- 0.01
  if (changed > 0) {
    print(paste0("Changed ", changed, " zeros in: ", var, " (time_period == ", time_period_ref, ")"))
  }
}

data_all$emission_co2e_co2_frst_harvested_wood_products = 0
  
if (length(missing)) {
  message("Variables in te_all$Vars not found in data_all: ",
          paste(missing, collapse = ", "))
}


#revise which sector-gas ids are zero at baseline 
te_all$simulation <- 0
for (i in 1:nrow(te_all))
 {
   # i<- 12
    vars <- unlist(strsplit(te_all$vars[i],":"))
    if (length(vars)>1) {
    te_all$simulation[i] <- as.numeric(rowSums(data_all[data_all$primary_id==gsub("_","",initial_conditions_id) &  data_all$time_period==time_period_ref,vars]))
    } else {
     te_all$simulation[i] <- as.numeric(data_all[data_all$primary_id==gsub("_","",initial_conditions_id) &  data_all$time_period==time_period_ref,vars])   
    }
    print(paste0('Sector: ', te_all$ID[i]))
}

te_all$simulation <- ifelse(te_all$simulation==0 & te_all$tvalue>0,0,1)
correct<- aggregate(list(factor_correction=te_all$simulation),list(ID=te_all$ID),mean)
te_all <- merge(te_all,correct,by="ID")
te_all$tvalue <- te_all$tvalue/te_all$factor_correction
te_all$simulation<-NULL 
te_all$factor_correction<-NULL
te_all$ID<-NULL

#now run

source("ssp_modeling/output_postprocessing/scr/invent/intertemporal_decomposition.r")
z<-1
rescale(z,rall,data_all,te_all,initial_conditions_id,dir.output,time_period_ref)

print('Finish:run_script_baseline_run_new_asp process')

