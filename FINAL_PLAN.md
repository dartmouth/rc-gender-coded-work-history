## AI Variables
- Two variables (occupation gender and industry gender) in two modalities:
  - census-based, determined using table from corresponding year or closest one (NEEDS RESEARCH TO FIND TABLES)
  - Jen-based, using the same mapping for all years
- Let AI use N/A to mark records that have no clear correspondence to available variable levels
  - Julia will do human review of all unmapped records and mark them as manually mapped
  - Revisit: Let AI take another pass at the missing mappings?


- Sources for industry mapping:
  - Jen-based mapping: company_gender_share_jm.xlsx
  - Census-based mapping: tbd
- Sources for occupation mapping:
  - Jen-based mapping: function_gender percentage.xlsx
  - census-based mapping: cpsaat11.xlsx (2024) + tbd (for additional years)

## Output format
- Deliver three separate tables
- Concatenate all three tables into a wide format table with one row per student (creating multiple columns like interview_1, interview_2, interview_3, ... for one-to-many relationships)
- In wide table, include variable number_of_interviews

## Conventional variables (secondary concerns)
- Prepare additional variables for regression modeling
- Prepare codebook
- Variables according to `Model Variables - for Simon.docx`
- Additional variables from previous discussion (TODO: find list)

Target: Mid-May