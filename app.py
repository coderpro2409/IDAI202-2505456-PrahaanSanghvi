"""
Hospital Inpatient Discharges Dashboard
MediScope Health Analytics - Healthcare AI and Data Insights Team

Run locally:  streamlit run app.py
Data:         the app downloads the discharges CSV from the configured Google Drive folder
              into ./data/ on first run. You can still upload a CSV from the sidebar to
              override it.
"""

import glob
import os

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    import gdown
    GDOWN_AVAILABLE = True
except ImportError:
    GDOWN_AVAILABLE = False

st.set_page_config(
    page_title="Hospital Inpatient Discharges Dashboard",
    page_icon="🏥",
    layout="wide",
)

# ----------------------------------------------------------------------------
# GOOGLE DRIVE CONFIGURATION
# ----------------------------------------------------------------------------
# Folder ID taken from:
# https://drive.google.com/drive/u/0/folders/1bHdRvwN77O3F85pFzoqmzBY2wNOabXms
GDRIVE_FOLDER_ID = "1bHdRvwN77O3F85pFzoqmzBY2wNOabXms"

# Robust base directory for local storage of the downloaded dataset
APP_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
DATA_DIR = os.path.join(APP_DIR, "data")


# ----------------------------------------------------------------------------
# 1. COLUMN MAPPING
# ----------------------------------------------------------------------------
COLUMN_ALIASES = {
    "county": ["hospital county", "county", "hospital_county"],
    "facility": ["facility name", "facility", "hospital", "facility_name"],
    "age_group": ["age group", "age_group", "age"],
    "gender": ["gender", "sex"],
    "race": ["race"],
    "los": ["length of stay", "length_of_stay", "los"],
    "dx_code": [
        "ccsr diagnosis code",   # <-- CCSR (refined) codes, alphanumeric
        "ccsr dx code",
        "ccs diagnosis code",    # <-- legacy CCS (numeric)
        "diagnosis code",
        "ccs_diagnosis_code",
        "dx code",
        "apr drg code",          # <-- fallback if CCSR missing
    ],
    "dx_desc": [
        "ccsr diagnosis description",
        "ccsr dx description",
        "ccs diagnosis description",
        "diagnosis description",
        "apr drg description",
        "diagnosis",
    ],
    "severity": [
        "apr severity of illness description",
        "severity of illness description",
        "severity",
        "apr severity of illness",
    ],
    "payment": [
        "payment typology 1",
        "payment type",
        "payment_typology_1",
        "payment",
        "expected payment typology",
    ],
    "charges": ["total charges", "charges", "total_charges"],
    "costs": ["total costs", "costs", "total_costs"],
    "birth_weight": ["birth weight", "birth_weight"],
    "disposition": ["patient disposition", "disposition"],
    "admit_type": ["type of admission", "admission type"],
}

REQUIRED = ["los", "charges"]

SEVERITY_ORDER = ["Minor", "Moderate", "Major", "Extreme"]
AGE_ORDER = ["0 to 17", "18 to 29", "30 to 49", "50 to 69", "70 or Older"]


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().replace("_", " ").split())


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw columns to short readable names using the alias table."""
    lookup = {_norm(c): c for c in df.columns}
    mapping = {}
    for short, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if _norm(a) in lookup and lookup[_norm(a)] not in mapping:
                mapping[lookup[_norm(a)]] = short
                break
    return df.rename(columns=mapping)


# ----------------------------------------------------------------------------
# 2. DATA LOADING & CLEANING
# ----------------------------------------------------------------------------
def clean_money(series: pd.Series) -> pd.Series:
    """Convert strings such as '$1,234.50' or '(200)' to float."""
    s = series.astype(str).str.strip()
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    s = s.str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def clean_los(series: pd.Series) -> pd.Series:
    """Length of stay: '120 +' style top-codes become 120, text becomes number."""
    s = series.astype(str).str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def standardise_text(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "Unknown": pd.NA, "U": pd.NA})
    return s


# CCSR alphanumeric prefixes -> broad medical category
CCSR_PREFIX_MAP = {
    "INF": "Infectious diseases",
    "NEO": "Cancers / Neoplasms",
    "END": "Endocrine & metabolic",
    "BLD": "Blood disorders",
    "MBD": "Mental health",
    "NVS": "Nervous system",
    "EYE": "Eye disorders",
    "EAR": "Ear disorders",
    "CIR": "Circulatory (heart)",
    "RSP": "Respiratory",
    "DIG": "Digestive",
    "GEN": "Genitourinary",
    "PRG": "Pregnancy & childbirth",
    "SKN": "Skin disorders",
    "MUS": "Musculoskeletal",
    "CNG": "Congenital anomalies",
    "PRN": "Perinatal / newborn",
    "INJ": "Injury & poisoning",
    "SYM": "Symptoms & signs",
    "FAS": "Symptoms & signs",
    "OTH": "Other conditions",
}


def map_dx_category(code) -> str:
    """Map diagnosis codes to broad readable medical categories.

    Handles two families:
      * Legacy CCS numeric codes (integer ranges).
      * CCSR alphanumeric codes (3-letter prefix, e.g. 'INF012', 'NVS005').
    """
    if code is None:
        return "Other / Unknown"
    try:
        if pd.isna(code):
            return "Other / Unknown"
    except (TypeError, ValueError):
        pass

    s = str(code).strip().upper()
    if s in ("", "NAN", "<NA>", "NONE"):
        return "Other / Unknown"

    # ---- Try legacy CCS numeric range mapping -----------------------------
    try:
        c = int(float(s))
    except (TypeError, ValueError):
        c = None

    if c is not None:
        ranges = [
            (1, 10, "Infectious diseases"),
            (11, 47, "Cancers / Neoplasms"),
            (48, 58, "Endocrine & metabolic"),
            (59, 64, "Blood disorders"),
            (65, 75, "Mental health"),
            (76, 95, "Nervous system"),
            (96, 121, "Circulatory (heart)"),
            (122, 134, "Respiratory"),
            (135, 155, "Digestive"),
            (156, 175, "Genitourinary"),
            (176, 196, "Pregnancy & childbirth"),
            (197, 200, "Skin disorders"),
            (201, 212, "Musculoskeletal"),
            (213, 217, "Congenital anomalies"),
            (218, 224, "Perinatal / newborn"),
            (225, 244, "Injury & poisoning"),
            (245, 259, "Other conditions"),
        ]
        for lo, hi, name in ranges:
            if lo <= c <= hi:
                return name
        return "Other / Unknown"

    # ---- CCSR alphanumeric prefix mapping ---------------------------------
    return CCSR_PREFIX_MAP.get(s[:3], "Other / Unknown")


@st.cache_data(show_spinner="Loading and cleaning data...")
def load_and_clean(source) -> tuple[pd.DataFrame, dict]:
    # --- MEMORY OPTIMIZATION 1: Load only necessary columns ---
    # Peek at the CSV to get the raw column names
    peek = pd.read_csv(source, nrows=1)
    available_cols = peek.columns.tolist()
    
    # Match available columns to our alias list
    lookup = {_norm(c): c for c in available_cols}
    cols_to_load = set()
    for aliases in COLUMN_ALIASES.values():
        for alias in aliases:
            if _norm(alias) in lookup:
                cols_to_load.add(lookup[_norm(alias)])
                break
                
    # Load the dataset with ONLY the required columns
    # dtype_backend="pyarrow" vastly reduces memory usage for strings
    try:
        raw = pd.read_csv(source, usecols=lambda c: c in cols_to_load, low_memory=False, dtype_backend="pyarrow")
    except Exception:
        # Fallback if pyarrow backend fails
        raw = pd.read_csv(source, usecols=lambda c: c in cols_to_load, low_memory=False)

    report = {"raw_rows": len(raw), "raw_cols": raw.shape[1]}

    # --- MEMORY OPTIMIZATION 2: Rename in-place to avoid duplicating the dataframe ---
    lookup_rename = {_norm(c): c for c in raw.columns}
    mapping = {}
    for short, aliases in COLUMN_ALIASES.items():
        for a in aliases:
            if _norm(a) in lookup_rename and lookup_rename[_norm(a)] not in mapping:
                mapping[lookup_rename[_norm(a)]] = short
                break
    raw.rename(columns=mapping, inplace=True)
    df = raw

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(
            f"Could not find required column(s): {missing}. "
            f"Columns in file: {list(available_cols)}"
        )

    # Drop null-heavy columns (> 60% missing), e.g. birth weight
    null_share = df.isna().mean()
    dropped = null_share[null_share > 0.60].index.tolist()
    if "birth_weight" in df.columns:
        bw = pd.to_numeric(df["birth_weight"], errors="coerce").replace(0, np.nan)
        if bw.isna().mean() > 0.60 and "birth_weight" not in dropped:
            dropped.append("birth_weight")
    df.drop(columns=[c for c in dropped if c in df.columns], inplace=True)
    report["dropped_columns"] = dropped

    # Numeric conversions
    df["charges"] = clean_money(df["charges"])
    if "costs" in df.columns:
        df["costs"] = clean_money(df["costs"])
    df["los"] = clean_los(df["los"])

    # Remove invalid records (and free memory)
    before = len(df)
    df.dropna(subset=["los", "charges"], inplace=True)
    report["dropped_null_numeric"] = before - len(df)

    before = len(df)
    df = df[(df["los"] > 0) & (df["charges"] > 0)].copy() # .copy() defragments memory
    report["dropped_invalid_values"] = before - len(df)

    # Standardise categoricals
    for col in ["county", "facility", "age_group", "gender", "race",
                "severity", "payment", "dx_desc"]:
        if col in df.columns:
            df[col] = standardise_text(df[col])

    if "gender" in df.columns:
        df["gender"] = df["gender"].replace({"M": "Male", "F": "Female", "U": pd.NA})
    if "severity" in df.columns:
        df["severity"] = df["severity"].str.title()
        df["severity"] = pd.Categorical(df["severity"], categories=SEVERITY_ORDER, ordered=True)
    if "age_group" in df.columns:
        present = [a for a in AGE_ORDER if a in set(df["age_group"].dropna())]
        extra = sorted(set(df["age_group"].dropna()) - set(present))
        df["age_group"] = pd.Categorical(df["age_group"], categories=present + extra, ordered=True)

    # Diagnosis code -> readable category
    if "dx_code" in df.columns:
        df["dx_code"] = (
            df["dx_code"].astype("string").str.strip()
            .replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA})
        )
        df["dx_category"] = df["dx_code"].map(map_dx_category)
        if "dx_desc" in df.columns:
            df["dx_label"] = (
                df["dx_code"].fillna("?") + " - " + df["dx_desc"].fillna("")
            )
        else:
            df["dx_label"] = "Code " + df["dx_code"].fillna("?")

    # Outlier handling
    def iqr_flag(s: pd.Series) -> pd.Series:
        q1, q3 = s.quantile([0.25, 0.75])
        return s > q3 + 3 * (q3 - q1)

    df["los_outlier"] = iqr_flag(df["los"])
    df["charge_outlier"] = iqr_flag(df["charges"])
    report["los_outliers"] = int(df["los_outlier"].sum())
    report["charge_outliers"] = int(df["charge_outlier"].sum())

    # Feature engineering
    df["charge_per_day"] = df["charges"] / df["los"]
    df["long_stay"] = df["los"] > df["los"].quantile(0.90)

    # --- MEMORY OPTIMIZATION 3: Downcast floats to 32-bit ---
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = df[col].astype('float32')

    df = df.reset_index(drop=True)
    report["clean_rows"] = len(df)
    return df, report

# ----------------------------------------------------------------------------
# 2b. GOOGLE DRIVE DOWNLOAD
# ----------------------------------------------------------------------------
def download_data_from_gdrive(folder_id: str, output_dir: str = DATA_DIR):
    """
    Download every file from a public Google Drive folder into `output_dir`
    and return the path to the largest CSV found. Returns None on failure.
    """
    if not GDOWN_AVAILABLE:
        st.error(
            "The `gdown` package is required to fetch the dataset from Google Drive. "
            "Install it with `pip install gdown` and restart the app."
        )
        return None

    os.makedirs(output_dir, exist_ok=True)
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

    with st.spinner(
        "Downloading dataset from Google Drive... "
        "This may take a while for large files (only happens once)."
    ):
        try:
            gdown.download_folder(
                url=folder_url,
                output=output_dir,
                quiet=False,
                use_cookies=False,
            )
        except Exception as e:
            st.error(
                f"Failed to download from Google Drive. "
                f"Please verify the folder ID and that the folder is shared as "
                f"'Anyone with the link'. Error: {e}"
            )
            return None

    csv_files = glob.glob(os.path.join(output_dir, "*.csv"))
    if not csv_files:
        st.error("Google Drive download completed but no CSV file was found.")
        return None

    # Pick the largest CSV (likely the actual dataset, not a small metadata file)
    csv_files.sort(key=os.path.getsize, reverse=True)
    return csv_files[0]


def find_default_file():
    """
    Locate the dataset:
      1. Any *.csv already sitting in ./data/
      2. Otherwise download the Google Drive folder and pick the largest CSV.
    """
    local_files = sorted(
        glob.glob(os.path.join(DATA_DIR, "*.csv")),
        key=os.path.getsize,
        reverse=True,
    )
    if local_files:
        return local_files[0]

    st.info(
        "No local dataset found in `data/`. "
        "Downloading from the configured Google Drive folder..."
    )
    downloaded = download_data_from_gdrive(GDRIVE_FOLDER_ID)
    if downloaded:
        st.success(f"Dataset downloaded: `{os.path.basename(downloaded)}`")
        return downloaded

    return None


# ----------------------------------------------------------------------------
# 3. SIDEBAR: DATA SOURCE + FILTERS
# ----------------------------------------------------------------------------
st.title("🏥 Hospital Inpatient Discharges Dashboard")
st.caption(
    "MediScope Health Analytics | Helping administrators, clinicians and operations "
    "managers understand length of stay, cost and utilisation."
)

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload discharges CSV (optional)", type=["csv"])
    st.caption(
        f"Default source: Google Drive folder `…/{GDRIVE_FOLDER_ID[-8:]}` "
        f"(downloaded once into `data/`)."
    )

source = uploaded if uploaded is not None else find_default_file()
if source is None:
    st.info(
        "No dataset found. Ensure the Google Drive folder "
        f"`{GDRIVE_FOLDER_ID}` is shared as 'Anyone with the link', or "
        "upload a CSV from the sidebar."
    )
    st.stop()

try:
    df, report = load_and_clean(source)
except Exception as e:
    st.error(f"Could not process the dataset: {e}")
    st.stop()

with st.sidebar:
    st.header("Filters")

    def multi(label, col):
        if col not in df.columns:
            return None
        opts = [o for o in df[col].cat.categories] if str(df[col].dtype) == "category" else sorted(df[col].dropna().unique())
        return st.multiselect(label, opts, default=[])

    sel_county = multi("County", "county")
    sel_age = multi("Age group", "age_group")
    sel_sev = multi("Severity", "severity")
    sel_pay = multi("Payment type", "payment")
    sel_gender = multi("Gender", "gender")
    hide_outliers = st.checkbox("Hide extreme outliers (stay & charges)", value=False)

mask = pd.Series(True, index=df.index)
for col, sel in [
    ("county", sel_county),
    ("age_group", sel_age),
    ("severity", sel_sev),
    ("payment", sel_pay),
    ("gender", sel_gender),
]:
    if sel:
        mask &= df[col].isin(sel)
if hide_outliers:
    mask &= ~(df["los_outlier"] | df["charge_outlier"])
f = df[mask]

if f.empty:
    st.warning("No records match the current filters.")
    st.stop()

# ----------------------------------------------------------------------------
# 4. KPI ROW
# ----------------------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Discharges", f"{len(f):,}")
k2.metric("Avg length of stay", f"{f['los'].mean():.1f} days")
k3.metric("Median stay", f"{f['los'].median():.0f} days")
k4.metric("Avg charges", f"${f['charges'].mean():,.0f}")
k5.metric("Total charges", f"${f['charges'].sum() / 1e6:,.1f}M")

tab_overview, tab_dx, tab_cost, tab_fac, tab_eda, tab_data = st.tabs(
    ["Overview", "Diagnoses", "Cost & Severity", "Facilities & Counties", "EDA & Insights", "Data & Cleaning"]
)

# ----------------------------------------------------------------------------
# TAB: OVERVIEW
# ----------------------------------------------------------------------------
with tab_overview:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribution of length of stay")
        cap = st.slider("Show stays up to (days)", 5, int(max(10, f["los"].quantile(0.995))), 30)
        fig = px.histogram(
            f[f["los"] <= cap], x="los", nbins=min(cap, 60),
            labels={"los": "Length of stay (days)", "count": "Discharges"},
            color_discrete_sequence=["#1f77b4"],
        )
        fig.add_vline(x=f["los"].median(), line_dash="dash", line_color="red",
                      annotation_text=f"Median {f['los'].median():.0f}d")
        fig.update_layout(yaxis_title="Discharges", bargap=0.05)
        st.plotly_chart(fig, width="stretch")
        st.caption("Stays are right-skewed: most patients leave within a few days while a small group stays much longer and drives bed occupancy.")
    with c2:
        st.subheader("Patients by payment type")
        if "payment" in f.columns:
            pay = f["payment"].fillna("Unknown").value_counts().reset_index()
            pay.columns = ["payment", "patients"]
            fig = px.pie(pay, names="payment", values="patients", hole=0.4)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No payment column in this dataset.")

    if "age_group" in f.columns and "gender" in f.columns:
        st.subheader("Discharges by age group and gender")
        ag = f.groupby(["age_group", "gender"], observed=True).size().reset_index(name="discharges")
        st.plotly_chart(
            px.bar(ag, x="age_group", y="discharges", color="gender", barmode="group",
                   labels={"age_group": "Age group"}),
            width="stretch",
        )

# ----------------------------------------------------------------------------
# TAB: DIAGNOSES
# ----------------------------------------------------------------------------
with tab_dx:
    if "dx_label" not in f.columns:
        st.info("No diagnosis code column in this dataset.")
    else:
        st.subheader("Average hospital stay per diagnosis code")
        cc1, cc2 = st.columns([1, 1])
        top_n = cc1.slider("Number of diagnoses", 5, 30, 15)
        min_cases = cc2.slider("Minimum cases per diagnosis", 1, 500, 30)
        dx = (
            f.groupby("dx_label")
            .agg(avg_los=("los", "mean"), cases=("los", "size"), avg_charges=("charges", "mean"))
            .query("cases >= @min_cases")
            .sort_values("avg_los", ascending=False)
            .head(top_n)
            .reset_index()
        )
        if dx.empty:
            st.info("No diagnoses meet the minimum case count. Lower the slider.")
        else:
            fig = px.bar(
                dx.sort_values("avg_los"), x="avg_los", y="dx_label", orientation="h",
                color="avg_los", color_continuous_scale="Reds",
                hover_data={"cases": True, "avg_charges": ":,.0f"},
                labels={"avg_los": "Average stay (days)", "dx_label": "Diagnosis"},
            )
            fig.update_layout(height=max(400, 28 * len(dx)), coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch")
            st.caption("Diagnoses with the longest average stay. A minimum case count avoids rare diagnoses distorting the ranking.")

        st.subheader("Average stay by broad medical category")
        cat = f.groupby("dx_category").agg(avg_los=("los", "mean"), cases=("los", "size")).reset_index().sort_values("avg_los")
        st.plotly_chart(
            px.bar(cat, x="avg_los", y="dx_category", orientation="h", hover_data=["cases"],
                   labels={"avg_los": "Average stay (days)", "dx_category": "Category"}),
            width="stretch",
        )

# ----------------------------------------------------------------------------
# TAB: COST & SEVERITY
# ----------------------------------------------------------------------------
with tab_cost:
    if "severity" not in f.columns:
        st.info("No severity column in this dataset.")
    else:
        st.subheader("Total charges by severity of illness")
        log_scale = st.checkbox("Log scale (recommended - charges are heavily skewed)", value=True)
        fig = px.box(
            f.dropna(subset=["severity"]), x="severity", y="charges", color="severity",
            category_orders={"severity": SEVERITY_ORDER},
            labels={"charges": "Total charges ($)", "severity": "Severity"},
            log_y=log_scale, points=False,
        )
        st.plotly_chart(fig, width="stretch")
        sev = (
            f.groupby("severity", observed=True)
            .agg(patients=("los", "size"), avg_los=("los", "mean"),
                 median_charges=("charges", "median"), avg_charges=("charges", "mean"))
            .round(1)
        )
        st.dataframe(sev, width="stretch")

    if "age_group" in f.columns:
        st.subheader("Average and total charges by age group")
        ag = f.groupby("age_group", observed=True).agg(avg_charges=("charges", "mean"), total_charges=("charges", "sum")).reset_index()
        a1, a2 = st.columns(2)
        a1.plotly_chart(px.bar(ag, x="age_group", y="avg_charges", title="Average charge per stay",
                               labels={"avg_charges": "$", "age_group": "Age group"}), width="stretch")
        a2.plotly_chart(px.bar(ag, x="age_group", y="total_charges", title="Total charges",
                               labels={"total_charges": "$", "age_group": "Age group"}), width="stretch")

    if "payment" in f.columns:
        st.subheader("Billing by payment type")
        pay = f.groupby("payment").agg(avg_charges=("charges", "mean"), avg_los=("los", "mean"), patients=("los", "size")).reset_index().sort_values("avg_charges", ascending=False)
        st.plotly_chart(px.bar(pay, x="payment", y="avg_charges", hover_data=["avg_los", "patients"],
                               labels={"avg_charges": "Average charges ($)", "payment": "Payment type"}),
                        width="stretch")

# ----------------------------------------------------------------------------
# TAB: FACILITIES & COUNTIES
# ----------------------------------------------------------------------------
with tab_fac:
    if "facility" not in f.columns or "county" not in f.columns:
        st.info("Facility/county columns are not in this dataset.")
    else:
        st.subheader("Average stay by facility and county (heatmap)")
        n_fac = st.slider("Top facilities by volume", 5, 40, 15)
        top_fac = f["facility"].value_counts().head(n_fac).index
        sub = f[f["facility"].isin(top_fac)]
        pt = sub.pivot_table(index="facility", columns="county", values="los", aggfunc="mean")
        pt = pt.dropna(axis=1, how="all")
        fig = px.imshow(
            pt, aspect="auto", color_continuous_scale="YlOrRd",
            labels=dict(color="Avg stay (days)", x="County", y="Facility"),
        )
        fig.update_layout(height=max(450, 30 * len(pt)))
        st.plotly_chart(fig, width="stretch")
        st.caption("Blank cells mean the facility has no discharges in that county. Darker cells show longer average stays.")

        st.subheader("High-utilisation facilities")
        util = (
            f.groupby("facility")
            .agg(discharges=("los", "size"), bed_days=("los", "sum"), avg_los=("los", "mean"), total_charges=("charges", "sum"))
            .sort_values("bed_days", ascending=False).head(15).round(1)
        )
        st.dataframe(util, width="stretch")

        st.subheader("Counties ranked by average stay")
        cty = f.groupby("county").agg(avg_los=("los", "mean"), discharges=("los", "size")).query("discharges >= 30").sort_values("avg_los", ascending=False).head(20).reset_index()
        st.plotly_chart(px.bar(cty, x="county", y="avg_los", hover_data=["discharges"],
                               labels={"avg_los": "Avg stay (days)", "county": "County"}), width="stretch")

# ----------------------------------------------------------------------------
# TAB: EDA & INSIGHTS
# ----------------------------------------------------------------------------
with tab_eda:
    st.subheader("Statistical summary")
    st.dataframe(f[["los", "charges", "charge_per_day"]].describe(percentiles=[.25, .5, .75, .9, .99]).round(1), width="stretch")

    skew_los = f["los"].skew()
    skew_ch = f["charges"].skew()
    corr = f["los"].corr(f["charges"], method="spearman")
    st.markdown(
        f"- Skewness of length of stay is **{skew_los:.1f}** and of charges **{skew_ch:.1f}**, so both are strongly right-skewed. Medians describe a typical patient better than means.\n"
        f"- Spearman correlation between stay and charges is **{corr:.2f}**: longer stays are generally more expensive."
    )

    st.subheader("Pivot: average stay by severity and age group")
    if "severity" in f.columns and "age_group" in f.columns:
        pv = f.pivot_table(index="severity", columns="age_group", values="los", aggfunc="mean", observed=True).round(1)
        st.dataframe(pv.style.background_gradient(cmap="YlOrRd", axis=None), width="stretch")

    st.subheader("Pivot: average charges by county and payment type")
    if "county" in f.columns and "payment" in f.columns:
        top_c = f["county"].value_counts().head(10).index
        pv2 = f[f["county"].isin(top_c)].pivot_table(index="county", columns="payment", values="charges", aggfunc="mean").round(0)
        st.dataframe(pv2.style.format("{:,.0f}").background_gradient(cmap="Blues", axis=None), width="stretch")

    st.subheader("Stay length vs charges")
    sample = f.sample(min(5000, len(f)), random_state=1)
    color_col = "severity" if "severity" in f.columns else None
    st.plotly_chart(
        px.scatter(sample, x="los", y="charges", color=color_col, opacity=0.5, log_y=True,
                   labels={"los": "Length of stay (days)", "charges": "Total charges ($)"}),
        width="stretch",
    )
    st.caption("Random sample of up to 5,000 discharges for speed.")

    st.subheader("Key findings (computed from the current filter)")
    findings = []
    if "dx_label" in f.columns:
        d = f.groupby("dx_label").agg(a=("los", "mean"), n=("los", "size")).query("n >= 30").sort_values("a", ascending=False)
        if len(d):
            findings.append(f"Longest average stay (30+ cases): **{d.index[0]}** at {d.iloc[0]['a']:.1f} days.")
    if "severity" in f.columns:
        s = f.groupby("severity", observed=True)["charges"].median()
        if len(s) > 1:
            findings.append(f"Median charge rises from ${s.iloc[0]:,.0f} ({s.index[0]}) to ${s.iloc[-1]:,.0f} ({s.index[-1]}), about {s.iloc[-1] / s.iloc[0]:.1f}x.")
    if "age_group" in f.columns:
        a = f.groupby("age_group", observed=True)["charges"].sum()
        findings.append(f"Highest total spend comes from age group **{a.idxmax()}** ({a.max() / a.sum():.0%} of all charges).")
    if "county" in f.columns:
        c = f.groupby("county").agg(a=("los", "mean"), n=("los", "size")).query("n >= 30").sort_values("a", ascending=False)
        if len(c):
            findings.append(f"County with the longest average stay (30+ cases): **{c.index[0]}** ({c.iloc[0]['a']:.1f} days).")
    findings.append(f"The longest 10% of stays account for **{f.loc[f['long_stay'], 'los'].sum() / f['los'].sum():.0%}** of all bed-days.")
    for item in findings:
        st.markdown(f"- {item}")

# ----------------------------------------------------------------------------
# TAB: DATA & CLEANING
# ----------------------------------------------------------------------------
with tab_data:
    st.subheader("Cleaning report")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Raw rows", f"{report['raw_rows']:,}")
    r2.metric("Clean rows", f"{report['clean_rows']:,}")
    r3.metric("Removed (null/invalid)", f"{report['dropped_null_numeric'] + report['dropped_invalid_values']:,}")
    r4.metric("Columns dropped", len(report["dropped_columns"]))
    st.markdown(
        f"- Dropped null-heavy columns: `{report['dropped_columns'] or 'none'}`\n"
        f"- Rows with missing stay or charges removed: **{report['dropped_null_numeric']:,}**\n"
        f"- Rows with zero or negative stay/charges removed: **{report['dropped_invalid_values']:,}**\n"
        f"- Extreme outliers flagged (kept unless hidden in the sidebar): stay **{report['los_outliers']:,}**, charges **{report['charge_outliers']:,}**\n"
        "- Currency strings converted to floats; categories standardised; diagnosis codes mapped to medical categories.\n"
        "- Engineered features: `charge_per_day`, `long_stay`, `dx_category`, `dx_label`."
    )
    st.subheader("Preview of cleaned data")
    st.dataframe(f.head(200), width="stretch")
    st.download_button("Download filtered data (CSV)", f.to_csv(index=False).encode(), "filtered_discharges.csv", "text/csv")
