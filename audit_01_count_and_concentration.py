"""
Customer base audit, part 1: the count, and the concentration that depends on it.

Run:  python audit_01_count_and_concentration.py

Concentration leads, per the service description: revenue resting on a few customers is a risk
the multiple should price. But concentration is a SHARE, and a share needs a denominator, which
is the count nobody has agreed on. That dependency is the spine of the talk.

Prints numbers only. No conclusions. The reasoning goes in the deck.
"""
import pandas as pd

AS_OF = pd.Timestamp("2026-08-20")

cust = pd.read_csv("billing_customers.csv", parse_dates=["first_invoice_date", "last_paid_invoice_date"])
inv = pd.read_csv("billing_invoices.csv", parse_dates=["invoice_date"])
crm = pd.read_csv("crm_accounts.csv", parse_dates=["created_date"])
use = pd.read_csv("product_usage.csv", parse_dates=["event_date"])

def rule(label, n):
    print(f"  {label:<52} {n:>6}")

print("=" * 78)
print("1. HOW MANY CUSTOMERS? Each rule is defensible. None is obviously wrong.")
print("=" * 78)

crm_active = (crm.account_status == "Active").sum()
rule("CRM account_status == 'Active'", crm_active)

# Window boundaries are INCLUSIVE (>= as_of - N days), matching SOLUTIONS.md.
# This is a choice, not a fact. See section 1b.
paid90 = inv[(inv.status == "paid") & (inv.invoice_date >= AS_OF - pd.Timedelta(days=90))]
rule("paid invoice in the last 90 days", paid90.customer_ref.nunique())

paid365 = inv[(inv.status == "paid") & (inv.invoice_date >= AS_OF - pd.Timedelta(days=365))]
rule("paid invoice in the last 365 days (annual-aware)", paid365.customer_ref.nunique())

use30 = use[use.event_date >= AS_OF - pd.Timedelta(days=30)]
rule("any product usage in the last 30 days", use30.org_slug.nunique())

mrr_live = ((crm.mrr_usd > 0) & (crm.account_status != "Churned")).sum()
rule("CRM mrr_usd > 0 and not Churned", mrr_live)

print()
print("  Spread between highest and lowest rule:",
      max(crm_active, paid90.customer_ref.nunique(), paid365.customer_ref.nunique(),
          use30.org_slug.nunique(), mrr_live)
      - min(crm_active, paid90.customer_ref.nunique(), paid365.customer_ref.nunique(),
            use30.org_slug.nunique(), mrr_live))

print()
print("  WHY THE 90-DAY RULE IS THE TRAP, quantified:")
annual = cust[cust.contract_type == "annual"]
annual_stale = annual[annual.last_paid_invoice_date < AS_OF - pd.Timedelta(days=90)]
print(f"    annual-contract billing customers                  {len(annual):>6}")
print(f"    of those, last paid MORE than 90 days ago          {len(annual_stale):>6}")
print(f"    -> excluded by a 90-day rule while fully current")

print()
print("  1b. THE SAME PROBLEM ONE LEVEL DOWN: is the window boundary inclusive?")
p_ex = inv[(inv.status == "paid") & (inv.invoice_date > AS_OF - pd.Timedelta(days=90))]
u_ex = use[use.event_date > AS_OF - pd.Timedelta(days=30)]
print(f"    paid 90d, boundary INCLUSIVE (>=)                {paid90.customer_ref.nunique():>6}")
print(f"    paid 90d, boundary EXCLUSIVE (>)                 {p_ex.customer_ref.nunique():>6}")
print(f"    usage 30d, boundary INCLUSIVE (>=)               {use30.org_slug.nunique():>6}")
print(f"    usage 30d, boundary EXCLUSIVE (>)                {u_ex.org_slug.nunique():>6}")
print("    Nobody writes this down either. It is the same failure at the smallest scale")
print("    the data can express, and it is invisible in every dashboard built on top of it.")

print()
print("=" * 78)
print("2. CONCENTRATION. The figure an acquirer prices risk off.")
print("=" * 78)

paid = inv[inv.status == "paid"].copy()
ttm = paid[paid.invoice_date > AS_OF - pd.Timedelta(days=365)]
by_cust = ttm.groupby("customer_ref").amount_usd.sum().sort_values(ascending=False)
total = by_cust.sum()

print(f"  TTM paid revenue (billing, as of {AS_OF.date()}):  ${total:,.0f}")
print(f"  paying customers in the window:                    {len(by_cust):>6}")
print()
print("  BILLING view, revenue share:")
for n in (1, 5, 10, 20, 50):
    if n <= len(by_cust):
        print(f"    top {n:<3} customers                        {by_cust.head(n).sum()/total*100:>6.1f}%")

crm_live = crm[(crm.mrr_usd > 0) & (crm.account_status != "Churned")].copy()
crm_annualized = (crm_live.mrr_usd * 12).sort_values(ascending=False)
crm_total = crm_annualized.sum()
print()
print("  CRM view, same question, annualized mrr_usd:")
print(f"    implied annual revenue                     ${crm_total:,.0f}")
print(f"    accounts counted                                 {len(crm_annualized):>6}")
for n in (1, 5, 10, 20, 50):
    if n <= len(crm_annualized):
        print(f"    top {n:<3} accounts                         {crm_annualized.head(n).sum()/crm_total*100:>6.1f}%")

print()
print(f"  REVENUE GAP between the two systems:  ${abs(crm_total-total):,.0f} "
      f"({abs(crm_total-total)/total*100:.1f}% of billing)")
print("  Both are 'revenue'. They are not the same number, and there is no shared key to reconcile them.")

print()
print("=" * 78)
print("3. THE DENOMINATOR PROBLEM, stated as a number")
print("=" * 78)
top10 = by_cust.head(10).sum()
print("  'Top 10 customers are X% of revenue' depends on which revenue you divide by:")
print(f"    top 10 / billing TTM paid                        {top10/total*100:>6.1f}%")
print(f"    top 10 / CRM annualized mrr                      {top10/crm_total*100:>6.1f}%")
print("  Same numerator. Two defensible denominators. The answer moves by percentage points,")
print("  and nothing in the data says which one is right.")
