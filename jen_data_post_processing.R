library(readxl)
library(dplyr)
library(janitor)


mapped_admissions <- read_excel('data/derived/admissions_gendered_jen.xlsx') %>% 
  clean_names() %>% 
  select(-idx)

mapped_interviews <- read_excel("data/derived/interviews_gendered_jen.xlsx") %>% 
  clean_names() 

mapped_outcomes <- read_excel("data/derived/outcomes_gendered_jen.xlsx") %>% 
  clean_names()

company_gender_pct <- read_excel("data/derived/company_gender_share_jen.xlsx") %>% 
  clean_names() %>% 
  select(name, industry_jen = industry, women_pct_industry = women_pct) %>% 
  distinct()

function_gender_pct <- read_excel("data/supplemental/function_gender percentage.xlsx", sheet = "for Simon_cleaned") %>% 
  select(census_occupation = `Job Function`,
         women_pct_occupation = `Average of func_gen_perc`
         ) %>% 
  distinct()

joined_admissions <- mapped_admissions %>% 
  left_join(function_gender_pct) %>% 
  left_join(company_gender_pct, by=c('job_1_organization'='name'))

joined_interviews <- mapped_interviews %>% 
  left_join(function_gender_pct) %>% 
  left_join(company_gender_pct, by=c('employer'='name'))

joined_outcomes <- mapped_outcomes %>% 
  left_join(function_gender_pct) %>% 
  left_join(company_gender_pct, by=c('employer'='name'))

failed_admissions <- joined_admissions %>% 
  filter(census_occupation == 'N/A' | industry_jen == 'N/A')

failed_outcomes = joined_outcomes %>% 
  filter(census_occupation == 'N/A' | industry_jen == 'N/A')


failed_interviews <- joined_interviews %>% 
  filter(census_occupation == 'N/A' | industry_jen == 'N/A')

# 1
failed_admissions %>% 
  filter(industry_jen == 'N/A')

# 0
failed_interviews %>% 
  filter(industry_jen == 'N/A')

# 9
failed_outcomes %>% 
  filter(industry_jen == 'N/A') %>% 
  select(detailed_industry)

library(tidyr)


outcomes_wide <- joined_outcomes %>%
  arrange(student_id, offer_received_date) %>%
  group_by(student_id) %>%
  mutate(outcome_num = row_number()) %>%
  ungroup() %>%
  select(-outcome_id) %>% 
  pivot_wider(
    id_cols = student_id,
    names_from = outcome_num,
    values_from = -c(student_id, outcome_num, graduation_year, gender, most_recent_job_pre_school),
    names_glue = "{.value}_{outcome_num}"
  ) %>% left_join(
    joined_outcomes %>% 
      group_by(student_id) %>% 
      count() %>% 
      rename(num_offers=n)
  )



interviews_wide <- joined_interviews %>%
  arrange(student_id, interview_date) %>%
  group_by(student_id) %>%
  mutate(outcome_num = row_number()) %>%
  ungroup() %>%
  pivot_wider(
    id_cols = student_id,
    names_from = outcome_num,
    values_from = -c(student_id, outcome_num, graduation_year),
    names_glue = "{.value}_{outcome_num}"
  ) %>% 
  left_join(
    joined_interviews %>% 
      group_by(student_id) %>% 
      count() %>% 
      rename(num_interviews=n)
  )
library(readr)

write_csv(joined_outcomes, 'data/derived/outcomes_long_jen.csv')
write_csv(joined_interviews, 'data/derived/interviews_long_jen.csv')
write_csv(joined_admissions, 'data/derived/admissions_jen.csv')

write_csv(outcomes_wide, 'data/derived/outcomes_wide_jen.csv')
write_csv(interviews_wide, 'data/derived/interviews_wide_jen.csv')

master <- joined_admissions %>%
  left_join(interviews_wide, by = 'student_id') %>%
  left_join(outcomes_wide, by = 'student_id')

write_csv(master, 'data/derived/master_jen.csv')

write_csv(failed_interviews, 'data/derived/failed_interviews_jen.csv')
write_csv(failed_admissions, 'data/derived/failed_admissions_jen.csv')
write_csv(failed_outcomes, 'data/derived/failed_outcomes_jen.csv')


