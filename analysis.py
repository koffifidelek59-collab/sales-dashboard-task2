# -*- coding: utf-8 -*-
"""
Task 2: cleaning, validation and exploratory analysis of the FactSale file
=========================================================================

Every section below states its INPUT, its METHOD and its OUTPUT before the code,
and defines any term the first time it appears.

Reading order: load, clean, validate, analyse, plot. The order is not arbitrary.
Diagnosing after correcting would report the wrong counts, and removing
duplicates before parsing the dates would compare character strings rather than
dates.

Outputs
-------
data/FactSale_clean.csv     the cleaned table
results/quality_report.json the audit, the KPIs and every figure quoted elsewhere
results/*.csv               the aggregate tables behind each chart
charts/*.png                six figures
"""
import os, json, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
import seaborn as sns
warnings.filterwarnings("ignore")

NAVY, BLUE, MID, LIGHT, PALE = "#10456B", "#1f77b4", "#6BAED6", "#9ECAE1", "#D6E6F2"
plt.rcParams.update({
    "figure.dpi":110,"savefig.dpi":200,"figure.facecolor":"white",
    "font.family":"DejaVu Sans","font.size":11,
    "axes.titlesize":13,"axes.titleweight":"bold","axes.titlepad":10,
    "axes.labelsize":11,"axes.edgecolor":"#3A3A3A","axes.linewidth":0.9,
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.grid":True,"grid.color":"#D9D9D9","grid.linewidth":0.8,"axes.axisbelow":True,
    "legend.frameon":False,"legend.fontsize":10,
    "xtick.labelsize":10,"ytick.labelsize":10})
sns.set_palette([BLUE, MID, LIGHT, NAVY])
R = {}   # results collected for the report

# =============================================================================
# 1. LOAD
# -----------------------------------------------------------------------------
# INPUT  : FactSale.csv, the file as supplied
# METHOD : read once into `raw`, then work on a copy. `raw` is kept because the
#          duplicate check in section 2 needs all 21 original columns: judging a
#          duplicate on a subset of columns would flag genuinely distinct orders.
# OUTPUT : raw and df, 26,397 rows
# =============================================================================
raw = pd.read_csv("FactSale.csv")
R["rows_raw"], R["cols_raw"] = len(raw), raw.shape[1]
df = raw.copy()

# =============================================================================
# 2. CLEANING
# -----------------------------------------------------------------------------
# INPUT  : df, with the dates still stored as text
# METHOD : five steps, in this order. Diagnose, fix types, remove duplicates,
#          handle missing values, derive the analysis fields.
# OUTPUT : a cleaned df and data/FactSale_clean.csv
#
# Terms used below
#   Business key : the set of columns that identifies a transaction when no
#                  surrogate key is trusted. Here: invoice, item, date, quantity
#                  and price.
#   Imputation   : replacing a missing value with an estimate. It is appropriate
#                  when the value is missing at random and the field is not used
#                  to derive another quantity. Neither holds for the delivery
#                  date, so it is deliberately not imputed.
# =============================================================================
# 2.1 Dates. The brief anticipates impossible calendar dates such as 31/02.
#     We test for them explicitly rather than assume either way.
date_audit = {}
for c in ["Invoice Date Key", "Delivery Date Key"]:
    s = df[c].astype("string").str.strip()
    p = pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
    date_audit[c] = {"source_null": int(s.isna().sum()),
                     "unparsed_non_null": int((p.isna() & s.notna()).sum())}
    df[c] = p
R["date_audit"] = date_audit
df = df.rename(columns={"Invoice Date Key":"invoice_date","Delivery Date Key":"delivery_date"})

# 2.2 Duplicates, on the full record and on the business key.
R["dup_full"] = int(raw.duplicated().sum())
R["dup_salekey"] = int(raw["Sale Key"].duplicated().sum())
R["dup_business"] = int(raw.duplicated(subset=["WWI Invoice ID","Stock Item Key",
                                               "Invoice Date Key","Quantity","Unit Price"]).sum())
n0 = len(df); df = df.drop_duplicates().reset_index(drop=True)
R["dup_removed"] = n0 - len(df)

# 2.3 Types.
num = ["Quantity","Unit Price","Tax Rate","Total Excluding Tax","Tax Amount",
       "Profit","Total Including Tax","Total Dry Items","Total Chiller Items"]
for c in num: df[c] = pd.to_numeric(df[c], errors="coerce")
df["Quantity"] = df["Quantity"].astype("int64")
for c in ["Description","Package"]:
    df[c] = df[c].astype("string").str.strip()
df["Package"] = df["Package"].astype("category")

# 2.4 Missing values.
miss = df.isna().sum(); R["missing"] = miss[miss>0].to_dict()
# Delivery date is missing on a handful of rows. It is not imputed: it feeds a
# delivery-lag metric, and an invented date would manufacture a lag that never
# happened. The rows are kept, since every revenue field on them is intact.
R["delivery_missing"] = int(df["delivery_date"].isna().sum())

# 2.5 Derived fields.
df["unit_price_implied"] = df["Total Excluding Tax"] / df["Quantity"]
df["delivery_lag_days"]  = (df["delivery_date"] - df["invoice_date"]).dt.days
df["year"] = df["invoice_date"].dt.year
df["month"] = df["invoice_date"].dt.month
df["quarter"] = df["invoice_date"].dt.quarter
df["year_month"] = df["invoice_date"].dt.to_period("M").dt.to_timestamp()
df["margin_pct"] = 100 * df["Profit"] / df["Total Excluding Tax"]
df["has_customer"] = df["Customer Key"] != 0

# =============================================================================
# 3. VALIDATION
# -----------------------------------------------------------------------------
# INPUT  : the cleaned df
# METHOD : three arithmetic identities tested to a one-cent tolerance, seven
#          business rules, an interquartile screen, and a completeness check on
#          each year.
# OUTPUT : the validation dictionary, written to results/quality_report.json
#
# Terms used below
#   Arithmetic identity : a relation that must hold by construction, for example
#                         quantity times unit price equals the line total. A
#                         breach is a defect, not a business event.
#   IQR screen          : flags a value as an outlier when it lies more than 1.5
#                         interquartile ranges beyond the first or third
#                         quartile. The rule assumes an approximately symmetric
#                         distribution, which sales value is not. It is computed
#                         here and deliberately NOT applied; the reported revenue
#                         share is the reason why.
# =============================================================================
tol = 0.01
v = {}
v["qty_x_price_vs_total"] = int(((df["Quantity"]*df["Unit Price"] - df["Total Excluding Tax"]).abs() > tol).sum())
v["tax_rule"]  = int(((df["Total Excluding Tax"]*df["Tax Rate"]/100 - df["Tax Amount"]).abs() > tol).sum())
v["total_rule"]= int(((df["Total Excluding Tax"] + df["Tax Amount"] - df["Total Including Tax"]).abs() > tol).sum())
v["qty_le_0"]  = int((df["Quantity"] <= 0).sum())
v["price_le_0"]= int((df["Unit Price"] <= 0).sum())
v["price_gt_1000"] = int((df["Unit Price"] > 1000).sum())
v["sales_lt_0"] = int((df["Total Excluding Tax"] < 0).sum())
v["profit_lt_0"] = int((df["Profit"] < 0).sum())
v["delivery_before_invoice"] = int((df["delivery_lag_days"] < 0).sum())
v["customer_key_zero"] = int((~df["has_customer"]).sum())
v["customer_key_zero_pct"] = round(100*(~df["has_customer"]).mean(), 1)
v["profit_lt_0_amount"] = float(df.loc[df["Profit"]<0, "Profit"].sum())
R["validation"] = v

# IQR screen, reported and NOT applied.
iqr = {}
for c in ["Total Excluding Tax","Unit Price","Quantity"]:
    q1,q3 = df[c].quantile([.25,.75]); i = q3-q1
    lo,hi = q1-1.5*i, q3+1.5*i
    mask = (df[c]<lo)|(df[c]>hi)
    iqr[c] = {"n":int(mask.sum()), "pct":round(100*mask.mean(),1),
              "lower":round(lo,2), "upper":round(hi,2),
              "revenue_share":round(100*df.loc[mask,"Total Excluding Tax"].sum()/df["Total Excluding Tax"].sum(),1)}
R["iqr"] = iqr

# Coverage: 2016 is a partial year. This is the single most dangerous feature
# of the file for anyone building a year-on-year chart.
cov = df.groupby("year").agg(rows=("Sale Key","size"),
                             first=("invoice_date","min"), last=("invoice_date","max"),
                             sales=("Total Excluding Tax","sum"))
R["coverage"] = {int(k): {"rows":int(r["rows"]), "first":str(r["first"].date()),
                          "last":str(r["last"].date()), "sales":float(r["sales"])}
                 for k,r in cov.iterrows()}
R["last_full_year"] = int(cov.index[cov.index < cov.index.max()].max())

df.to_csv("data/FactSale_clean.csv", index=False)
R["rows_clean"] = len(df)
print(f"Cleaned: {len(df):,} rows written to data/FactSale_clean.csv")
json.dump(R, open("results/quality_report.json","w"), indent=2, default=str)

# =============================================================================
# 4. EXPLORATORY ANALYSIS
# -----------------------------------------------------------------------------
# INPUT  : the validated df
# METHOD : nine KPIs, then group-and-aggregate by month, calendar month, quarter,
#          package, product and customer, plus the correlation matrix.
# OUTPUT : the KPI dictionary and six tables in results/
#
# Terms used below
#   AOV          : average order value, total sales divided by the number of
#                  distinct invoices. It separates a rise in basket size from a
#                  rise in order count, which a sales total cannot.
#   Gross margin : profit over sales, as a percentage. It is the one ratio that
#                  survives a change of scale, so it compares groups of very
#                  different size.
#   Complete year: a calendar year fully covered by the data. Seasonality is
#                  computed on complete years only, because 2016 stops in May and
#                  including it would weight January to May more heavily.
# =============================================================================
S = "Total Excluding Tax"
total_sales   = df[S].sum()
total_profit  = df["Profit"].sum()
total_orders  = df["WWI Invoice ID"].nunique()
total_lines   = len(df)
aov           = total_sales / total_orders
margin        = 100 * total_profit / total_sales
units         = int(df["Quantity"].sum())

kpi = {"Total sales (excl. tax)": total_sales, "Total profit": total_profit,
       "Gross margin %": margin, "Orders (invoices)": total_orders,
       "Order lines": total_lines, "Average order value": aov,
       "Units sold": units, "Distinct products": df["Description"].nunique(),
       "Identified customers": int(df.loc[df.has_customer,"Customer Key"].nunique())}
R["kpi"] = {k: float(v) for k, v in kpi.items()}

by_month_ts = df.groupby("year_month").agg(sales=(S,"sum"), profit=("Profit","sum"),
                                           orders=("WWI Invoice ID","nunique"))
full = df[df.year <= R["last_full_year"]]
by_cal_month = full.groupby("month")[S].sum()
by_quarter   = full.groupby("quarter")[S].sum()
R["best_month"]   = int(by_cal_month.idxmax()); R["worst_month"] = int(by_cal_month.idxmin())
R["season_ratio"] = float(by_cal_month.max()/by_cal_month.min())
R["best_quarter"] = int(by_quarter.idxmax())

by_package = df.groupby("Package", observed=True).agg(sales=(S,"sum"), profit=("Profit","sum"),
                                                      units=("Quantity","sum"), lines=(S,"size"))
by_package["margin_%"] = 100*by_package.profit/by_package.sales
by_package["share_%"]  = 100*by_package.sales/total_sales
by_package = by_package.sort_values("sales", ascending=False)

by_product = df.groupby("Description").agg(sales=(S,"sum"), profit=("Profit","sum"),
                                           units=("Quantity","sum"), lines=(S,"size"))
by_product["margin_%"] = 100*by_product.profit/by_product.sales
top_products = by_product.sort_values("sales", ascending=False).head(10)
R["top10_share"] = float(100*top_products.sales.sum()/total_sales)

cust = df[df.has_customer].groupby("Customer Key").agg(
    sales=(S,"sum"), profit=("Profit","sum"), orders=("WWI Invoice ID","nunique"),
    first=("invoice_date","min"), last=("invoice_date","max"))
cust["margin_%"] = 100*cust.profit/cust.sales
top_customers = cust.sort_values("sales", ascending=False).head(10)
R["n_customers"] = int(len(cust))
R["top10_cust_share"] = float(100*top_customers.sales.sum()/cust.sales.sum())

sp = df.groupby("Salesperson Key").agg(sales=(S,"sum"), orders=("WWI Invoice ID","nunique"))
R["n_salespeople"] = int(len(sp))

corr = df[["Quantity","Unit Price",S,"Profit","Tax Amount"]].corr()
R["corr_qty_sales"]  = float(corr.loc["Quantity",S])
R["corr_price_qty"]  = float(corr.loc["Unit Price","Quantity"])
R["corr_sales_profit"]= float(corr.loc[S,"Profit"])

for name, obj in [("kpi_summary", pd.Series(kpi).rename("value").to_frame()),
                  ("sales_by_package", by_package.round(2)),
                  ("top10_products", top_products.round(2)),
                  ("top10_customers", top_customers.round(2)),
                  ("monthly_timeseries", by_month_ts.round(2))]:
    obj.to_csv(f"results/{name}.csv")

print(f"\nKPIs  sales={total_sales:,.0f}  profit={total_profit:,.0f}  "
      f"margin={margin:.1f}%  orders={total_orders:,}  AOV={aov:,.0f}")
print(f"Season: best month={R['best_month']} worst={R['worst_month']} ratio={R['season_ratio']:.2f}")
print(f"Top10 products = {R['top10_share']:.1f}% of sales | "
      f"Top10 customers = {R['top10_cust_share']:.1f}% of identified revenue")
print(f"corr(Quantity, Sales)={R['corr_qty_sales']:.2f}  corr(UnitPrice, Quantity)={R['corr_price_qty']:.2f}")
json.dump(R, open("results/quality_report.json","w"), indent=2, default=str)

# =============================================================================
# 5. CHARTS
# -----------------------------------------------------------------------------
# INPUT  : the aggregate tables from section 4
# METHOD : six figures, each chart type chosen from the data type: a line for
#          continuous time, vertical bars for the ordered calendar, horizontal
#          bars where labels are long, a cumulative curve for concentration, and
#          a single-hue heatmap for the correlation matrix.
# OUTPUT : six PNG files in charts/
#
# On the palette: one blue scale throughout. A categorical rainbow would imply
# the groups differ in kind, when here they differ only in magnitude. The grid is
# drawn behind the marks so that grid lines do not cross the bars.
# =============================================================================
def save(fig, name):
    fig.savefig(f"charts/{name}.png", bbox_inches="tight"); plt.close(fig)

# C1 monthly trend, with the partial year shaded
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(by_month_ts.index, by_month_ts.sales, color=BLUE, lw=1.9, label="Monthly sales")
ma = by_month_ts.sales.rolling(12, center=True).mean()
ax.plot(ma.index, ma, color=NAVY, lw=2.6, ls="--", label="12-month moving average")
cut = pd.Timestamp(f"{R['last_full_year']+1}-01-01")
ax.axvspan(cut, by_month_ts.index.max(), color=PALE, zorder=0)
ax.text(cut, ax.get_ylim()[1]*0.94, "  Partial year:\n  Jan to May only",
        fontsize=9.5, color=NAVY, va="top", fontweight="bold")
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
ax.set_xlabel("Month"); ax.set_ylabel("Sales excluding tax")
ax.set_title("Figure 1. Monthly sales, with the incomplete year marked")
ax.legend(loc="upper left"); save(fig, "01_sales_trend")

# C2 seasonality on complete years only
fig, ax = plt.subplots(figsize=(10, 4.2))
mo = by_cal_month.copy(); mo.index = pd.to_datetime(mo.index, format="%m").strftime("%b")
cols = [NAVY if m==mo.idxmax() else (PALE if m==mo.idxmin() else MID) for m in mo.index]
b = ax.bar(mo.index, mo.values, color=cols, edgecolor="black", linewidth=0.8, zorder=3)
for bb,v in zip(b, mo.values):
    ax.text(bb.get_x()+bb.get_width()/2, v*1.012, f"{v/1e6:.2f}M", ha="center", fontsize=9)
ax.set_ylim(0, mo.max()*1.12)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
ax.set_xlabel("Calendar month"); ax.set_ylabel("Sales, 2013 to 2015 combined")
ax.set_title("Figure 2. Seasonality, complete years only")
ax.grid(axis="x", alpha=0); save(fig, "02_seasonality")

# C3 package: sales and margin
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
p = by_package
c1 = [NAVY] + [MID]*(len(p)-1)
b1 = ax[0].bar(p.index.astype(str), p.sales, color=c1, edgecolor="black", linewidth=0.8, zorder=3)
for bb,v in zip(b1, p["share_%"]):
    ax[0].text(bb.get_x()+bb.get_width()/2, bb.get_height()*1.015, f"{v:.0f}%",
               ha="center", fontsize=10, fontweight="bold")
ax[0].set_ylim(0, p.sales.max()*1.14)
ax[0].yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
ax[0].set_ylabel("Sales excluding tax"); ax[0].set_title("(a) Sales by package type", loc="left")
ax[0].grid(axis="x", alpha=0)
c2 = [NAVY if m==p["margin_%"].min() else MID for m in p["margin_%"]]
b2 = ax[1].bar(p.index.astype(str), p["margin_%"], color=c2, edgecolor="black", linewidth=0.8, zorder=3)
for bb,v in zip(b2, p["margin_%"]):
    ax[1].text(bb.get_x()+bb.get_width()/2, v+0.6, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")
ax[1].set_ylim(0, p["margin_%"].max()*1.2)
ax[1].set_ylabel("Gross margin (%)"); ax[1].set_title("(b) Margin by package type", loc="left")
ax[1].grid(axis="x", alpha=0); save(fig, "03_package")

# C4 top products
fig, ax = plt.subplots(figsize=(10, 5))
t = top_products.sales.sort_values()
lab = [x if len(x)<=44 else x[:41]+"..." for x in t.index]
cols = [NAVY if i==len(t)-1 else MID for i in range(len(t))]
b = ax.barh(lab, t.values, color=cols, edgecolor="black", linewidth=0.8, zorder=3)
for bb,v in zip(b, t.values):
    ax.text(v*1.01, bb.get_y()+bb.get_height()/2, f"{v/1e6:.2f}M", va="center",
            fontsize=10, fontweight="bold")
ax.set_xlim(0, t.max()*1.17)
ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
ax.set_xlabel("Sales excluding tax")
ax.set_title(f"Figure 4. Top 10 products, {R['top10_share']:.0f}% of total sales")
ax.grid(axis="y", alpha=0); save(fig, "04_top_products")

# C5 customer concentration, Pareto
fig, ax = plt.subplots(figsize=(10, 4.2))
cs = cust.sales.sort_values(ascending=False)
cum = 100*cs.cumsum()/cs.sum(); x = 100*np.arange(1, len(cs)+1)/len(cs)
ax.plot(x, cum, color=BLUE, lw=2.4)
ax.plot([0,100],[0,100], color=MID, ls=":", lw=1.4, label="Perfect equality")
i20 = int(np.searchsorted(x, 20)); share20 = cum.iloc[min(i20, len(cum)-1)]
ax.axvline(20, color=NAVY, ls="--", lw=1.2)
ax.plot(20, share20, "o", color=NAVY, ms=9, zorder=5)
ax.annotate(f"Top 20% of customers\ncarry {share20:.0f}% of revenue", (20, share20),
            xytext=(30, -18), textcoords="offset points", fontsize=10,
            color=NAVY, fontweight="bold")
ax.set_xlim(0,100); ax.set_ylim(0,102)
ax.set_xlabel("Customers, ranked by revenue (%)"); ax.set_ylabel("Cumulative share of revenue (%)")
ax.set_title("Figure 5. Revenue concentration across identified customers")
ax.legend(loc="lower right"); save(fig, "05_customer_pareto")
R["top20pct_customer_share"] = float(share20)

# C6 correlation heatmap, blues only
fig, ax = plt.subplots(figsize=(7, 5.2))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="Blues", vmin=-1, vmax=1,
            linewidths=0.8, linecolor="white", cbar_kws={"label":"Pearson r"}, ax=ax)
ax.set_title("Figure 6. Correlation between the numeric measures")
save(fig, "06_correlation")

print("Charts written:", sorted(os.listdir("charts")))
json.dump(R, open("results/quality_report.json","w"), indent=2, default=str)
