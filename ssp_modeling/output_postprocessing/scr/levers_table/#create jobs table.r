#create jobs table 
jobs_table <- read.csv("ssp_modeling/output_postprocessing/data/levers/Sisepuede - Employment Results - WB (SECTOR).csv")
jobs_table$ssp_sector <- do.call(rbind, strsplit(as.character(jobs_table$Strategy), ":"))[,1]
jobs_table$ssp_transformation_name <- do.call(rbind, strsplit(as.character(jobs_table$Strategy), ":"))[,2]
jobs_table <- subset(jobs_table,Country=="LBY")

write.csv(jobs_table,"ssp_modeling/tableau/data/jobs_demand_libya.csv")

print("Jobs table created")