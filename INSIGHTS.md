# Insights Report: Hospital Inpatient Discharges


## 1. Problem and background research

Hospital administrators use discharge data to plan beds and staffing, control costs and benchmark facilities. Three measures dominate this work:

- **Length of stay (LOS):** the main driver of bed occupancy and cost; right-skewed, so medians and percentiles matter.
- **Severity of illness (Minor to Extreme):** lets hospitals compare like with like.
- **Payer mix (Medicare, Medicaid, private, self-pay):** shapes reimbursement and financial risk.

Charges are billed amounts rather than actual costs and are heavily skewed, so medians and log scales are used for fair comparison.

## 2. Research questions

1. Which diagnosis codes are linked to long stays?
2. Which age groups incur the highest charges?
3. How does patient severity affect total cost?
4. Which counties and facilities have the longest stays or highest utilisation?
5. How do payment types differ in billing and patient volume?
6. How much of total bed-day demand comes from the longest 10% of stays?

## 3. Data cleaning summary

| Step | Result |
|---|---|
| Raw rows | 2,101,588 |
| Removed: missing stay/charges | 0 |
| Removed: zero or negative stay/charges | 0 |
| Clean rows | 2,101,588 (100.0% kept; 0 removed) |
| Null-heavy columns dropped | Payment Typology 3, birth_weight |
| Extreme stay outliers flagged (3 x IQR) | 105,567 |
| Extreme charge outliers flagged (3 x IQR) | 94,147 |

Charges converted from text to numbers, top-coded stays such as `120 +` parsed, categories standardised, diagnosis codes mapped to 17 medical categories. Outliers are flagged, not deleted.

## 4. Statistical overview

| Statistic | Length of stay (days) | Charges ($) |
|---|---|---|
| count | 2101588.0 | 2101588.0 |
| mean | 5.7 | 73305.4 |
| std | 8.4 | 149202.0 |
| min | 1.0 | 0.3 |
| 25% | 2.0 | 19095.0 |
| 50% | 3.0 | 38421.5 |
| 75% | 6.0 | 77233.4 |
| 90% | 12.0 | 152889.9 |
| 99% | 40.0 | 572406.0 |
| max | 120.0 | 17935752.0 |

- Skewness: stay **5.8**, charges **17.9**. Both are strongly right-skewed, so the median (3 days, $38,422) describes a typical patient better than the mean (5.7 days, $73,305).
- Spearman correlation between stay and charges: **0.61**.

## 5. Findings by research question

### Q1. Diagnoses linked to long stays

Top 10 diagnoses by average stay (at least 30 cases):

| dx_label | Avg stay | Median stay | Cases | Avg charges |
|---|---|---|---|---|
| INJ046 - SPINAL CORD INJURY (SCI), SUBSEQUENT ENCOUNTER | 27.6 | 22.5 | 176 | $168,904 |
| PNL002 - SHORT GESTATION; LOW BIRTH WEIGHT; AND FETAL GROWTH RETARDATION | 27.5 | 17.0 | 307 | $342,318 |
| PNL005 - RESPIRATORY DISTRESS SYNDROME | 26.2 | 12.0 | 311 | $352,525 |
| NEO060 - LEUKEMIA - ACUTE MYELOID LEUKEMIA (AML) | 22.9 | 20.0 | 1567 | $398,925 |
| INF001 - TUBERCULOSIS | 21.5 | 15.0 | 363 | $215,731 |
| NEO059 - LEUKEMIA - ACUTE LYMPHOBLASTIC LEUKEMIA (ALL) | 20.9 | 18.0 | 586 | $438,436 |
| CIR022 - SEQUELA OF HEMORRHAGIC CEREBROVASCULAR DISEASE | 18.5 | 16.0 | 1126 | $121,603 |
| PNL006 - RESPIRATORY PERINATAL CONDITION | 17.6 | 5.0 | 452 | $251,118 |
| NEO006 - HEAD AND NECK CANCERS - HYPOPHARYNGEAL | 17.3 | 11.0 | 83 | $249,750 |
| INJ045 - TRAUMATIC BRAIN INJURY (TBI); CONCUSSION, SUBSEQUENT ENCOUNTER | 16.9 | 14.0 | 987 | $111,039 |

By broad medical category:

| dx_category | Avg stay | Cases |
|---|---|---|
| Mental health | 9.9 | 152521 |
| Infectious diseases | 9.2 | 229209 |
| Cancers / Neoplasms | 7.2 | 95638 |
| Injury & poisoning | 6.5 | 154436 |
| Nervous system | 5.9 | 63179 |
| Respiratory | 5.6 | 102227 |
| Circulatory (heart) | 5.6 | 280995 |
| Genitourinary | 5.2 | 89737 |
| Blood disorders | 5.2 | 26273 |
| Skin disorders | 5.1 | 30542 |
| Digestive | 4.9 | 182025 |
| Endocrine & metabolic | 4.6 | 93975 |
| Symptoms & signs | 4.6 | 46566 |
| Eye disorders | 4.1 | 2602 |
| Other / Unknown | 4.1 | 233922 |
| Musculoskeletal | 4.0 | 93301 |
| Ear disorders | 3.1 | 3420 |
| Pregnancy & childbirth | 2.7 | 221020 |

**Insight:** Mental health has the longest average stay among categories (9.9 days).

### Q2. Age groups and charges

| age_group | discharges | avg_charges | total_charges | share_of_total |
|---|---|---|---|---|
| 0 to 17 | 289732 | $47,628 | $13,799,431,079 | 9.0% |
| 18 to 29 | 192051 | $47,659 | $9,152,899,020 | 5.9% |
| 30 to 49 | 415681 | $58,971 | $24,513,305,494 | 15.9% |
| 50 to 69 | 584480 | $90,104 | $52,663,757,670 | 34.2% |
| 70 or Older | 619644 | $87,031 | $53,928,390,059 | 35.0% |

**Insight:** **70 or Older** generates the highest total charges (35.0% of the total); **50 to 69** has the highest average charge per stay.

### Q3. Severity and cost

| severity | patients | avg_los | median_charges | avg_charges |
|---|---|---|---|---|
| Minor | 638227 | 2.9 | $24,460 | $36,691 |
| Moderate | 760535 | 4.8 | $35,808 | $54,648 |
| Major | 499474 | 7.3 | $55,768 | $90,427 |
| Extreme | 200802 | 14.6 | $113,301 | $217,898 |

**Insight:** median charges rise **4.6x** from Minor to Extreme, and average stay rises from 2.9 to 14.6 days.

### Q4. Counties and facilities

Counties with the longest average stay (at least 30 discharges):

| county | discharges | avg_los | avg_charges |
|---|---|---|---|
| Columbia | 3320 | 7.4 | $33,676 |
| Niagara | 9605 | 6.7 | $18,985 |
| Westchester | 114986 | 6.7 | $92,089 |
| Rensselaer | 1966 | 6.5 | $33,702 |
| Monroe | 108333 | 6.5 | $37,112 |
| Clinton | 11287 | 6.5 | $47,836 |
| Bronx | 162542 | 6.2 | $82,072 |
| Kings | 190687 | 6.0 | $68,989 |
| Erie | 111157 | 6.0 | $41,375 |
| Manhattan | 364676 | 5.9 | $117,064 |

Top 10 high-utilisation facilities (by total bed-days):

| facility | discharges | bed_days | avg_los | total_charges |
|---|---|---|---|---|
| Mount Sinai Hospital | 49945 | 322063 | 6.4 | $6,215,839,394 |
| Strong Memorial Hospital | 41399 | 289284 | 7.0 | $2,011,490,448 |
| New York-Presbyterian Hospital - Columbia Presbyterian Center | 41787 | 278770 | 6.7 | $6,637,156,374 |
| North Shore University Hospital | 49203 | 271883 | 5.5 | $5,530,860,122 |
| Long Island Jewish Medical Center | 40371 | 264700 | 6.6 | $3,922,024,255 |
| New York-Presbyterian Hospital - New York Weill Cornell Center | 42221 | 239826 | 5.7 | $5,344,278,604 |
| Montefiore Medical Center - Henry & Lucy Moses Div | 35992 | 228455 | 6.3 | $5,124,557,958 |
| Albany Medical Center Hospital | 36471 | 220848 | 6.1 | $2,144,329,940 |
| Stony Brook University Hospital | 35986 | 219999 | 6.1 | $3,462,130,182 |
| NYU Langone Hospitals | 42864 | 214167 | 5.0 | $7,111,247,325 |

**Insight:** the 10 busiest facilities account for **21.1%** of all bed-days.

### Q5. Payment type

| payment | patients | avg_los | avg_charges | total_charges | patient_share |
|---|---|---|---|---|---|
| Medicare | 826250 | 6.9 | $87,976 | $72,690,162,901 | 39.3% |
| Medicaid | 646300 | 5.5 | $62,512 | $40,401,270,813 | 30.8% |
| Private Health Insurance | 307242 | 4.5 | $69,981 | $21,501,002,183 | 14.6% |
| Blue Cross/Blue Shield | 224090 | 4.2 | $60,655 | $13,592,129,153 | 10.7% |
| Managed Care, Unspecified | 28229 | 4.6 | $49,255 | $1,390,424,418 | 1.3% |
| Self-Pay | 27107 | 4.6 | $50,460 | $1,367,811,210 | 1.3% |
| Miscellaneous/Other | 22526 | 5.7 | $96,817 | $2,180,908,621 | 1.1% |
| Federal/State/Local/VA | 18604 | 5.2 | $45,411 | $844,824,852 | 0.9% |
| Department of Corrections | 1240 | 5.8 | $71,975 | $89,249,172 | 0.1% |

**Insight:** **Medicare** covers the most patients (39.3%); **Miscellaneous/Other** has the highest average charge.

### Q6. Concentration of bed-days

The longest 10% of stays (more than 12 days) use **41.8%** of all bed-days.

### Extra: average stay by severity and age group (days)

| severity | 0 to 17 | 18 to 29 | 30 to 49 | 50 to 69 | 70 or Older |
|---|---|---|---|---|---|
| Minor | 2.3 | 3.2 | 3.0 | 3.1 | 3.1 |
| Moderate | 4.3 | 4.9 | 4.7 | 5.1 | 4.8 |
| Major | 7.9 | 5.9 | 6.4 | 7.5 | 7.5 |
| Extreme | 29.5 | 14.7 | 14.8 | 15.4 | 13.0 |

## 6. Key takeaways

- **INJ046 - SPINAL CORD INJURY (SCI), SUBSEQUENT ENCOUNTER** has the longest average stay (27.6 days, 176 cases).
- Age group **70 or Older** accounts for 35.0% of all charges.
- Median charge is 4.6x higher for Extreme than Minor cases.
- **Columbia** county has the longest average stay (7.4 days).
- The top 10 facilities hold 21.1% of all bed-days.
- **Medicare** is the most common payer (39.3% of patients).
- The longest 10% of stays consume 41.8% of all bed-days.

## 7. Recommendations

1. Prioritise discharge planning for the diagnoses and age groups with the longest stays (Q1, Q2).
2. Monitor high-severity admissions closely, as they drive the largest share of cost per patient (Q3).
3. Benchmark facilities against peers with similar severity mix before judging efficiency (Q4).
4. Focus length-of-stay reduction on the longest 10% of stays, which use 42% of bed-days (Q6).
5. Track payer mix by facility to anticipate financial risk (Q5).

## 8. Limitations

Charges are billed amounts, not costs. There are no patient identifiers, so readmission rates cannot be calculated. Outliers use a fixed 3 x IQR rule. Rankings use a minimum of 30 cases to limit small-sample noise. Findings describe association, not causation.
