# Key Insights and Recommendations

**Dataset:** FactSale, 26,397 order lines, Jan 2013 to May 2016
**KOUAME Koffi Fidèle** · Data Analysis Internship

---

## Headline figures

| KPI | Value | Why it is on this list |
| :--- | ---: | :--- |
| Total sales, excl. tax | 19.88M | The top line every other figure divides into |
| Gross profit | 9.92M | Revenue that does not convert is not performance |
| Gross margin | 49.9% | The single ratio that survives a change of scale |
| Orders (invoices) | 8,188 | Distinguishes growth in volume from growth in basket |
| Average order value | 2,428 | The lever a commercial team can actually pull |
| Units sold | 1,028,670 | Detects margin bought with discount |
| Identified customers | 48 | Bounds every customer conclusion below |

## Insight 1. A third of the revenue cannot be attributed to a customer

9,077 order lines, **34.4% of the file**,
carry no customer key. Every customer metric in this study, and in any dashboard
built on this file, therefore describes two thirds of the business.

This is not a modelling limitation, it is a data capture failure upstream, and it is
the most valuable thing this analysis found. No segmentation, no lifetime value and
no retention measure can be trusted until it is closed.

**Recommendation.** Trace the 9,077 unattributed lines back to
their source system and establish why the key is absent. If they are counter sales
with no account, create a customer record for them. Until then, every customer
figure must be published with the coverage rate beside it.

## Insight 2. Products are concentrated, customers are not

Two concentration measures point in opposite directions, and the difference is the
finding.

**Products are concentrated.** The top 10 items carry **32.8%** of
revenue out of 227 distinct products. A small part of
the catalogue does most of the work.

**Customers are not.** Among the 48 identified customers, the top 20%
carry only **25%** of identified revenue. Perfect
equality would be 20%. The revenue is spread almost evenly across the account base,
which is the opposite of the Pareto pattern most retail businesses show.

That is unusual and it cuts both ways. There is **no key-account dependency**, so no
single customer loss threatens the top line. But there is also no high-value segment
to build a retention programme around, and the absence of a natural top tier means
account-based selling has nothing to target.

**Recommendation.** Do not build a key-account programme on this base, because the
data says there are no key accounts. Concentrate commercial effort on the product
side, where 33% of revenue sits in ten items, and protect the
availability and margin of those ten before anything else.

## Insight 3. Seasonality is real but moderate, and month 7 leads

On the complete years 2013 to 2015,
the strongest calendar month outsells the weakest by a factor of
**1.33**. Quarter 2 is the strongest.

A ratio of 1.33 is worth planning around but does not justify
large seasonal stock swings. It is a scheduling signal, not a demand shock.

**Recommendation.** Align staffing and inventory to the quarterly pattern rather
than to the monthly one, whose amplitude does not warrant the operational cost of
adjusting to it.

## Insight 4. Price and volume move against each other, weakly

The correlation between unit price and quantity ordered is
**-0.14**, and between quantity and line revenue
**0.24**.

The first is the expected negative relationship: expensive items sell in smaller
quantities. Its weakness matters more than its sign. Revenue per line is driven by
price far more than by volume, so **discounting to move volume would not recover the
revenue it gives up.**

**Recommendation.** Do not use volume discounting as a revenue lever on this
catalogue. The correlation structure says it will not work.

## Insight 5. The loss-making lines are small in value and specific in pattern

566 lines return a negative margin, costing
40,502. Against total profit of
9.92M this is **0.41%**,
too small to be a strategic problem.

Reporting it as a headline would be an error of proportion. It is a control issue,
not a commercial one.

**Recommendation.** Add an automated flag on negative-margin lines at invoicing
rather than opening a pricing review. The cost of the fix should match the size of
the problem.

---

## Two cautions for whoever uses this dashboard

**The last year is incomplete.** The file ends in May 2016. Every year-on-year
comparison must exclude it, and the dashboard shades it for that reason.

**Customer figures cover 66% of revenue.** They are
correct for the population they describe and must never be presented as covering the
business.
