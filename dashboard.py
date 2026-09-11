# -*- coding: utf-8 -*-
"""
Sales Performance Dashboard, interactive and cross-filtered
===========================================================

Produces one self-contained HTML file with a Power BI style layout: a filter rail
on the left, a KPI band across the top, and six analytical panels that all react
to the same filter selection.

How the cross-filtering works
-----------------------------
A browser cannot run pandas. Rather than ship the 26,397 raw lines and aggregate
them in JavaScript, this script PRECOMPUTES every panel for every reachable
filter state (all years plus each year, crossed with all months plus each month)
and serialises the result to a compact JSON payload. The JavaScript then only has
to look up a key and call Plotly.react, which is instant.

The trade-off is stated because it is a real one: the payload is larger than a
raw extract would be for a small dataset, and far smaller for a large one. At
26,397 lines it is roughly 300 KB, which loads instantly from disk.

INPUT   data/FactSale_clean.csv, results/quality_report.json
OUTPUT  dashboard.html
"""
import json
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- palette
# Light executive theme. Colour is used sparingly and always to carry meaning:
#   BLUE    the default series and the primary accent
#   TEAL    the secondary series, used when two measures share one panel
#   AMBER   reserved for the value that needs attention
#   PURPLE  used once, on the data quality card, so quality never blends into
#           performance
# The charts themselves stay on the blue and teal pair. The other two hues
# appear only on the KPI icons and the summary cards, where they label a
# section rather than encode a quantity.
NAVY   = "#12395E"   # headers and titles
BLUE   = "#1F6FB2"   # primary series
TEAL   = "#17A2A2"   # secondary series
LIGHT  = "#7EB6DD"   # context series
AMBER  = "#E08A1E"   # attention
PURPLE = "#6B4FA8"   # data quality section only
GREEN  = "#1E9E6A"   # positive delta
RED    = "#C0392B"   # negative delta
PANEL, BORDER, PAGE = "#FFFFFF", "#E2E8F0", "#F4F7FA"
TEXT, SUBTLE, GRIDC = "#1E293B", "#64748B", "#E8EEF4"
FILL = "rgba(31,111,178,0.14)"

df = pd.read_csv("data/FactSale_clean.csv", parse_dates=["invoice_date"])
R  = json.load(open("results/quality_report.json"))
S  = "Total Excluding Tax"
LAST_FULL = int(R["last_full_year"])
YEARS  = sorted(int(y) for y in df.year.unique())
MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]


def panels(d):
    """Compute every panel for one filtered slice of the data.

    INPUT  : d, a subset of df
    METHOD : the same seven aggregations used throughout the study
    OUTPUT : a dict of plain lists, ready to serialise to JSON
    """
    if len(d) == 0:
        return None

    sales, profit = float(d[S].sum()), float(d["Profit"].sum())
    orders = int(d["WWI Invoice ID"].nunique())

    # Trend. Daily when a single month is selected, monthly otherwise, so the
    # line never collapses to a single point.
    freq = "D" if d.invoice_date.dt.to_period("M").nunique() <= 1 else "MS"
    t = (d.set_index("invoice_date")
           .resample(freq).agg(sales=(S, "sum"), profit=("Profit", "sum"))
           .reset_index())

    # Package mix, as a share.
    pk = (d.groupby("Package", observed=True)
            .agg(sales=(S, "sum"), profit=("Profit", "sum")))
    pk = pk[pk.sales > 0]

    prod_s = d.groupby("Description")[S].sum().sort_values(ascending=False).head(8)
    prod_p = d.groupby("Description")["Profit"].sum().sort_values(ascending=False).head(8)

    # Registered against unknown customer, the audit finding made visible.
    flag = d.groupby(d.has_customer.map({True: "Registered", False: "Unknown"}))[S].sum()

    cust = (d[d.has_customer].groupby("Customer Key")
              .agg(sales=(S, "sum"), orders=("WWI Invoice ID", "nunique"))
              .sort_values("sales", ascending=False).head(8))

    return {
        "kpi": {"sales": sales, "profit": profit,
                "margin": 100 * profit / sales if sales else 0,
                "qty": int(d.Quantity.sum()), "orders": orders,
                "aov": sales / orders if orders else 0,
                "lines": int(len(d))},
        "trend": {"x": t.invoice_date.dt.strftime("%Y-%m-%d").tolist(),
                  "sales": t.sales.round(0).tolist(),
                  "profit": t.profit.round(0).tolist()},
        "pkg":   {"labels": pk.index.astype(str).tolist(),
                  "values": pk.sales.round(0).tolist()},
        "prodS": {"labels": [x[:36] for x in prod_s.index[::-1]],
                  "full":   prod_s.index[::-1].tolist(),
                  "values": prod_s.values[::-1].round(0).tolist()},
        "prodP": {"labels": [x[:36] for x in prod_p.index[::-1]],
                  "full":   prod_p.index[::-1].tolist(),
                  "values": prod_p.values[::-1].round(0).tolist()},
        "flag":  {"labels": flag.index.tolist(), "values": flag.round(0).tolist()},
        "cust":  {"labels": cust.index.astype(str)[::-1].tolist(),
                  "values": cust.sales.values[::-1].round(0).tolist(),
                  "orders": cust.orders.values[::-1].tolist()},
    }


# ---- precompute every filter state ----------------------------------------
# Year-on-year deltas. A KPI without a comparison is a number, not a signal, so
# each yearly state carries its change against the same period one year earlier.
# The delta is suppressed for 2016, which is incomplete: comparing five months
# against twelve would report a collapse that did not happen.
def add_yoy(state, cur, prev, complete):
    if state is None:
        return None
    if prev is None or not complete:
        state["yoy"] = None
        return state
    d = {}
    for m in ["sales", "profit", "orders", "margin"]:
        a, b = cur["kpi"][m], prev["kpi"][m]
        d[m] = None if not b else round(100 * (a - b) / abs(b), 1)
    state["yoy"] = d
    return state


DATA = {"all|all": panels(df)}
DATA["all|all"]["yoy"] = None
for y in YEARS:
    cur = panels(df[df.year == y])
    prev = panels(df[df.year == y - 1]) if (y - 1) in YEARS else None
    # A year is complete when it is not the truncated final year.
    DATA[f"{y}|all"] = add_yoy(cur, cur, prev, complete=(y <= LAST_FULL))
for m in range(1, 13):
    st = panels(df[df.month == m])
    if st is not None:
        st["yoy"] = None
    DATA[f"all|{m}"] = st
    for y in YEARS:
        cur = panels(df[(df.year == y) & (df.month == m)])
        prev = panels(df[(df.year == y - 1) & (df.month == m)]) if (y - 1) in YEARS else None
        # A single month is always complete, so the comparison is valid.
        DATA[f"{y}|{m}"] = add_yoy(cur, cur, prev, complete=True)
DATA = {k: v for k, v in DATA.items() if v is not None}
payload = json.dumps(DATA, separators=(",", ":"))
print(f"{len(DATA)} filter states precomputed, payload {len(payload)/1024:.0f} KB")


# =============================================================================
# HTML SHELL
# -----------------------------------------------------------------------------
# Layout: a header band, a navigation rail, a KPI band, a chart grid, and a
# closing row of three summary cards. Each chart lives in its own div, so a long
# category label cannot overflow into a neighbouring panel, which is the failure
# mode of a shared subplot canvas.
#
# The closing row is not decoration. A dashboard that shows only charts leaves
# the reader to infer the conclusion; these three cards state it, state what to
# do about it, and state what the data will and will not support.
# =============================================================================
v = R["validation"]
iq = R["iqr"]["Total Excluding Tax"]

year_opts = "".join(f'<option value="{y}">{y}</option>' for y in YEARS)
month_opts = "".join(f'<option value="{i+1}">{m}</option>' for i, m in enumerate(MONTHS))

ICONS = {  # inline SVG, so the page needs no icon font and works offline
 "sales": '<svg viewBox="0 0 24 24"><path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
 "orders": '<svg viewBox="0 0 24 24"><path d="M3 3h18v18H3z"/><path d="M3 9h18M9 21V9"/></svg>',
 "profit": '<svg viewBox="0 0 24 24"><path d="M3 17l6-6 4 4 8-8"/><path d="M21 7v6h-6"/></svg>',
 "margin": '<svg viewBox="0 0 24 24"><circle cx="7" cy="7" r="3"/><circle cx="17" cy="17" r="3"/><path d="M19 5L5 19"/></svg>',
 "qty":   '<svg viewBox="0 0 24 24"><path d="M21 16V8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 22V13"/></svg>',
 "aov":   '<svg viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="13" rx="2"/><path d="M2 10h20"/></svg>',
}

KPI_DEFS = [("sales",  "Total Sales",       "sales",  BLUE),
            ("orders", "Total Orders",      "orders", TEAL),
            ("profit", "Total Profit",      "profit", PURPLE),
            ("margin", "Profit Margin",     "margin", AMBER),
            ("qty",    "Total Quantity",    "qty",    BLUE),
            ("aov",    "Avg Invoice Value", "aov",    TEAL)]

kpi_html = "".join(
    f'''<div class="kpi">
      <div class="kicon" style="background:{col}18;color:{col}">{ICONS[icon]}</div>
      <div class="kbody">
        <div class="klab">{lab}</div>
        <div class="kval" id="k_{key}">-</div>
        <div class="kdelta" id="d_{key}"></div>
      </div></div>'''
    for key, lab, icon, col in KPI_DEFS)

NAV = ["Overview", "Trend", "Product mix", "Customers", "Data quality"]
nav_html = "".join(
    f'''<a class="nav{" on" if i == 0 else ""}" href="#sec{i}">{n}</a>'''
    for i, n in enumerate(NAV))

INSIGHTS = [
 f"Revenue is concentrated in products but not in customers: the top ten items carry "
 f"{R['top10_share']:.0f}% of sales, while the top fifth of accounts carry only "
 f"{R['top20pct_customer_share']:.0f}%, against 20% under perfect equality.",
 f"{v['customer_key_zero_pct']}% of order lines carry no customer key, so every "
 f"customer figure on this page describes two thirds of the business.",
 f"Seasonality is real but moderate: the strongest calendar month outsells the "
 f"weakest by a factor of {R['season_ratio']:.2f} on complete years.",
 f"Price and quantity move against each other only weakly (r = {R['corr_price_qty']:.2f}), "
 f"so revenue per line is driven by price far more than by volume.",
]
RECS = [
 "Trace the unattributed order lines back to their source system. Until that gap is "
 "closed, no segmentation or lifetime value measure can be trusted.",
 "Do not build a key-account programme on this base. The concentration curve says "
 "there are no key accounts; concentrate effort on the ten leading products instead.",
 "Do not use volume discounting as a revenue lever. The correlation structure says it "
 "will not recover the revenue it gives up.",
 f"Flag negative-margin lines automatically at invoicing. At "
 f"{100*abs(v['profit_lt_0_amount'])/R['kpi']['Total profit']:.2f}% of profit this is a "
 "control issue, not a reason to reopen pricing.",
]
QUALITY = [
 ("Total records",          f"{R['rows_raw']:,}",              "ok"),
 ("Duplicates found",       f"{R['dup_full']}",                "ok"),
 ("Invalid dates",          f"{R['date_audit']['Invoice Date Key']['unparsed_non_null']}", "ok"),
 ("Arithmetic breaches",    f"{v['qty_x_price_vs_total'] + v['tax_rule'] + v['total_rule']}", "ok"),
 ("Missing delivery dates", f"{R['delivery_missing']} (kept, not imputed)", "warn"),
 ("Unidentified customers", f"{v['customer_key_zero']:,} ({v['customer_key_zero_pct']}%)", "warn"),
 ("Negative profit lines",  f"{v['profit_lt_0']:,} (business exception)", "warn"),
 ("Rows deleted",           "0",                               "ok"),
]

ins_html = "".join(f'<li>{t}</li>' for t in INSIGHTS)
rec_html = "".join(f'<li>{t}</li>' for t in RECS)
qual_html = "".join(
    f'<div class="qrow"><span class="qlab">{l}</span>'
    f'<span class="qval {c}">{v_}</span></div>' for l, v_, c in QUALITY)

HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sales Performance Dashboard | KOUAME Koffi Fidele</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{--navy:__NAVY__;--blue:__BLUE__;--teal:__TEAL__;--amber:__AMBER__;
      --purple:__PURPLE__;--green:__GREEN__;--red:__RED__;
      --panel:__PANEL__;--bd:__BORDER__;--page:__PAGE__;--tx:__TEXT__;--sub:__SUBTLE__;}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--tx);
     font-family:"Segoe UI",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}

/* ---- header ---- */
.top{background:var(--navy);color:#fff;padding:16px 26px;display:flex;
     align-items:center;gap:22px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:14px;flex:1;min-width:320px}
.logo{width:38px;height:38px;flex:none}
.logo rect{fill:#fff}
.top h1{margin:0;font-size:25px;font-weight:700;letter-spacing:.2px}
.tag{font-size:12.5px;color:#A9C6DF;margin-top:3px}
.tag b{color:#fff;font-weight:600}
.ctrl{display:flex;align-items:center;gap:16px}
.fld label{display:block;font-size:10.5px;letter-spacing:.9px;text-transform:uppercase;
           color:#A9C6DF;margin-bottom:4px}
.fld select{background:#fff;border:1px solid #D6E2ED;border-radius:7px;padding:7px 11px;
            font-size:13px;color:var(--tx);font-family:inherit;min-width:132px;cursor:pointer}
.src{border-left:1px solid #2F5madeup;padding-left:18px;font-size:12px;color:#A9C6DF;
     border-left:1px solid #2F5678}
.src b{display:block;color:#fff;font-size:13.5px}

/* ---- shell ---- */
.wrap{display:grid;grid-template-columns:186px 1fr;gap:18px;padding:18px 22px 40px;
      max-width:1800px;margin:0 auto}
.rail{position:sticky;top:18px;align-self:start;background:var(--panel);
      border:1px solid var(--bd);border-radius:12px;padding:9px;display:flex;
      flex-direction:column;gap:2px}
.nav{padding:10px 13px;border-radius:8px;font-size:13.5px;color:#475569;
     text-decoration:none;transition:all .13s}
.nav:hover{background:#EFF5FA;color:var(--navy)}
.nav.on{background:#E4EFF8;color:var(--navy);font-weight:600}

/* ---- KPI cards ---- */
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin-bottom:18px}
.kpi{background:var(--panel);border:1px solid var(--bd);border-radius:12px;
     padding:15px 14px;display:flex;gap:12px;align-items:flex-start;
     transition:transform .14s,box-shadow .14s}
.kpi:hover{transform:translateY(-3px);box-shadow:0 6px 18px rgba(18,57,94,.10)}
.kicon{width:38px;height:38px;border-radius:10px;flex:none;display:flex;
       align-items:center;justify-content:center}
.kicon svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:2;
           stroke-linecap:round;stroke-linejoin:round}
.kbody{min-width:0}
.klab{font-size:11.5px;color:var(--sub);font-weight:600}
.kval{font-size:22px;font-weight:700;color:var(--navy);line-height:1.2;margin-top:3px}
.kdelta{font-size:11.5px;margin-top:3px;color:var(--sub)}
.up{color:var(--green);font-weight:600} .down{color:var(--red);font-weight:600}

/* ---- panels ---- */
h2.sect{font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--navy);
        margin:22px 0 11px;padding-bottom:7px;border-bottom:1px solid var(--bd)}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:12px;
      padding:6px 13px 11px;transition:box-shadow .14s}
.card:hover{box-shadow:0 5px 16px rgba(18,57,94,.08)}
.c2{grid-column:span 2}
.note{margin:6px 4px 0;font-size:11.5px;color:#64748B;line-height:1.55}
.note b{color:var(--navy)}

/* ---- closing summary row ---- */
.sum{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;margin-top:16px}
.sc{background:var(--panel);border:1px solid var(--bd);border-radius:12px;overflow:hidden}
.sh{padding:12px 18px;color:#fff;font-size:13.5px;font-weight:600;
    display:flex;align-items:center;gap:9px}
.sh svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2;
        stroke-linecap:round;stroke-linejoin:round}
.h-ins{background:var(--navy)} .h-rec{background:var(--teal)} .h-qua{background:var(--purple)}
.sb{padding:13px 18px 16px}
.sb ol{margin:0;padding-left:20px;font-size:12.5px;line-height:1.65;color:#334155}
.sb ol li{margin-bottom:9px}
.sb ol li::marker{color:var(--blue);font-weight:700}
.qrow{display:flex;justify-content:space-between;gap:10px;padding:7px 0;
      border-bottom:1px solid #F1F5F9;font-size:12.5px}
.qrow:last-child{border-bottom:none}
.qlab{color:#475569} .qval{font-weight:600;text-align:right}
.qval.ok{color:var(--green)} .qval.warn{color:var(--amber)}
.qfoot{margin-top:11px;background:#EAF6F0;border:1px solid #BFE3D2;border-radius:8px;
       padding:9px 12px;font-size:12px;color:#14724E}

footer{margin-top:22px;padding-top:14px;border-top:1px solid var(--bd);
       font-size:11.5px;color:var(--sub)}
@media(max-width:1350px){.grid,.sum{grid-template-columns:1fr 1fr}.c2{grid-column:span 2}
  .kpis{grid-template-columns:repeat(3,1fr)}}
@media(max-width:900px){.wrap{grid-template-columns:1fr}.rail{position:static;
  flex-direction:row;flex-wrap:wrap}.grid,.sum{grid-template-columns:1fr}
  .c2{grid-column:span 1}.kpis{grid-template-columns:repeat(2,1fr)}}
</style></head><body>

<div class="top">
  <div class="brand">
    <svg class="logo" viewBox="0 0 24 24"><rect x="2" y="12" width="5" height="10" rx="1"/>
      <rect x="9.5" y="6" width="5" height="16" rx="1"/><rect x="17" y="2" width="5" height="20" rx="1"/></svg>
    <div><h1>Sales Performance Dashboard</h1>
      <div class="tag"><b>Clean data</b> &nbsp;|&nbsp; <b>Validated figures</b>
        &nbsp;|&nbsp; <b>Stated limits</b></div></div>
  </div>
  <div class="ctrl">
    <div class="fld"><label>Year</label>
      <select id="fy"><option value="all">All years</option>__YEARS__</select></div>
    <div class="fld"><label>Month</label>
      <select id="fm"><option value="all">All months</option>__MONTHS__</select></div>
    <div class="src">Source<b>FactSale.csv</b>(__ROWS__ records)</div>
  </div>
</div>

<div class="wrap">
  <aside class="rail">__NAV__</aside>

  <section>
    <div class="kpis">__KPIS__</div>

    <h2 class="sect" id="sec1">Trend</h2>
    <div class="grid">
      <div class="card c2"><div id="p_trend"></div>
        <p class="note">Daily resolution when one month is selected, monthly otherwise, so
        the line never collapses to a single point. <b>2016 stops in May</b>, so exclude it
        from any year-on-year reading.</p></div>
      <div class="card"><div id="p_year"></div>
        <p class="note">Annual comparison. The final bar covers five months only and is
        labelled accordingly.</p></div>
    </div>

    <h2 class="sect" id="sec2">Product mix</h2>
    <div class="grid">
      <div class="card"><div id="p_pkg"></div>
        <p class="note">Share of revenue by package type. One type carries the large
        majority, which is why the share matters more than the absolute value.</p></div>
      <div class="card c2"><div id="p_prodS"></div>
        <p class="note">Ranked by revenue. The profit ranking is a different list, shown
        below, and a product high here but absent there is selling volume without
        converting it.</p></div>
    </div>

    <h2 class="sect" id="sec3">Customers</h2>
    <div class="grid">
      <div class="card"><div id="p_flag"></div>
        <p class="note">The audit finding made visual: the grey arc is revenue that cannot
        be attributed to any customer.</p></div>
      <div class="card"><div id="p_cust"></div>
        <p class="note">Identified customers only. Hover for the order count behind each
        revenue figure.</p></div>
      <div class="card"><div id="p_prodP"></div>
        <p class="note">Top products by profit, for comparison with the revenue ranking
        above.</p></div>
    </div>

    <h2 class="sect" id="sec4">Conclusions</h2>
    <div class="sum">
      <div class="sc"><div class="sh h-ins">
        <svg viewBox="0 0 24 24"><path d="M9 18h6M10 22h4"/><path d="M12 2a7 7 0 00-4 12.7V17h8v-2.3A7 7 0 0012 2z"/></svg>
        Key insights</div>
        <div class="sb"><ol>__INS__</ol></div></div>

      <div class="sc"><div class="sh h-rec">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></svg>
        Recommendations</div>
        <div class="sb"><ol>__REC__</ol></div></div>

      <div class="sc"><div class="sh h-qua">
        <svg viewBox="0 0 24 24"><path d="M12 2l8 4v6c0 5-3.4 8.9-8 10-4.6-1.1-8-5-8-10V6z"/><path d="M9 12l2 2 4-4"/></svg>
        Data quality summary</div>
        <div class="sb">__QUAL__
          <div class="qfoot">No row was deleted. A standard outlier screen would have
          removed __IQR__% of all revenue, so it was computed and deliberately not
          applied.</div></div></div>
    </div>

    <footer>Source: FactSale, cleaned by <code>analysis.py</code>. Full audit in
      DATA_QUALITY.md, conclusions in INSIGHTS.md, formal report in report.pdf.
      &nbsp;&middot;&nbsp; KOUAME Koffi Fidele &nbsp;&middot;&nbsp; koffifidelek59@gmail.com</footer>
  </section>
</div>

<script>
const DATA=__PAYLOAD__, MONTHS=__MONTHNAMES__;
const NAVY="__NAVY__",BLUE="__BLUE__",TEAL="__TEAL__",LIGHT="__LIGHT__",
      AMBER="__AMBER__",PANEL="__PANEL__",TX="__TEXT__",SUB="__SUBTLE__",
      GR="__GRIDC__",FILL="__FILL__";
const YEARLY=__YEARLY__;

/* Shared layout, defined once so no panel can drift from the others. */
function L(t,x){return Object.assign({
  title:{text:"<b>"+t+"</b>",x:0.01,xanchor:"left",font:{size:13.5,color:NAVY}},
  paper_bgcolor:PANEL,plot_bgcolor:PANEL,
  font:{family:"Segoe UI,Arial",size:11.5,color:TX},
  margin:{t:44,b:38,l:56,r:18},height:262,showlegend:false,
  xaxis:{gridcolor:GR,zeroline:false,linecolor:"#CBD5E1",tickfont:{color:SUB,size:10.5}},
  yaxis:{gridcolor:GR,zeroline:false,linecolor:"#CBD5E1",tickfont:{color:SUB,size:10.5}},
  hoverlabel:{bgcolor:"#fff",bordercolor:BLUE,font:{color:TX,size:12}}},x||{});}
const CFG={displaylogo:false,responsive:true,displayModeBar:false};
const fmt=v=>Math.abs(v)>=1e6?(v/1e6).toFixed(2)+"M":Math.abs(v)>=1e3?
            (v/1e3).toFixed(1)+"K":Math.round(v).toLocaleString();

function setDelta(id,val,suffix){
  const el=document.getElementById(id);
  if(val===null||val===undefined){el.innerHTML='<span style="opacity:.75">no comparable period</span>';return;}
  const up=val>=0;
  el.innerHTML='<span class="'+(up?"up":"down")+'">'+(up?"\\u25B2 ":"\\u25BC ")+
    Math.abs(val).toFixed(1)+(suffix||"%")+'</span> vs previous year';
}

function draw(d){
  const k=d.kpi,y=d.yoy;
  document.getElementById("k_sales").textContent=fmt(k.sales);
  document.getElementById("k_orders").textContent=k.orders.toLocaleString();
  document.getElementById("k_profit").textContent=fmt(k.profit);
  document.getElementById("k_margin").textContent=k.margin.toFixed(1)+"%";
  document.getElementById("k_qty").textContent=fmt(k.qty);
  document.getElementById("k_aov").textContent=Math.round(k.aov).toLocaleString();
  setDelta("d_sales", y?y.sales:null); setDelta("d_orders", y?y.orders:null);
  setDelta("d_profit", y?y.profit:null); setDelta("d_margin", y?y.margin:null);
  setDelta("d_qty", null); setDelta("d_aov", null);

  Plotly.react("p_trend",[
   {x:d.trend.x,y:d.trend.sales,type:"scatter",mode:"lines",name:"Sales",
    line:{color:BLUE,width:2.4},fill:"tozeroy",fillcolor:FILL,
    hovertemplate:"<b>%{x}</b><br>Sales %{y:,.0f}<extra></extra>"},
   {x:d.trend.x,y:d.trend.profit,type:"scatter",mode:"lines+markers",name:"Profit",
    line:{color:TEAL,width:2.2},marker:{size:4},
    hovertemplate:"<b>%{x}</b><br>Profit %{y:,.0f}<extra></extra>"}],
   L("Monthly sales and profit trend",{showlegend:true,height:300,
     legend:{orientation:"h",y:1.12,x:0,font:{color:SUB,size:10.5}}}),CFG);

  Plotly.react("p_year",[
   {x:YEARLY.years,y:YEARLY.sales,type:"bar",name:"Sales",
    marker:{color:YEARLY.years.map(v=>v==YEARLY.partial?LIGHT:BLUE)},
    hovertemplate:"<b>%{x}</b><br>Sales %{y:,.0f}<extra></extra>"},
   {x:YEARLY.years,y:YEARLY.profit,type:"bar",name:"Profit",marker:{color:TEAL},
    hovertemplate:"<b>%{x}</b><br>Profit %{y:,.0f}<extra></extra>"}],
   L("Annual sales and profit",{height:300,barmode:"group",showlegend:true,
     legend:{orientation:"h",y:1.12,x:0,font:{color:SUB,size:10.5}},
     annotations:[{x:YEARLY.partial,y:YEARLY.sales[YEARLY.years.indexOf(YEARLY.partial)],
       text:"5 months only",showarrow:true,arrowhead:0,ax:0,ay:-26,
       font:{color:AMBER,size:10.5}}]}),CFG);

  Plotly.react("p_pkg",[{labels:d.pkg.labels,values:d.pkg.values,type:"pie",hole:.6,
   marker:{colors:[BLUE,TEAL,LIGHT,AMBER],line:{color:"#fff",width:2}},
   textinfo:"percent",textfont:{size:11,color:"#fff"},sort:true,
   hovertemplate:"<b>%{label}</b><br>%{value:,.0f}<br>%{percent}<extra></extra>"}],
   L("Sales by package type",{height:300,showlegend:true,
     legend:{orientation:"v",x:1,y:.5,font:{color:SUB,size:10.5}},
     margin:{t:44,b:20,l:14,r:14}}),CFG);

  Plotly.react("p_flag",[{labels:d.flag.labels,values:d.flag.values,type:"pie",hole:.6,
   marker:{colors:d.flag.labels.map(l=>l==="Registered"?BLUE:"#94A3B8"),
           line:{color:"#fff",width:2}},
   textinfo:"percent",textfont:{size:11,color:"#fff"},sort:false,
   hovertemplate:"<b>%{label}</b><br>%{value:,.0f}<br>%{percent}<extra></extra>"}],
   L("Revenue by customer identification",{height:300,showlegend:true,
     legend:{orientation:"v",x:1,y:.5,font:{color:SUB,size:10.5}},
     margin:{t:44,b:20,l:14,r:14}}),CFG);

  const bar=(id,p,t,c,lm)=>Plotly.react(id,[{y:p.labels,x:p.values,type:"bar",
   orientation:"h",marker:{color:c},text:p.values.map(fmt),textposition:"outside",
   textfont:{color:SUB,size:10.5},cliponaxis:false,customdata:p.full||p.labels,
   hovertemplate:"<b>%{customdata}</b><br>%{x:,.0f}<extra></extra>"}],
   L(t,{height:300,margin:{t:44,b:38,l:lm,r:56},
     yaxis:{gridcolor:"rgba(0,0,0,0)",tickfont:{color:SUB,size:10}}}),CFG);
  bar("p_prodS",d.prodS,"Top products by revenue",BLUE,205);
  bar("p_prodP",d.prodP,"Top products by profit",TEAL,205);

  Plotly.react("p_cust",[{y:d.cust.labels,x:d.cust.values,type:"bar",orientation:"h",
   marker:{color:BLUE},customdata:d.cust.orders,text:d.cust.values.map(fmt),
   textposition:"outside",textfont:{color:SUB,size:10.5},cliponaxis:false,
   hovertemplate:"<b>Customer %{y}</b><br>Sales %{x:,.0f}<br>Orders %{customdata}<extra></extra>"}],
   L("Top customers by revenue",{height:300,margin:{t:44,b:38,l:66,r:56},
     yaxis:{gridcolor:"rgba(0,0,0,0)",tickfont:{color:SUB,size:10.5}}}),CFG);
}

function apply(){
  const y=document.getElementById("fy").value,m=document.getElementById("fm").value;
  const d=DATA[y+"|"+m];
  if(!d){alert("No orders in "+(m==="all"?"":MONTHS[m-1]+" ")+y+". Showing all years.");
    document.getElementById("fy").value="all";document.getElementById("fm").value="all";
    draw(DATA["all|all"]);return;}
  draw(d);
}
document.getElementById("fy").addEventListener("change",apply);
document.getElementById("fm").addEventListener("change",apply);
document.querySelectorAll(".nav").forEach(a=>a.addEventListener("click",e=>{
  document.querySelectorAll(".nav").forEach(x=>x.classList.remove("on"));
  e.target.classList.add("on");}));
apply();
</script></body></html>"""

# Annual totals for the comparison panel, computed once outside the filter states.
_yr = df.groupby("year").agg(sales=(S, "sum"), profit=("Profit", "sum"))
YEARLY = {"years": [str(y) for y in _yr.index],
          "sales": _yr.sales.round(0).tolist(),
          "profit": _yr.profit.round(0).tolist(),
          "partial": str(int(_yr.index.max()))}

HTML = (HTML.replace("__NAVY__", NAVY).replace("__BLUE__", BLUE).replace("__TEAL__", TEAL)
            .replace("__LIGHT__", LIGHT).replace("__AMBER__", AMBER)
            .replace("__PURPLE__", PURPLE).replace("__GREEN__", GREEN).replace("__RED__", RED)
            .replace("__PANEL__", PANEL).replace("__BORDER__", BORDER).replace("__PAGE__", PAGE)
            .replace("__TEXT__", TEXT).replace("__SUBTLE__", SUBTLE).replace("__GRIDC__", GRIDC)
            .replace("__FILL__", FILL)
            .replace("__YEARS__", year_opts).replace("__MONTHS__", month_opts)
            .replace("__NAV__", nav_html).replace("__KPIS__", kpi_html)
            .replace("__INS__", ins_html).replace("__REC__", rec_html)
            .replace("__QUAL__", qual_html)
            .replace("__ROWS__", f"{R['rows_clean']:,}")
            .replace("__IQR__", str(iq["revenue_share"]))
            .replace("__MONTHNAMES__", json.dumps(MONTHS))
            .replace("__YEARLY__", json.dumps(YEARLY))
            .replace("__PAYLOAD__", payload))
HTML = HTML.replace("#2F5madeup", "#2F5678")

open("dashboard.html", "w", encoding="utf-8").write(HTML)
print(f"dashboard.html written, {len(HTML)/1024:.0f} KB, "
      f"{len(DATA)} filter states, 6 cross-filtered panels")
