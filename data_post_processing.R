library(readr)
library(dplyr)
library(janitor)

mapped_admissions <- read_csv('data/derived/mapped_admissions.csv') %>% 
  clean_names()

mapped_interviews <- read_csv("data/derived/mapped_interviews.csv") %>% 
  clean_names()

mapped_outcomes <- read_csv("data/derived/mapped_outcomes.csv") %>% 
  clean_names()

years <- c(2015:2024)

bls_by_year = lapply(years, function(x){
  read_csv(sprintf('data/bls/bls_occupation_data_%s.csv', x)) %>% 
    mutate(year = x)
}) %>% 
  bind_rows() %>% 
  select(occupation,
         year,
         pct_women
         ) %>% 
  mutate(census_occupation_code = as.numeric(factor(occupation,levels = sort(unique(occupation)))),
         pct_women = pct_women / 100
  )

bls_industry_by_year <- lapply(years, function(x){
  read_csv(sprintf('data/bls/bls_industry_data_%s.csv', x)) %>% 
    mutate(year = x)
}) %>% 
  bind_rows() %>% 
  select(census_industry=industry, year, pct_women_industry = pct_women) %>% 
  mutate(census_industry_code = as.numeric(factor(census_industry,levels = sort(unique(census_industry)))),
         pct_women_industry = pct_women_industry / 100
         )

bls_by_year %>% group_by(year) %>% count()


joined_interviews <- mapped_interviews %>% 
  left_join(bls_by_year, by = join_by(census_occupation  == occupation, year))

joined_admissions <- mapped_admissions %>% 
  left_join(bls_by_year, by = join_by(census_occupation  == occupation, year))


joined_outcomes <- mapped_outcomes %>% 
  left_join(bls_by_year, by = join_by(census_occupation == occupation, year))


interviews_with_industry <- read_csv("data/derived/interviews_industry_mapping.csv") %>% 
  clean_names()

outcomes_with_industry <- read_csv("data/derived/outcomes_industry_mapping.csv") %>% 
  clean_names() %>% 
  rename(census_industry=occupation) %>% 
  select(-assessment)

admissions_with_industry <- read_csv("data/derived/admissions_industry_mapping.csv") %>% 
  clean_names() %>% 
  rename(census_industry=occupation) %>% 
  select(-assessment)


interviews <- joined_interviews %>% 
  distinct() %>% 
  left_join(interviews_with_industry) %>% 
  left_join(bls_industry_by_year)

outcomes <- joined_outcomes %>% 
  left_join(outcomes_with_industry) %>% 
  left_join(bls_industry_by_year)

admissions <- joined_admissions %>% 
  left_join(admissions_with_industry) %>% 
  left_join(bls_industry_by_year)


bls_failed_admissions <- admissions %>% 
  filter(census_occupation == 'N/A' | census_industry == 'N/A')

bls_failed_outcomes <- outcomes %>% 
  filter(census_occupation == 'N/A' | census_industry == 'N/A')


bls_failed_interviews <- interviews %>% 
  filter(census_occupation == 'N/A' | census_industry == 'N/A')


bls_failed_admissions %>% 
  filter(job_number_1_industry_code %in% bls_industry_by_year$census_industry)

bls_failed_interviews %>% 
  filter(census_industry == 'N/A')

# 15
bls_failed_outcomes %>% 
  filter(census_industry == 'N/A') %>% 
  select(detailed_industry)

library(tidyr)


outcomes_wide <- outcomes %>%
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


write_csv(outcomes, 'data/derived/joined_outcomes_long.csv')
write_csv(interviews, 'data/derived/joined_interviews_long.csv')
write_csv(admissions, 'data/derived/joined_admissions.csv')

write_csv(outcomes_wide, 'data/derived/outcomes_wide.csv')
write_csv(interviews_wide, 'data/derived/interviews_wide.csv')

master <- joined_admissions %>%
  left_join(interviews_wide, by = 'student_id') %>%
  left_join(outcomes_wide, by = 'student_id')

write_csv(master, 'data/derived/master.csv')

write_csv(bls_failed_interviews, 'data/derived/bls_failed_interviews.csv')
write_csv(bls_failed_admissions, 'data/derived/bls_failed_admissions.csv')
write_csv(bls_failed_outcomes, 'data/derived/bls_failed_outcomes.csv')


