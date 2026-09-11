# -*- coding: utf-8 -*-
"""Static dashboard view, for the PDF report and for anyone without a browser."""
import json, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec
import seaborn as sns

NAVY, BLUE, MID, LIGHT, PALE = "#10456B", "#1f77b4", "#6BAED6", "#9ECAE1", "#D6E6F2"
plt.rcParams.update({"figure.dpi":110,"savefig.dpi":180,"figure.facecolor":"white",
 "font.family":"DejaVu Sans","font.size":10,"axes.titlesize":11.5,"axes.titleweight":"bold",
 "axes.titlepad":8,"axes.labelsize":10,"axes.edgecolor":"#3A3A3A","axes.linewidth":0.8,
 "axes.spines.top":False,"axes.spines.right":False,"axes.grid":True,"grid.color":"#DCDCDC",
 "grid.linewidth":0.7,"axes.axisbelow":True,"legend.frameon":False,"legend.fontsize":9,
 "xtick.labelsize":9,"ytick.labelsize":9})

df = pd.read_csv("data/FactSale_clean.csv", parse_dates=["invoice_date","year_month"])
R = json.load(open("results/quality_report.json")); k = R["kpi"]; S = "Total Excluding Tax"
LF = int(R["last_full_year"])

fig = plt.figure(figsize=(16, 11.5))
gs = GridSpec(4, 2, figure=fig, height_ratios=[0.30, 1, 1, 1], hspace=0.42, wspace=0.20)

# ---- KPI band -------------------------------------------------------------
axk = fig.add_subplot(gs[0, :]); axk.axis("off")
kpis = [("TOTAL SALES", f"{k['Total sales (excl. tax)']/1e6:.2f}M"),
        ("GROSS PROFIT", f"{k['Total profit']/1e6:.2f}M"),
        ("MARGIN", f"{k['Gross margin %']:.1f}%"),
        ("ORDERS", f"{k['Orders (invoices)']:,.0f}"),
        ("AVG ORDER VALUE", f"{k['Average order value']:,.0f}"),
        ("UNITS SOLD", f"{k['Units sold']:,.0f}"),
        ("PRODUCTS", f"{k['Distinct products']:,.0f}")]
for i, (lab, val) in enumerate(kpis):
    x = i/len(kpis) + 0.5/len(kpis)
    axk.text(x, 0.72, val, ha="center", fontsize=21, fontweight="bold", color=NAVY)
    axk.text(x, 0.28, lab, ha="center", fontsize=9.5, color="#555555")
axk.axhline(0.04, color=NAVY, lw=1.4)

# ---- 1 trend --------------------------------------------------------------
ax = fig.add_subplot(gs[1, :])
ts = df.groupby("year_month").agg(sales=(S,"sum")).reset_index()
ax.plot(ts.year_month, ts.sales, color=BLUE, lw=1.9, label="Monthly sales")
ma = ts.set_index("year_month").sales.rolling(12, center=True).mean()
ax.plot(ma.index, ma, color=NAVY, lw=2.5, ls="--", label="12-month moving average")
ax.axvspan(pd.Timestamp(f"{LF+1}-01-01"), ts.year_month.max(), color=PALE, zorder=0)
ax.text(pd.Timestamp(f"{LF+1}-01-15"), ax.get_ylim()[1]*0.93,
        "Partial year\nJan to May", fontsize=9.5, color=NAVY, va="top", fontweight="bold")
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
ax.set_ylabel("Sales excl. tax"); ax.set_title("Sales trend, with the incomplete year marked", loc="left")
ax.legend(loc="upper left", ncol=2)

# ---- 2 seasonality --------------------------------------------------------
ax = fig.add_subplot(gs[2, 0])
mo = df[df.year <= LF].groupby("month")[S].sum()
mo.index = pd.to_datetime(mo.index, format="%m").strftime("%b")
c = [NAVY if v==mo.max() else (LIGHT if v==mo.min() else MID) for v in mo.values]
ax.bar(mo.index, mo.values, color=c, edgecolor="black", linewidth=0.7, zorder=3)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
ax.set_title(f"Seasonality, complete years only", loc="left"); ax.grid(axis="x", alpha=0)

# ---- 3 package ------------------------------------------------------------
ax = fig.add_subplot(gs[2, 1])
p = (df.groupby("Package").agg(sales=(S,"sum"), profit=("Profit","sum"))
       .assign(margin=lambda x: 100*x.profit/x.sales).sort_values("sales"))
c = [NAVY if m==p.margin.min() else BLUE for m in p.margin]
p["share"] = 100*p.sales/p.sales.sum()
b = ax.barh(p.index.astype(str), p.sales, color=c, edgecolor="black", linewidth=0.7, zorder=3)
for bb, m, sh in zip(b, p.margin, p.share):
    ax.text(bb.get_width()*1.35, bb.get_y()+bb.get_height()/2,
            f"{sh:.1f}% of sales, {m:.0f}% margin",
            va="center", fontsize=8.5, fontweight="bold", color=NAVY)
ax.set_xscale("log"); ax.set_xlim(p.sales.min()*0.5, p.sales.max()*60)
ax.set_title("Sales by package (log scale), share and margin labelled", loc="left")
ax.grid(axis="y", alpha=0)

# ---- 4 top products -------------------------------------------------------
ax = fig.add_subplot(gs[3, 0])
t = df.groupby("Description")[S].sum().sort_values(ascending=False).head(10).sort_values()
lab = [x if len(x)<=34 else x[:31]+"..." for x in t.index]
c = [NAVY if i==len(t)-1 else MID for i in range(len(t))]
ax.barh(lab, t.values, color=c, edgecolor="black", linewidth=0.7, zorder=3)
ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
ax.set_title(f"Top 10 products, {R['top10_share']:.0f}% of sales", loc="left")
ax.tick_params(axis="y", labelsize=8); ax.grid(axis="y", alpha=0)

# ---- 5 customer Pareto ----------------------------------------------------
ax = fig.add_subplot(gs[3, 1])
cs = df[df.has_customer].groupby("Customer Key")[S].sum().sort_values(ascending=False)
x = 100*np.arange(1, len(cs)+1)/len(cs); y = 100*cs.cumsum().values/cs.sum()
ax.plot(x, y, color=BLUE, lw=2.4); ax.fill_between(x, 0, y, color=PALE, zorder=0)
ax.plot([0,100],[0,100], color=MID, ls=":", lw=1.3)
s20 = float(np.interp(20, x, y))
ax.axvline(20, color=NAVY, ls="--", lw=1.1); ax.plot(20, s20, "o", color=NAVY, ms=8, zorder=5)
ax.annotate(f"Top 20% carry {s20:.0f}%", (20, s20), xytext=(26, -14),
            textcoords="offset points", fontsize=9.5, color=NAVY, fontweight="bold")
ax.set_xlim(0,100); ax.set_ylim(0,102)
ax.set_xlabel("Customers ranked by revenue (%)"); ax.set_ylabel("Cumulative revenue (%)")
ax.set_title(f"Revenue concentration, {R['n_customers']:,} identified customers", loc="left")

fig.suptitle("Sales Performance Dashboard", fontsize=20, fontweight="bold", color=NAVY, y=1.030)
fig.text(0.5, 0.995, f"FactSale  ·  {R['rows_clean']:,} order lines  ·  January 2013 to May 2016"
         f"  ·  Prepared by KOUAME Koffi Fidèle",
         ha="center", fontsize=10.5, color="#555555")
fig.savefig("charts/07_dashboard.png", bbox_inches="tight")
print("charts/07_dashboard.png written")
