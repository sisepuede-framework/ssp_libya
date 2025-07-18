rm(list=ls())

file.name <-"uganda.csv"
iso_code3 <- "UGA"
Country <- "uganda"
output.folder <- "ssp_modeling/ssp_run/asp/"
dir.data <- output.folder
mapping <- read.csv("ssp_modeling/output_postprocessing/data/mapping_corrected_uganda.csv")

#add edgar 
edgar <- read.csv("ssp_modeling/output_postprocessing/data/CSC-GHG_emissions-April2024_to_calibrate.csv")
edgar <- subset(edgar,Code==iso_code3)
edgar$Edgar_Class<- paste(edgar$CSC.Subsector,edgar$Gas,sep=":")

#load data  
data <- read.csv(paste0(dir.data,file.name)) 
data <- subset(data,region==Country)
#emission vars only 
id_vars <-c('region','time_period',"primary_id")
vars <- subset(colnames(data),!(colnames(data)%in%id_vars))
target_vars <- subset(vars,grepl("co2e_",vars)==TRUE)
total_vars <- subset(target_vars,grepl("emission_co2e_subsector_total",target_vars)==TRUE)
target_vars <- subset(target_vars,!(target_vars%in%total_vars))

#load inventory mapping table 
mapping$ids <- paste(row.names(mapping),mapping$Subsector,mapping$Gas,sep="_")
#now create those new columns in the simulation data set 
for  (i in 1:nrow(mapping))
{
#i<- 63
tvars <- mapping$Vars[i]
tvars <- unlist(strsplit(tvars,":"))
tvars <- subset(tvars,tvars%in%colnames(data))
if (length(tvars)>1) {
 data [,mapping$ids[i]] <- rowSums(data[,tvars])
} else if (length(tvars)==1 ) 
{ 
  data [,mapping$ids[i]] <- data[,tvars]
} else {
  data [,mapping$ids[i]] <- 0
} 
}
#now we just keep the new variables and the time period which we will reduce to above 2022
data_new <- data [,c(id_vars,mapping$ids)]
dim(data_new)

#convert from wide to long 
library(data.table)
#library(reshape2)
data_new <- data.table(data_new)
data_new <- melt(data_new, id.vars = id_vars,
                   measure.vars = mapping$ids,
             )
data_new <- data.frame(data_new)
data_new$ids <- as.character(data_new$variable)

#merge with mapping 
 mapping$Vars <- NULL
 colnames(mapping) <- gsub("Edgar_Sector","CSC.Sector",colnames(mapping))
 colnames(mapping) <- gsub("Edgar_Subsector","CSC.Subsector",colnames(mapping)) 
 data_new <- merge(data_new,mapping,by="ids")

#now aggregare at inventory level 
data_new <- aggregate(list(value=data_new$value),by=list(primary_id=data_new$primary_id,
                                             time_period=data_new$time_period,
                                             Edgar_Class=data_new$Edgar_Class,
                                             CSC.Sector=data_new$CSC.Sector,
                                             CSC.Subsector=data_new$CSC.Subsector),sum)


data_new$Year <- data_new$time_period + 2015
data_new$Gas <- do.call("rbind",strsplit(data_new$Edgar_Class,":"))[,2]

#merge additional files  
att <- read.csv(paste0(dir.data,"ATTRIBUTE_PRIMARY.csv"))
dim(data_new)
data_new <- merge(data_new,att,by="primary_id")
dim(data_new)
atts <- read.csv(paste0(output.folder,"ATTRIBUTE_STRATEGY.csv"))
#merge 
dim(data_new)
data_new <- merge(data_new,atts[c("strategy_id","strategy")],by="strategy_id")
dim(data_new)

#melt edgar data 
library(data.table)
id_varsEd <- c("Code","CSC.Sector","CSC.Subsector","Gas","Edgar_Class")
measure.vars_Ed <- subset(colnames(edgar),grepl("X",colnames(edgar))==TRUE)
edgar <- data.table(edgar)
edgar <- melt(edgar, id.vars = id_varsEd, measure.vars =measure.vars_Ed)
edgar <- data.frame(edgar)
edgar$Year <- as.numeric(gsub("X","",edgar$variable))

#make sure both data frames have the same columns 
#edgar 
edgar$variable <- NULL
edgar$strategy_id <- NA
edgar$primary_id <- NA 
edgar$design_id <- NA 
edgar$future_id <- NA 
edgar$Contry <- Country
edgar$strategy <- "Historical" 
edgar$source <- "EDGAR"
edgar <- subset(edgar,Year<=max(edgar$Year))

#data_new 
data_new$time_period <- NULL 
data_new$Code <- iso_code3 
data_new$Contry <- Country
data_new$source <- "SISEPUEDE"
data_new <- subset(data_new,Year>=max(edgar$Year))

#rbind both 
data_new <- rbind(data_new,edgar)
data_new <- data_new[order(data_new$strategy_id,data_new$CSC.Subsector,data_new$Gas,data_new$Year),]

data_new$ids <- paste(data_new$CSC.Subsector,data_new$Gas,data_new$strategy_id,sep=":")


#edit name of strategies 
data_new <- subset(data_new,strategy!="Strategy TX:BASE")
#data_new$strategy <- gsub("Strategy TX:BASE","BAU",data_new$strategy)
data_new$strategy <- gsub("NDC","ASP + NDC",data_new$strategy)
data_new$strategy <- gsub("NZ","ASP + Net Zero",data_new$strategy)

#write file 
dir.out <- paste0("ssp_modeling/Tableau/data/")
file.name <- "emissions_asp.csv"
write.csv(data_new,paste0(dir.out,file.name),row.names=FALSE)

#integrate asp and bau into one single file 
bau <- read.csv(paste0(dir.out,"emissions_bau.csv"))
bau <- subset(bau,strategy!="Historical")
asp <- read.csv(paste0(dir.out,"emissions_asp.csv"))

#
all <- rbind(bau,asp)
#dir.out <- paste0(root,"Tableau/")
file.name <- "emissions.csv"

#remove not modeled sectors 
all <- subset(all,all$CSC.Subsector%in%c("AG - Crops","AG - Livestock","IN - Industrial Processes","LULUCF - Deforestation","LULUCF - Forest Land","Waste - Solid Waste","Waste - Wastewater Treatment"))
#remove historical 
all <- subset(all,strategy!="Historical")

#add power 
power <- read.csv("ssp_modeling/output_postprocessing/data/power.csv")
all <- rbind(all,power)
#add others 
others <- read.csv("ssp_modeling/output_postprocessing/data/other_sectors.csv")
#others$ids <- paste(others$CSC.Subsector,others$Gas,others$strategy_id,sep=":")
all <- rbind(all,others)

#before making adjustment remove historic  
all_historical <- subset(all,strategy=="Historical")
all <- subset(all,strategy!="Historical")

#adjust to the latest inventory 
all$value <-ifelse(grepl("AG - Crops",all$ids)==TRUE,all$value*18.56/8.67,all$value)
all$value <-ifelse(grepl("AG - Livestock",all$ids)==TRUE,all$value*20.51/20.24,all$value)
all$value <-ifelse(grepl("IN - Industrial Processes",all$ids)==TRUE,all$value*0.383/2.3,all$value)
all$value <-ifelse(grepl("LULUCF - Deforestation",all$ids)==TRUE,all$value*56.7/62.61,all$value)
all$value <-ifelse(grepl("Waste - Solid Waste",all$ids)==TRUE,all$value*5.658/0.596,all$value)
all$value <-ifelse(grepl("Waste - Wastewater Treatment",all$ids)==TRUE,all$value*2.56/7.62,all$value)

#make power historical zero 
all_historical[all_historical$CSC.Subsector=="EN - Electricity/Heat","value"]<-0

all_historical$CSC.Subsector <- gsub("LULUCF - Deforestation","LULUCF - Forest Lands",all_historical$CSC.Subsector)


#write
all<-rbind(all,all_historical)
write.csv(all,paste0(dir.out,file.name),row.names=FALSE)

print('Finish post processing process')