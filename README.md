# 🏥 Hospital Inpatient Discharges Dashboard

**Course:** Mathematics for AI-II (Artificial Intelligence) | **Assessment:** Summative Assessment, Scenario 2
**Client scenario:** MediScope Health Analytics, Healthcare AI and Data Insights Team

**Live app:** `<paste your Streamlit Cloud URL here>`
**Student:** `Prahaan Pratik Sanghvi` | **Student ID:** `2505456` | **Registration no.:** `1000332`



## 1. Project overview

An interactive Streamlit dashboard that helps hospital administrators, clinicians and operations managers understand **length of stay, hospital charges, severity, payment mix and facility utilisation** from inpatient discharge records.

### Research questions answered

| # | Question | Where in the app |
|---|----------|------------------|
| 1 | Which diagnosis codes are linked to long stays? | Diagnoses tab (bar chart) |
| 2 | Which age groups incur the highest charges? | Cost & Severity tab |
| 3 | How does patient severity affect total cost? | Cost & Severity tab (box plot) |
| 4 | Which counties and facilities have the longest stays and highest utilisation? | Facilities & Counties tab (heatmap) |
| 5 | How do payment types affect billing and patient mix? | Overview (pie) and Cost & Severity tab |
| 6 | How concentrated are bed-days in very long stays? | EDA & Insights tab |

### Key features

- **Five required visuals**, all interactive (Plotly hover, zoom, filter):
  bar chart (avg stay per diagnosis code), box plot (charges by severity), heatmap (avg stay by facility and county), pie chart (patients by payment type), histogram (length of stay distribution).
- **Extra visuals:** age and gender breakdown, charges by age group, county ranking, stay vs charges scatter.
- **Sidebar filters:** county, age group, severity, payment type, gender, optional outlier hiding.
- **KPI row** that updates with filters: discharges, average and median stay, average and total charges.
- **Auto-generated findings** computed from the filtered data.
- **Transparent cleaning report** and CSV download of filtered data.
- **Robust loading:** column names are matched flexibly, so small naming differences in the CSV will not break the app.

## 2. Data and cleaning

Dataset: Hospital Inpatient Discharges (provided in the assignment Drive folder).

| Step | What the code does |
|------|--------------------|
| Load | `pandas.read_csv`, columns renamed to short readable names |
| Money | `"$1,234.50"` strings converted to float |
| Length of stay | Top-coded values like `"120 +"` converted to numbers |
| Invalid rows | Missing, zero or negative stay and charges removed |
| Null-heavy columns | Dropped (e.g. birth weight, mostly empty/zero) |
| Categories | Trimmed, "Unknown" to missing, `M/F` to Male/Female, ordered severity and age groups |
| Diagnosis mapping | CCS codes grouped into 17 readable medical categories |
| Outliers | Flagged with a 3 x IQR rule, kept by default, optionally hidden |
| Features | `charge_per_day`, `long_stay` (top 10 percent), `dx_category`, `dx_label` |

## 3. Integration details

- **Python 3.10+**, Streamlit (UI), pandas and NumPy (cleaning and analysis), Plotly Express (charts).
- Data is read from `data/*.csv` in the repo, or from the sidebar uploader.
- `@st.cache_data` caches loading and cleaning so filters respond instantly.

## 4. Repository structure

```
.
├── app.py              # Streamlit dashboard (cleaning + EDA + visuals)
├── requirements.txt    # Dependencies for Streamlit Cloud
├── INSIGHTS.md         # Research questions, methodology and findings
├── README.md
├── data/               # Put the discharges CSV here
└── screenshots/        # Dashboard screenshots
```

## 5. Run locally

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
# copy the dataset CSV into ./data/
streamlit run app.py
```

## 6. Deployment instructions (Streamlit Community Cloud)

1. Push `app.py`, `requirements.txt`, `data/` and this README to a public GitHub repository named like `IADAI202<StudentID>-<studentname>`.
2. Go to <https://streamlit.io/cloud> and sign in with GitHub.
3. Click **Create app / Deploy an app** and select your repository, branch `main`, main file `app.py`.
4. Click **Deploy**. When it is live, paste the URL at the top of this README.
5. Grant repository access to `ai.assignments@wacpinternational.org` (Settings, Collaborators).

> If the CSV is larger than GitHub's 100 MB file limit, upload a filtered sample (for example one year) to `data/`, or compress it. The app also accepts uploads in the sidebar.

## 7. Limitations and next steps

- Charges are billed amounts, not actual costs; use the costs column if available for cost analysis.
- The data has no patient identifiers, so true readmission rates cannot be computed.
- Possible extensions: predictive model for length of stay, per-diagnosis cost benchmarks.
