#create jobs table 
#uganda
jobs_table <- read.csv("/Users/edmun/Library/CloudStorage/OneDrive-Personal/Edmundo-ITESM/3.Proyectos/51. WB Decarbonization Project/Uganda_NDC_3/Tableau/2025_09_27/Sisepuede - Employment Results - WB (SECTOR).csv")
jobs_table$ssp_sector <- do.call(rbind, strsplit(as.character(jobs_table$Strategy), ":"))[,1]
jobs_table$ssp_transformation_name <- do.call(rbind, strsplit(as.character(jobs_table$Strategy), ":"))[,2]
jobs_table <- subset(jobs_table,Country=="UGA")

write.csv(jobs_table,"/Users/edmun/Library/CloudStorage/OneDrive-Personal/Edmundo-ITESM/3.Proyectos/51. WB Decarbonization Project/Uganda_NDC_3/Tableau/2025_09_27/jobs_demand_uganda.csv")

#mexico 
jobs_table <- read.csv("/Users/edmun/Library/CloudStorage/OneDrive-Personal/Edmundo-ITESM/3.Proyectos/51. WB Decarbonization Project/Uganda_NDC_3/Tableau/2025_09_27/Sisepuede - Employment Results - WB (SECTOR).csv")
jobs_table$ssp_sector <- do.call(rbind, strsplit(as.character(jobs_table$Strategy), ":"))[,1]
jobs_table$ssp_transformation_name <- do.call(rbind, strsplit(as.character(jobs_table$Strategy), ":"))[,2]
jobs_table <- subset(jobs_table,Country=="MEX")

write.csv(jobs_table,"/Users/edmun/Downloads/jobs_demand_mexico.csv")
