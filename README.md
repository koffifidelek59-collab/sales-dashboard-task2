# Task 2: Sales Data Cleaning, Validation, Analysis and Dashboard

**KOUAME Koffi Fidèle** · Data Analysis Internship · koffifidelek59@gmail.com

---

## Contents

```
KOUAME_Koffi_Fidele_Task2/
├── dashboard.html              Interactive dashboard, opens in any browser
├── report.pdf                  Formal report, 7 pages, with the dashboard view
├── report.tex                  LaTeX source of the report
├── Task2_Analysis.ipynb        Commented notebook, executed, with all outputs
├── DATA_QUALITY.md             What was found, what was done, and why
├── INSIGHTS.md                 Five insights and five recommendations
├── README.md                   This file
├── analysis.py                 Cleaning, validation and EDA, commented
├── dashboard.py                Dashboard build script
├── data/
│   ├── FactSale.csv            Original file
│   └── FactSale_clean.csv      Cleaned dataset, 26,397 rows
├── charts/                     Seven figures, PNG, including the dashboard view
└── results/                    KPI and aggregate tables, CSV, plus the audit JSON
```

## How to open the dashboard

Double-click `dashboard.html`. It is self-contained: no server, no Python, no install.

**Layout.** A header band carrying the year and month filters and the source, a
navigation rail, six KPI cards, three sections of charts, and a closing row of three
summary cards.

**Cross-filtering.** Changing the year or the month updates **every KPI and every chart
at once**. A browser cannot run pandas, so the script precomputes all 58 reachable
filter states and embeds them; the JavaScript looks up a key and calls `Plotly.react`,
which is instant. The payload is 154 KB, and the trade-off is stated in the code because
it is real: larger than a raw extract for a small table, far smaller for a large one.

**Year-on-year deltas** appear under each KPI. They are **suppressed for 2016**, which
covers five months: comparing five months against twelve would report a collapse that
did not happen.

**The closing row is the point of the dashboard.** Key Insights states what the data
shows, Recommendations states what to do about it, and the Data Quality Summary states
what the data will and will not support. A dashboard that shows only charts leaves the
reader to infer the conclusion.

**On colour.** The charts stay on a blue and teal pair. Amber and purple appear only on
KPI icons and section headers, where they label a section rather than encode a quantity.
Colour that encodes nothing is decoration, and decoration on a management report costs
credibility.

**Two themes on purpose.** The interactive dashboard is light, which prints and projects
well. The static view in `charts/07_dashboard.png` matches it.

## The short version

The brief anticipates a dirty file. It largely is not one. Every arithmetic
relationship holds to within one cent, there are no duplicates, and every date
parses. **The real risks are structural, and a routine cleaning pass would have
missed all three:**

1. **34.4% of lines have no customer key.** Every customer metric therefore covers
   two thirds of the business, and must say so.
2. **The last year is incomplete**, January to May 2016 only. Any year-on-year chart
   built without noticing shows a collapse that never happened.
3. **A standard IQR outlier screen would delete 8.9% of the lines carrying 39% of
   all revenue.** Sales value is right-skewed by construction, and a symmetric rule
   applied to a skewed variable removes the top of the distribution rather than
   errors.

No row was deleted. The full reasoning is in `DATA_QUALITY.md`.

## Method

| Stage | What was done |
| :--- | :--- |
| Cleaning | Date parsing with an explicit format audit, type conversion, whitespace trimming, category encoding, derived analysis fields |
| Validation | Three arithmetic identities tested to a one-cent tolerance, seven business rules, an IQR screen computed and deliberately not applied |
| EDA | KPIs, monthly and seasonal trends on complete years only, package and product performance, customer concentration, correlation structure |
| Dashboard | Six linked panels with hover detail, zoom and export |

## Reproducing

### Google Colab, recommended

Open `Task2_Analysis.ipynb` with the badge at the top of the notebook and run every
cell. When it asks for `FactSale.csv`, upload it with the picker that appears. The
last cell downloads the clean dataset, the charts and the result tables back to your
machine, so nothing is lost when the session ends.

### Locally

```bash
pip install pandas numpy matplotlib seaborn plotly
python analysis.py     # cleaning, validation, EDA, charts, results
python dashboard.py     # builds dashboard.html
python dashboard_png.py # builds the static dashboard view
```

## Tools

Python 3, pandas, NumPy, Matplotlib, Seaborn, Plotly.
