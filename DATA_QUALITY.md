# Data Quality Report

**Dataset:** `FactSale.csv` · **KOUAME Koffi Fidèle** · Data Analysis Internship

---

## 1. Summary

The file contains **26,397 order lines** across 21 columns,
covering invoices from January 2013 to May 2016.

The brief anticipates a dirty file: impossible calendar dates such as 31 February,
duplicate rows, missing values, broken arithmetic. **Each of those was tested
explicitly, and most of them are not present.** The findings below report what the
file actually contains, not what a checklist expects.

The genuine risks in this dataset are not arithmetic. They are two structural
features that would corrupt an analysis built without noticing them, and one
statistical trap that a routine outlier procedure walks straight into.

## 2. Checks that passed

| Check | Result |
| :--- | ---: |
| Duplicate rows, full record | **0** |
| Duplicate business keys (invoice, item, date, qty, price) | **0** |
| Duplicate `Sale Key` | **0** |
| Impossible or unparseable invoice dates | **0** |
| `Quantity × Unit Price ≠ Total Excluding Tax` | **0** |
| `Total Excl. × Tax Rate ÷ 100 ≠ Tax Amount` | **0** |
| `Total Excl. + Tax ≠ Total Including Tax` | **0** |
| Quantity ≤ 0 | **0** |
| Unit price ≤ 0 | **0** |
| Negative sales | **0** |
| Delivery date before invoice date | **0** |

Every arithmetic relationship in the file holds to within one cent. The dates parse
without exception under `%m/%d/%Y`. No row was removed for any of these reasons.

## 3. Issues found, and how each was handled

### 3.1 Unidentified customers: 9,077 lines, 34.4% of the file

**The most consequential defect.** `Customer Key` is zero on
9,077 of 26,397 lines. Zero is not a customer; it is
a placeholder for a sale that was never mapped to one.

**Handling:** the rows are **kept** for every revenue, product and time analysis,
because their financial fields are complete and removing them would delete a third
of the revenue. They are **excluded** from customer analysis only, through an
explicit `has_customer` flag rather than a silent filter.

**Impact:** every customer figure in this study describes the
34.4%-smaller identified population, and says so. Any
customer metric computed over the whole file without this distinction would be
wrong by construction.

### 3.2 The final year is incomplete: 2016 covers January to May only

**A trap rather than an error.** The file ends on 2016-05-31.
Any year-on-year chart built without noticing this shows a collapse in 2016 that is
an artefact of the extraction date, not a business event.

**Handling:** seasonality and any month-on-month comparison are computed on the
complete years 2013 to 2015 only. The
incomplete period is shaded in every time series so a reader cannot mistake it.

### 3.3 Missing delivery dates: 13 lines

13 lines carry no delivery date, that is
0.05% of the file.

**Handling: not imputed.** The delivery date feeds a delivery-lag metric. An imputed
date would manufacture a lag that never occurred, which is worse than a gap. The
rows are retained, since every revenue field on them is intact, and the lag metric
is computed on the 26,384 lines that have one.

### 3.4 Loss-making lines: 566 lines

566 lines return a negative profit, totalling
40,502 in lost margin.

**Handling: kept.** These are not data errors. A negative margin on a real sale is a
commercial event, and it is one of the more actionable findings in the file.
Removing them as outliers would inflate total profit and conceal the problem.

### 3.5 High unit prices: 113 lines

113 lines carry a unit price above 1,000, which the brief suggests
treating as aberrant.

**Handling: kept, after inspection.** Every one of them is the same product family,
an air cushion machine priced at 1,899. The price is consistent across all its
lines, the quantities are plausible, and the arithmetic holds. This is an expensive
product, not a typing error. Deleting it would remove a legitimate high-value
segment.

## 4. The outlier trap

An IQR screen at 1.5 times the interquartile range flags:

| Field | Lines flagged | Share of lines | Share of revenue |
| :--- | ---: | ---: | ---: |
| Total Excluding Tax | 2,337 | 8.9% | **48.0%** |
| Unit Price | 2,742 | 10.4% | 39.4% |
| Quantity | 1,589 | 6.0% | 4.7% |

**The screen was computed and deliberately not applied.** Removing the lines it
flags on Total Excluding Tax would delete
**48.0% of all revenue**, and those lines are
the large legitimate orders that a sales analysis exists to explain.

The IQR rule assumes an approximately symmetric distribution. Sales value is
strongly right-skewed by construction, because a few large orders always exist.
Applying a symmetric rule to a skewed variable does not remove errors, it removes
the top of the distribution.

## 5. Conclusion

No row was deleted. 26,397 of 26,397 lines are retained.

The cleaning performed consists of type conversion, date parsing, whitespace
trimming, category encoding and the derivation of the analysis fields. The
substantive work was not repair but **diagnosis**: establishing that the arithmetic
is sound, that a third of the file has no customer, that the last year is partial,
and that the standard outlier procedure would have destroyed a tenth of the revenue.

Each of those four facts changes how the analysis must be built, and none of them is
visible in a summary table.
