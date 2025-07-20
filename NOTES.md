
- [ ] Exctract number of children and age at time of admission (0 for unborn) using LLM
- [ ] Merge two admissions data files on the studen ID, prefering the file from Admissions if conflicting data and merging all other columns
- [ ] Create new file for analysis data
- [ ] Verify that flagged companies are actually relevant in the analysis, i.e., did the student actually matriculate?

Interviews.xlsx:
- [ ] Using the Interviews.xlsx, create variable "Number of interviews", "Number of offers"
- [ ] Gender-code employer column in Interviews.xlsx
- [ ] Check Jen's documentation on gender-coding procedure

Outcome Data.xslx:
- [ ] Gender-code employer column


TODO:
- [x] Check, how many records each of the flagged companies affect, so we can direct manual data review efforts in the most effective way
- [ ] Clean up unmatched company names
- [x] Keep student IDs that are in the `outcomes`, not necessarily in `interviews`
- [x] Prepare list of IDs that appear in `outcomes` but not in `admissions` and send to Julia
- [x] Prepare list of IDs that appear in `admissions` but not in `outcomes` and send to Julia
- [x] Keep all info on student data
- [ ] Gender coding:
  - [ ] `companies`: Use column `industries`
  - [ ] `outcomes`: Use columns `detailed industry` and `detailed function` (gendered separately)
  - [ ] Find Census industry categories that we have gender distribution for
  - [ ] Map LinkedIn company industries to Census industries taking the job function/title into account
  - [ ] Submit mapping to human review
  - [ ] Send table with company and industries and example model output

Questions:
- [ ] What to do with the aggregate categories? Ignore or fallback?
  - [ ] Break aggregate and granular categories into two separate kinds of industries
- [ ] Table 11 and 14 clearly relevant, what about the others?

- Validate model mapping with Jen's manual coding


Use Jen's table to get categories, then use Census to fill in missing ones.
