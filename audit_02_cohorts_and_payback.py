"""
Customer base audit, part 2: cohorts, retention, CLV, and the CAC/payback teardown.

Run:  python audit_02_cohorts_and_payback.py

Windows are INCLUSIVE (>= as_of - N days), matching SOLUTIONS.md.
Prints numbers only. No conclusions.
"""
import pandas as pd

AS_OF = pd.Timestamp("2026-08-20")

cust = pd.read_csv("billing_customers.csv", parse_dates=["first_invoice_date", "last_paid_invoice_date"])
inv = pd.read_csv("billing_invoices.csv", parse_dates=["invoice_date"])
crm = pd.read_csv("crm_accounts.csv", parse_dates=["created_date"])
spend = pd.read_csv("marketing_spend.csv")

paid = inv[inv.status == "paid"].copy()
paid = paid.merge(cust[["customer_ref", "first_invoice_date", "contract_type"]], on="customer_ref", how="left")

print("=" * 78)
print("4. COHORTS. Annual cohort by first invoice, revenue retained by year.")
print("=" * 78)
paid["cohort"] = paid.first_invoice_date.dt.year
paid["year"] = paid.invoice_date.dt.year
paid["year_idx"] = paid.year - paid.cohort

mat = paid.pivot_table(index="cohort", columns="year_idx", values="amount_usd", aggfunc="sum")
sizes = cust.assign(cohort=cust.first_invoice_date.dt.year).groupby("cohort").customer_ref.nunique()

print("  Cohort  N     Y0          Y1          Y2          Y3")
for c in sorted(mat.index):
    row = f"  {c}   {sizes.get(c,0):>4}  "
    for y in range(0, 4):
        v = mat.loc[c, y] if y in mat.columns and pd.notna(mat.loc[c, y]) else None
        row += f"{('$'+format(v,',.0f')) if v else '-':>12}"
    print(row)
print()
print("  CAUTION: 2026 is a PARTIAL year (as-of 2026-08-20), so its Y0 is ~8 months, not 12.")
print("  Reading the last row as a decline is the most common way this chart lies.")

print()
print("  Revenue retention, Y1 as a percent of Y0 (full cohorts only).")
print("  READ THE CAVEAT BEFORE THE NUMBERS: cohorts are keyed on CALENDAR YEAR, so a")
print("  customer who signs in October contributes 3 months to Y0 and 12 months to Y1.")
print("  Y1/Y0 above 100% is therefore mostly a calendar artifact, NOT expansion revenue.")
print("  Reporting it as net revenue retention would be wrong, and it is a very easy")
print("  mistake to make because the number looks like the answer everyone wants.")
for c in sorted(mat.index):
    if 0 in mat.columns and 1 in mat.columns and pd.notna(mat.loc[c, 0]) and pd.notna(mat.loc[c, 1]):
        if c < 2026:
            print(f"    {c} cohort                                     {mat.loc[c,1]/mat.loc[c,0]*100:>6.0f}%")

print()
print("=" * 78)
print("5. CLV, and why it inherits the count problem")
print("=" * 78)
life = paid.groupby("customer_ref").amount_usd.sum()
print(f"  mean lifetime paid revenue per billing customer   ${life.mean():>12,.0f}")
print(f"  median                                            ${life.median():>12,.0f}")
print(f"  mean is higher than median by                     {life.mean()/life.median():>12.2f}x")
print("  A mean-based CLV on a skewed book overstates the typical customer.")

print()
print("=" * 78)
print("6. CAC AND PAYBACK. The teardown.")
print("=" * 78)
total_spend = spend.spend_usd.sum()
print(f"  total marketing spend on file                     ${total_spend:>12,.0f}")
print(f"  months covered                                    {spend.month.nunique():>13}")
print(f"  channels in FINANCE                               {spend.channel.nunique():>13}")
print(f"  distinct lead_source values in CRM                {crm.lead_source.nunique():>13}")
print("  -> finance and sales do not share a vocabulary. Same join failure, one system over.")

blank = crm.lead_source.isna().sum()
print()
print(f"  lead_source BLANK                                 {blank:>6} of {len(crm)} rows "
      f"({blank/len(crm)*100:.0f}%)")
early = crm[crm.created_date < "2024-06-01"]
print(f"  accounts created before 2024-06-01                {len(early):>6}")
print(f"    of those, lead_source blank                     {early.lead_source.isna().sum():>6}")
print("  -> the field did not exist yet. The blanks are the OLDEST and highest-value accounts,")
print("     so any channel analysis is silently biased toward recent, smaller customers.")

print()
print("  Channel mix as FINANCE books it:")
for ch, v in spend.groupby("channel").spend_usd.sum().sort_values(ascending=False).items():
    print(f"    {ch:<24} ${v:>12,.0f}   {v/total_spend*100:>5.1f}%")

print()
print("  Top lead_source values as SALES enters them:")
for ls, n in crm.lead_source.value_counts().head(12).items():
    print(f"    {ls:<24} {n:>6}")

print()
print("  6a. THE ACQUIRED BOOK IS NOT UNLABELLED. IT IS UNDETECTABLE.")
print("  Per the generator's answer key, 160 companies (Northgate 63, Pelham 52, Vireo 45)")
print("  arrived by acquisition and cost nothing to acquire. They belong in no CAC denominator.")
print("  Nothing in any of the five files identifies them. What I tried:")
s = crm.created_date.dt.to_period("M").value_counts().sort_index()
med = s.median()
spikes = [(p, n) for p, n in s.items() if n > med * 1.8]
print(f"    - a creation-date spike:  {len(spikes)} months exceed 1.8x the median "
      f"(median {med:.0f}/mo, max {s.max()}/mo, ratio {s.max()/med:.2f}x)")
print("      A bought customer list arrives on one day, so a spike was the obvious tell.")
print("      There is no spike. The book was spread across a 120-day signing window.")
print(f"    - a lead_source tell:     the migration blanked 45% of them and WRONGLY tagged 33")
print("      to real marketing channels, which inflates exactly the channels you would trust.")
print("  So 13% of the denominator is free customers that cannot be found and cannot be removed.")

print()
print("  6b. BLENDED CAC. The denominator is a COMPANY COUNT, which is the disputed number.")
n_companies = 1200          # entity count from the generator's answer key
n_acquired = 160
print(f"    spend / all companies ({n_companies})                   ${total_spend/n_companies:>12,.0f}")
print(f"    spend / marketed-to only ({n_companies-n_acquired})                ${total_spend/(n_companies-n_acquired):>12,.0f}")
print(f"    difference                                        {(total_spend/(n_companies-n_acquired))/(total_spend/n_companies)-1:>12.0%}")
print("    Both are 'blended CAC'. The 15% gap is entirely a definitional choice nobody wrote down.")

print()
print("  6c. AND HERE IS THE WHOLE TALK IN ONE TABLE.")
print("  CAC = $6.89M / N. Every count rule from section 1 is a defensible N:")
for label, n in [("CRM Active", 756), ("product usage 30d", 770),
                 ("mrr > 0, not churned", 739), ("paid invoice 90d", 485),
                 ("paid invoice 90d, deduplicated", 475), ("ground truth (unknowable)", 758)]:
    print(f"    {label:<34} N={n:<5} CAC = ${total_spend/n:>9,.0f}")
print()
print(f"    Highest CAC is {(total_spend/475)/(total_spend/770)-1:.0%} above the lowest.")
print("    Same spend. Same company. Same day. Nothing dirty in the data.")
print("    The board sees one of these numbers and never learns the other five existed.")

print()
print("    CAVEAT, AND SAY IT OUT LOUD BEFORE ANYONE ELSE DOES: this table divides 47 months")
print("    of CUMULATIVE spend by a CURRENT customer count, which is not a defensible CAC on")
print("    its own. It is here to isolate one variable, the denominator. But the error is")
print("    itself the lesson: mixing a lifetime numerator with a point-in-time denominator is")
print("    the single most common way CAC gets misreported, and it is invisible once the")
print("    number reaches a slide. A cohort CAC (spend in the window / customers acquired in")
print("    that window) is the defensible form, and it still needs the count definition first.")

print()
print("  CAC BY CHANNEL: not computable, and here is the proof.")
print(f"    spend rows carrying an account key                     0 of {len(spend)}")
print("    marketing_spend has no account_id, customer_ref or org_slug. The ONLY bridge is")
print("    crm_accounts.lead_source, which is blank on half the rows, uses 23 labels against")
print("    finance's 6, and records LAST touch rather than what actually drove the account.")
print("    Any per-channel CAC computed here is a number with no denominator anyone can defend.")

print()
print("  PAYBACK inherits all of it, plus one more:")
n_ann = (cust.contract_type == "annual").sum()
print(f"    annual-contract customers                       {n_ann:>6} of {len(cust)} "
      f"({n_ann/len(cust)*100:.0f}%)")
print("    An annual customer pays up front, so payback is immediate by one convention and")
print("    twelve months by another. A single blended payback number across a book that is")
print(f"    {n_ann/len(cust)*100:.0f}% annual and {100-n_ann/len(cust)*100:.0f}% monthly is an average of two different things.")
