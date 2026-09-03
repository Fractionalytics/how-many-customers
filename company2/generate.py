#!/usr/bin/env python3
"""
Company 2: Halyard Systems, Inc.  A synthetic fixture built to carry a full customer base
audit and data condition review, not only the customer-count question.

Two layers, deliberately separate:

  1. THE LIFECYCLE LAYER (the referee). Every company gets a tier, a contract, an MRR with a
     real tail, a tenure-dependent churn hazard, expansion and contraction, a channel that
     actually drove it, and, for 160 of them, an acquisition book. Cohort mix shifts toward
     the Starter tier over time as paid search takes a larger share of spend. Three books
     were bought. The board keeps a spreadsheet. None of this is written to any file as a
     fact; each file holds the proxies for it, the way real systems do.

  2. THE SYSTEMS LAYER (the traps). Salesforce-shaped CRM with a hand-maintained status, a
     Stripe-shaped billing system with no key back to the CRM and a clerk's spellings,
     product telemetry keyed on a slug that matches neither, marketing spend with no account
     link, a last-touch lead_source with 23 spellings for six channels. All sixteen traps
     from company 1 are preserved here in kind.

Deterministic. Same seed, same bytes. Each layer draws from its own Random instance, so a
change in one does not reshuffle the others.

Usage:  python generate.py [outdir]
PROFILE.md carries the backstory; SOLUTIONS.md carries the referee's answers.
"""

import csv
import math
import os
import random
import sys
import unicodedata
from collections import defaultdict
from datetime import date, timedelta

SEED = 20260903
AS_OF = date(2026, 8, 20)
AS_OF_MONTH = date(2026, 8, 1)
BILLING_START = date(2022, 10, 1)          # Stripe went live; everything before it is legacy
FOUNDED = date(2016, 4, 1)
LEAD_SOURCE_FIELD_ADDED = date(2024, 6, 1)
CONTROLLER_CHANGED = date(2025, 3, 1)      # the month the board revenue line switched basis

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

lrng = random.Random(SEED)          # lifecycle
srng = random.Random(SEED + 1)      # systems layer: names, variants, statuses, duplicates
urng = random.Random(SEED + 2)      # telemetry
arng = random.Random(SEED + 3)      # attribution and spend
brng = random.Random(SEED + 4)      # the board's spreadsheet

# ------------------------------------------------------------------ calendar helpers

def add_months(d, n):
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    return date(y, m, 1)

def month_of(d):
    return date(d.year, d.month, 1)

def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)

def clamp_day(y, m, day):
    last = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(day, last))

SIM_MONTHS = [add_months(BILLING_START, i) for i in range(months_between(BILLING_START, AS_OF_MONTH) + 1)]

# ------------------------------------------------------------------ name material
# Identical to company 1, so the systems-layer traps behave the same way.

STEMS = [
    "Northwind", "Acme", "Cerulean", "Harborview", "Ironwood", "Lakeshore",
    "Meridian", "Northgate", "Oakfield", "Pinnacle", "Quarry", "Redstone",
    "Silverline", "Thornbury", "Umbra", "Vantage", "Westbrook", "Yellowfin",
    "Zenith", "Alder", "Brightwater", "Copperfield", "Dunmore", "Eastvale",
    "Fairmount", "Glenrock", "Hollowway", "Inglewood", "Juniper", "Kestrel",
    "Larkspur", "Marbury", "Nightingale", "Orchard", "Pemberton", "Quillfeather",
    "Ravenswood", "Stonebridge", "Tanglewood", "Underhill", "Verdigris",
    "Whitmore", "Yarrow", "Ashcombe", "Blackthorn", "Cranfield", "Dovetail",
]
ACCENTED_STEMS = [
    "Grupo Pena", "Munoz Holdings", "Garcia Sistemas", "Andre Freres",
    "Lopez y Asociados", "Sao Bento", "Nunez Capital", "Perez Group",
    "Hernandez Retail", "Vasquez Media", "Guimaraes Log", "Ferreira Servicos",
]
ACCENT_MAP = {
    "Grupo Pena": "Grupo Peña", "Munoz Holdings": "Muñoz Holdings",
    "Garcia Sistemas": "García Sistemas", "Andre Freres": "André Frères",
    "Lopez y Asociados": "López y Asociados", "Sao Bento": "São Bento",
    "Nunez Capital": "Núñez Capital", "Perez Group": "Pérez Group",
    "Hernandez Retail": "Hernández Retail", "Vasquez Media": "Vásquez Media",
    "Guimaraes Log": "Guimarães Log", "Ferreira Servicos": "Ferreira Serviços",
}
MIDDLES = [
    "Trading", "Supply", "Freight", "Analytics", "Clinical", "Digital",
    "Precision", "Coastal", "Summit", "Foundry", "Beacon", "Anchor",
    "Cascade", "Pioneer", "Sterling", "Vector", "Atlas", "Compass",
    "Keystone", "Lumen", "Nimbus", "Onyx", "Quantum", "Sable",
]
SUFFIXES = ["Inc", "LLC", "Corp", "Group", "Holdings", "Partners", "Systems", "Labs"]
SECTORS = ["Retail", "Logistics", "Healthcare", "Fintech", "Manufacturing",
           "Media", "Education", "Hospitality", "Energy", "Construction"]
OWNERS = ["a.reyes", "j.whitfield", "s.okoro", "m.tan", "d.castellanos", "p.lindqvist"]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def slugify(s):
    s = strip_accents(s).lower()
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")

def crm_id(i):
    return "001Qy%011d" % i

def bill_ref(i):
    return "cus_%012d" % i

def vary_name(canonical, mode):
    base = canonical
    if mode == "exact":
        return base
    if mode == "drop_suffix":
        parts = base.split()
        return " ".join(parts[:-1]) if len(parts) > 2 else base
    if mode == "expand":
        return base.replace(" Corp", " Corporation").replace(" Inc", " Incorporated")
    if mode == "punct":
        return base.replace(" Inc", " Inc.").replace(" Corp", " Corp.")
    if mode == "upper":
        return base.upper()
    if mode == "dba":
        return base.split()[0] + " (DBA)"
    if mode == "amp":
        return base.replace(" and ", " & ")
    return base

# ------------------------------------------------------------------ the designed economics
# Retention targets are twelve-month LOGO retention for organic customers, calibrated to
# Lenny's Newsletter "What is good retention": SMB/mid-market SaaS 60% good / 80% great on
# six-month user retention and 90 / 110 NRR; enterprise 70 / 90 and 110 / 130.

TIERS = {
    #             MRR log-normal          band              12m logo   contract mix (monthly, annual, usage)
    "Starter":    dict(median=560,   sigma=0.42, lo=250,   hi=1500,   ret12=0.66, contract=(0.80, 0.15, 0.05),
                       density=0.32, users=(1, 6),   exp=0.030, con=0.020),
    "Growth":     dict(median=2300,  sigma=0.50, lo=1200,  hi=9000,   ret12=0.78, contract=(0.45, 0.45, 0.10),
                       density=0.50, users=(3, 25),  exp=0.075, con=0.018),
    "Enterprise": dict(median=8000,  sigma=0.85, lo=6000,  hi=90000,  ret12=0.88, contract=(0.05, 0.85, 0.10),
                       density=0.66, users=(10, 80), exp=0.100, con=0.012),
}
TIER_NAMES = list(TIERS)

# Tenure multipliers on the monthly hazard: the first half-year is the dangerous one.
def tenure_mult(tenure_months):
    if tenure_months <= 6:
        return 1.7
    if tenure_months <= 12:
        return 1.1
    if tenure_months <= 36:
        return 0.75
    return 0.55

def solve_base_hazard(ret12):
    """Monthly base hazard h such that twelve-month survival under the tenure multipliers is ret12."""
    lo, hi = 0.0, 0.5
    for _ in range(60):
        h = (lo + hi) / 2
        s = 1.0
        for t in range(1, 13):
            s *= max(0.0, 1 - h * tenure_mult(t))
        if s > ret12:
            lo = h
        else:
            hi = h
    return (lo + hi) / 2

BASE_HAZARD = {t: solve_base_hazard(cfg["ret12"]) for t, cfg in TIERS.items()}

SECTOR_MULT = {"Construction": 1.30}          # one weak sector
ACQUIRED_MULT = 1.4                           # the bought books churn faster (thesis leg 2 fails), on PLATFORM tenure
LEGACY_MULT = 0.70                            # survivors of the pre-2022 book

# What actually drove each customer, and how that tilts the tier. Paid channels bring small
# customers; partner, events and outbound bring larger ones. Spend tilts toward paid search
# over time, and the cohort mix tilts with it. This is the mix shift.
CHANNEL_TIER = {
    "paid_search":   (0.76, 0.21, 0.03),
    "paid_social":   (0.74, 0.23, 0.03),
    "content_seo":   (0.58, 0.34, 0.08),
    "events":        (0.26, 0.54, 0.20),
    "partner":       (0.30, 0.54, 0.16),
    "outbound":      (0.16, 0.60, 0.24),
    "word_of_mouth": (0.52, 0.40, 0.08),
}
# Base monthly spend by channel, and its multiplier at the end of the history.
SPEND_CHANNELS = {
    "Paid Search":           ("paid_search",  155_000, 2.6),
    "Paid Social":           ("paid_social",   70_000, 1.9),
    "Events & Sponsorships": ("events",        75_000, 1.0),
    "Content & SEO":         ("content_seo",   45_000, 1.3),
    "Partner Program":       ("partner",       40_000, 1.0),
    "Outbound SDR":          ("outbound",      90_000, 1.2),
}
SOURCE_VARIANTS = {
    "paid_search":  ["Google Ads", "PPC", "paid search", "Paid Search"],
    "paid_social":  ["LinkedIn", "Paid Social", "social", "LinkedIn Ads"],
    "events":       ["Event", "Conference", "Tradeshow"],
    "content_seo":  ["Organic Search", "SEO", "Blog"],
    "partner":      ["Partner", "Referral", "Partner Referral"],
    "outbound":     ["Outbound", "SDR", "Cold Outreach"],
    "direct":       ["Direct", "Word of Mouth", "direct"],
}

ACQUISITIONS = [
    # book, closed, accounts, the seller's product, city
    ("Northgate", date(2024, 2, 29), 63, "a field-reporting app", "Columbus, Ohio"),
    ("Pelham",    date(2024, 10, 31), 52, "an approvals workflow", "Pittsburgh, Pennsylvania"),
    ("Vireo",     date(2025, 5, 30), 45, "a crew-scheduling tool", "Charlotte, North Carolina"),
]
N_LEGACY = 140                                # customers already on the books when Stripe went live

def progress(m):
    """0 before October 2024, 1 by August 2026: when the mix shift happens."""
    return min(1.0, max(0.0, months_between(date(2024, 10, 1), m) / 22.0))

def spend_for(channel_name, m, i):
    ch, base, end_mult = SPEND_CHANNELS[channel_name]
    ramp = 1.0 + (end_mult - 1.0) * (i / (len(SIM_MONTHS) - 1))
    season = 1.18 if m.month in (2, 3, 9, 10) else (0.78 if m.month in (7, 12) else 1.0)
    return base * ramp * season * arng.uniform(0.84, 1.18)

def channel_mix_for(m, i):
    """Share of spend by true channel this month, plus a word-of-mouth slice spend never buys."""
    shares = {}
    for name, (ch, base, end_mult) in SPEND_CHANNELS.items():
        ramp = 1.0 + (end_mult - 1.0) * (i / (len(SIM_MONTHS) - 1))
        shares[ch] = base * ramp
    tot = sum(shares.values())
    mix = {ch: 0.92 * v / tot for ch, v in shares.items()}
    mix["word_of_mouth"] = 0.08
    return mix

def draw_tier(channel, m):
    s, g, e = CHANNEL_TIER[channel]
    # a further tilt toward Starter as the company leans on self-serve
    p = progress(m)
    s2 = s + 0.18 * p
    e2 = max(0.02, e - 0.05 * p)
    g2 = 1.0 - s2 - e2
    r = lrng.random()
    return "Starter" if r < s2 else ("Growth" if r < s2 + g2 else "Enterprise")

def draw_mrr(tier):
    cfg = TIERS[tier]
    v = math.exp(math.log(cfg["median"]) + cfg["sigma"] * lrng.gauss(0, 1))
    return round(min(cfg["hi"], max(cfg["lo"], v)), 2)

def draw_contract(tier):
    pm, pa, pu = TIERS[tier]["contract"]
    r = lrng.random()
    return "monthly" if r < pm else ("annual" if r < pm + pa else "usage")

# ------------------------------------------------------------------ the companies

companies = []
used_names = set()
last_name = None
near_collision_slots = set()

def new_name(idx):
    global last_name
    if idx % 100 < 8:
        plain = ACCENTED_STEMS[idx % len(ACCENTED_STEMS)]
        canonical = "%s %s" % (ACCENT_MAP[plain], srng.choice(MIDDLES))
        accented = True
    elif idx in near_collision_slots and last_name:
        parts = last_name.split()
        canonical = " ".join(parts[:-1] + [srng.choice([s for s in SUFFIXES if s != parts[-1]])])
        accented = False
    else:
        canonical, accented = None, False
        while canonical is None or canonical in used_names:
            canonical = "%s %s %s" % (srng.choice(STEMS), srng.choice(MIDDLES), srng.choice(SUFFIXES))
    while canonical in used_names:
        canonical += " II"
    used_names.add(canonical)
    last_name = canonical
    return canonical, accented

def make_company(idx, kind, tier, contract, mrr, signed, platform_start, channel, book=None):
    name, accented = new_name(idx)
    sector = lrng.choice(SECTORS)
    return {
        "cid": idx, "canonical": name, "accented": accented, "sector": sector,
        "kind": kind,                     # organic | legacy | acquired
        "tier": tier, "contract": contract, "mrr0": mrr,
        "signed": signed,                 # the ORIGINAL contract date (CRM created_date follows it)
        "platform_start": platform_start, # first invoice on Halyard's billing
        "true_channel": channel, "acq_book": book,
        "owner": lrng.choice(OWNERS),
    }

idx = 0
# 1. The legacy book: customers already live when Stripe went live in October 2022.
for _ in range(N_LEGACY):
    r = lrng.random()
    tier = "Starter" if r < 0.35 else ("Growth" if r < 0.82 else "Enterprise")
    signed = FOUNDED + timedelta(days=lrng.randint(300, (BILLING_START - FOUNDED).days - 30))
    start = BILLING_START + timedelta(days=lrng.randint(0, 75))
    companies.append(make_company(idx, "legacy", tier, draw_contract(tier), draw_mrr(tier),
                                  signed, start, lrng.choice(list(CHANNEL_TIER))))
    idx += 1

# 2. Organic acquisition, month by month, driven by the channel mix of the month.
for i, m in enumerate(SIM_MONTHS):
    base = 17 + 15 * (i / (len(SIM_MONTHS) - 1))
    season = 1.15 if m.month in (3, 4, 10, 11) else (0.75 if m.month in (7, 12) else 1.0)
    n_new = int(round(base * season * lrng.uniform(0.8, 1.2)))
    if m == AS_OF_MONTH:
        n_new = int(n_new * 20 / 31)
    mix = channel_mix_for(m, i)
    chs, ws = zip(*mix.items())
    for _ in range(n_new):
        ch = lrng.choices(chs, weights=ws)[0]
        tier = draw_tier(ch, m)
        day = lrng.randint(1, 28)
        signed = clamp_day(m.year, m.month, day)
        if signed > AS_OF - timedelta(days=3):
            continue
        companies.append(make_company(idx, "organic", tier, draw_contract(tier), draw_mrr(tier),
                                      signed, signed, ch))
        idx += 1

# 3. The acquired books. Original contract dates are years old; the migration preserved them
#    (good practice, and it erases the only fingerprint). Billing starts as each contract was
#    re-papered in the quarter after close.
for book, closed, n, _, _ in ACQUISITIONS:
    for _ in range(n):
        r = lrng.random()
        tier = "Starter" if r < 0.45 else ("Growth" if r < 0.92 else "Enterprise")
        signed = closed - timedelta(days=lrng.randint(200, 1800))
        start = closed + timedelta(days=lrng.randint(5, 95))
        companies.append(make_company(idx, "acquired", tier, draw_contract(tier), draw_mrr(tier),
                                      signed, start, "acquisition", book))
        idx += 1

# 4. Strategic accounts. Every mid-market book has a handful of customers three to five times
#    the size of the next tier down, and two of them here are on MONTHLY contracts, which is a
#    risk the multiple should price.
whales = sorted((c for c in companies if c["kind"] == "organic" and c["tier"] == "Enterprise"),
                key=lambda c: c["mrr0"], reverse=True)[:5]
for j, c in enumerate(whales):
    c["mrr0"] = round(c["mrr0"] * lrng.uniform(2.5, 4.5), 2)
    c["whale"] = True
    if j in (1, 3):
        c["contract"] = "monthly"

N = len(companies)
near_collision_slots = set()   # names are already drawn; kept for parity with company 1

# ------------------------------------------------------------------ the lifecycle simulation
# Month by month from platform start to the as-of month. Produces, per company: the MRR in
# force each month, the churn date (if any), the dormant window (if any), and the invoices.

def hazard(c, tenure):
    h = BASE_HAZARD[c["tier"]] * tenure_mult(tenure)
    h *= SECTOR_MULT.get(c["sector"], 1.0)
    if c["kind"] == "acquired":
        h *= ACQUIRED_MULT
    if c["kind"] == "legacy":
        h *= LEGACY_MULT
    return min(0.6, h)

def annual_renewal_survival(c, tenure_at_renewal):
    s = 1.0
    for t in range(tenure_at_renewal - 11, tenure_at_renewal + 1):
        s *= max(0.0, 1 - hazard(c, max(1, t)))
    return s

invoice_rows = []
next_inv = 1

for c in companies:
    cfg = TIERS[c["tier"]]
    start = c["platform_start"]
    start_month = month_of(start)
    mrr = c["mrr0"]
    alive = True
    churn_date = None
    mrr_by_month = {}
    pending_change = 1.0            # for annual: accumulated expansion applied at renewal
    day = min(start.day, 28)
    m = start_month
    mi = 0
    while m <= AS_OF_MONTH and alive:
        # Original tenure for organic and legacy customers; platform tenure for an acquired one,
        # because the relationship with Halyard is new whatever the old contract date says.
        tenure = mi + 1 if c["kind"] == "acquired" else max(1, months_between(month_of(c["signed"]), m))
        inv_date = clamp_day(m.year, m.month, day)
        if inv_date < start:
            inv_date = start
        is_anniv = (mi > 0 and mi % 12 == 0)
        # --- churn decision for this month
        if c["contract"] == "annual":
            if is_anniv and lrng.random() > annual_renewal_survival(c, tenure):
                alive = False
                churn_date = inv_date
                break
        else:
            if mi > 0 and lrng.random() < hazard(c, tenure):
                alive = False
                churn_date = inv_date - timedelta(days=lrng.randint(1, 20))
                break
        # --- expansion / contraction
        r = lrng.random()
        if c["contract"] == "annual":
            if r < cfg["exp"]:
                pending_change *= lrng.uniform(1.05, 1.28)
            elif r < cfg["exp"] + cfg["con"]:
                pending_change *= lrng.uniform(0.80, 0.95)
            if is_anniv:
                mrr = round(min(cfg["hi"] * 1.5, mrr * pending_change), 2)
                pending_change = 1.0
        else:
            if r < cfg["exp"]:
                mrr = round(min(cfg["hi"] * 1.5, mrr * lrng.uniform(1.05, 1.28)), 2)
            elif r < cfg["exp"] + cfg["con"]:
                mrr = round(max(cfg["lo"] * 0.5, mrr * lrng.uniform(0.80, 0.95)), 2)
        mrr_by_month[m] = mrr
        # --- the invoice
        if inv_date <= AS_OF:
            if c["contract"] == "annual":
                amt = mrr * 12 if (mi == 0 or is_anniv) else None
            elif c["contract"] == "usage":
                amt = mrr * lrng.uniform(0.75, 1.30)
            else:
                amt = mrr
            if amt is not None:
                invoice_rows.append([c["cid"], inv_date, round(amt, 2)])
        m = add_months(m, 1)
        mi += 1
    c["alive"] = alive
    c["churn_date"] = churn_date
    c["mrr_by_month"] = mrr_by_month
    c["mrr_now"] = mrr
    # Dormant: paying, not using. A small share of live monthly and usage customers.
    c["dormant_from"] = None
    if alive and c["contract"] != "annual" and c["tier"] != "Enterprise" and lrng.random() < 0.07:
        c["dormant_from"] = AS_OF - timedelta(days=lrng.randint(60, 150))

# Invoice statuses. A failed invoice is retried; a void one is reissued; a refund is a refund.
inv_out = []
for cid, d, amt in sorted(invoice_rows, key=lambda r: (r[1], r[0])):
    r = srng.random()
    if r < 0.925:
        status = "paid"
    elif r < 0.950:
        status = "failed"
    elif r < 0.975:
        status = "void"
    else:
        status = "refunded"
    inv_out.append([cid, d, amt, status])
    if status == "failed" and srng.random() < 0.85:
        inv_out.append([cid, d + timedelta(days=srng.randint(3, 9)), amt, "paid"])
    if status == "void":
        inv_out.append([cid, d, round(amt * srng.uniform(0.9, 1.1), 2), "paid"])

# ------------------------------------------------------------------ CRM system
crm_rows = []
next_crm = 100000
crm_pop = set(srng.sample(range(N), int(N * 0.958)))
dupe_in_crm = set(srng.sample(sorted(crm_pop), int(N * 0.05)))
by_cid = {c["cid"]: c for c in companies}

def crm_status_for(c, k):
    if k == 1:
        return srng.choices(["Inactive", "Churned", "Active", ""], weights=[40, 30, 22, 8])[0]
    if not c["alive"]:
        return srng.choices(["Churned", "Active", "Inactive", ""], weights=[64, 22, 10, 4])[0]
    if c["dormant_from"]:
        return srng.choices(["Active", "Inactive", "", "Churned"], weights=[55, 28, 12, 5])[0]
    return srng.choices(["Active", "", "Inactive"], weights=[88, 8, 4])[0]

for c in companies:
    if c["cid"] not in crm_pop:
        continue
    n_rows = 2 if c["cid"] in dupe_in_crm else 1
    for k in range(n_rows):
        next_crm += 1
        mode = srng.choices(["exact", "drop_suffix", "expand", "punct", "upper", "dba", "amp"],
                            weights=[62, 9, 8, 8, 5, 4, 4])[0]
        name = vary_name(c["canonical"], "exact" if k == 0 else mode)
        status = crm_status_for(c, k)
        # The CRM MRR field is typed in and not maintained: for a churned account it is
        # whatever it was when someone last touched it.
        if k == 0:
            mrr = c["mrr_now"] if c["alive"] else (c["mrr_now"] if status == "Active" else
                                                   round(c["mrr_now"] * srng.choice([1, 1, 0]), 2))
        else:
            mrr = round(c["mrr_now"] * srng.uniform(0, 0.4), 2)
        tier = c["tier"] if srng.random() < 0.94 else srng.choice(TIER_NAMES)
        c.setdefault("crm_status", status if k == 0 else c.get("crm_status"))
        crm_rows.append({
            "account_id": crm_id(next_crm),
            "account_name": name,
            "email_domain": slugify(c["canonical"].split()[0]) + ".com",
            "sector": c["sector"],
            "created_date": (c["signed"] - timedelta(days=srng.randint(0, 45))).isoformat(),
            "account_status": status,
            "plan_tier": tier,
            "mrr_usd": "%.2f" % mrr,
            "owner": c["owner"],
            "_cid": c["cid"], "_k": k,
        })

# ------------------------------------------------------------------ billing system
bill_rows, inv_rows = [], []
next_bill = 500000
bill_pop = set(srng.sample(range(N), int(N * 0.945)))
split_billing = set(srng.sample(sorted(bill_pop), 25))
inv_by_cid = defaultdict(list)
for cid, d, amt, status in inv_out:
    inv_by_cid[cid].append((d, amt, status))

for c in companies:
    if c["cid"] not in bill_pop:
        continue
    n_rows = 2 if c["cid"] in split_billing else 1
    refs = []
    for k in range(n_rows):
        next_bill += 1
        mode = srng.choices(["exact", "drop_suffix", "expand", "punct", "upper", "amp"],
                            weights=[40, 16, 14, 14, 8, 8])[0]
        name = vary_name(c["canonical"], mode)
        if c["accented"]:
            name = strip_accents(name)
        if k == 1:
            name = name + " - " + srng.choice(["EMEA", "LATAM", "Subsidiary", "Div 2"])
        refs.append((bill_ref(next_bill), name))
    invs = inv_by_cid.get(c["cid"], [])
    last_paid = {ref: None for ref, _ in refs}
    first = min((d for d, _, _ in invs), default=c["platform_start"])
    for d, amt, status in invs:
        share = amt / n_rows
        for ref, _ in refs:
            inv_rows.append({"invoice_id": None, "customer_ref": ref, "invoice_date": d.isoformat(),
                             "amount_usd": "%.2f" % share, "status": status, "currency": "USD"})
            if status == "paid":
                last_paid[ref] = d
    for ref, name in refs:
        bill_rows.append({
            "customer_ref": ref, "company_name": name,
            "billing_email": "ap@" + slugify(c["canonical"].split()[0]) + ".com",
            "first_invoice_date": first.isoformat(),
            "last_paid_invoice_date": last_paid[ref].isoformat() if last_paid[ref] else "",
            "contract_type": c["contract"], "_cid": c["cid"],
        })

inv_rows.sort(key=lambda r: (r["invoice_date"], r["customer_ref"]))
for i, r in enumerate(inv_rows, 1):
    r["invoice_id"] = "in_%09d" % i

# ------------------------------------------------------------------ product telemetry
# Gated on the platform start and the churn date. Intensity decays over the 90 days before a
# churn (a leading indicator), stops in a dormant window, and trails for up to 40 days after
# a churn (the company-1 trap, kept). Weekends are quiet.
usage_rows = []
for c in companies:
    if c["cid"] not in bill_pop and c["cid"] not in crm_pop:
        continue
    cfg = TIERS[c["tier"]]
    slug = slugify(c["canonical"])
    lo_u, hi_u = cfg["users"]
    start = c["platform_start"] - timedelta(days=urng.randint(0, 14))     # a short trial
    end = AS_OF if c["alive"] else min(AS_OF, c["churn_date"] + timedelta(days=urng.randint(0, 40)))
    d = start
    while d <= end:
        dens = cfg["density"] * (0.25 if d.weekday() >= 5 else 1.0)
        if c["churn_date"]:
            days_to = (c["churn_date"] - d).days
            if 0 <= days_to <= 90:
                dens *= 0.15 + 0.85 * (days_to / 90.0)
            elif days_to < 0:
                dens = 0.06
        if c["dormant_from"] and d >= c["dormant_from"]:
            dens = 0.0
        if urng.random() < dens:
            scale = 0.4 if (c["churn_date"] and (c["churn_date"] - d).days <= 90) else 1.0
            usage_rows.append({"org_slug": slug, "event_date": d.isoformat(),
                               "active_users": max(1, int(urng.randint(lo_u, hi_u) * scale)),
                               "sessions": urng.randint(1, 8) * max(1, int(urng.randint(lo_u, hi_u) * scale))})
        d += timedelta(days=1)

# ------------------------------------------------------------------ attribution and spend
def last_touch_tag(c):
    created = c["signed"]
    if created < LEAD_SOURCE_FIELD_ADDED:
        return ""
    if arng.random() < 0.08:
        return ""
    ch = c["true_channel"]
    if ch == "acquisition":
        r = arng.random()
        if r < 0.45:
            return ""
        if r < 0.80:
            return arng.choice(SOURCE_VARIANTS[arng.choice(["paid_search", "content_seo", "outbound"])])
        return arng.choice(SOURCE_VARIANTS["partner"])
    if ch == "word_of_mouth":
        return arng.choice(SOURCE_VARIANTS["direct"] + [""])
    steal = {"paid_search": .24, "paid_social": .30, "events": .38,
             "content_seo": .12, "partner": .15, "outbound": .29}
    if arng.random() < steal.get(ch, .2):
        return arng.choice(SOURCE_VARIANTS["direct"] + SOURCE_VARIANTS["content_seo"])
    return arng.choice(SOURCE_VARIANTS[ch])

for r in crm_rows:
    r["lead_source"] = last_touch_tag(by_cid[r["_cid"]])

spend_rows = []
for i, m in enumerate(SIM_MONTHS):
    for name in SPEND_CHANNELS:
        spend_rows.append({"month": m.isoformat()[:7], "channel": name,
                           "spend_usd": "%.2f" % spend_for(name, m, i)})

# ------------------------------------------------------------------ the board's spreadsheet
# Built the way a controller builds it: from whatever the CRM said on the day the deck was
# made, with a revenue line pulled from billing on one basis until a new controller changed
# it, hand adjustments some months, and no definitions anywhere.

def crm_says_active_on(c, on):
    """What the CRM status read on a given date, reconstructed from the drift rules."""
    if c["cid"] not in crm_pop:
        return False
    if month_of(c["signed"]) > on:
        return False
    if c["alive"] or c["churn_date"] > on:
        return c.get("crm_status", "Active") in ("Active", "") or c["alive"]
    # churned before this date: was it marked yet?
    if c.get("crm_status") == "Active":
        return True                        # never marked; stale to this day
    marked = c["churn_date"] + timedelta(days=c.setdefault("_mark_lag", brng.randint(20, 120)))
    return on < marked

# The revenue line is pulled from Stripe, so it is built from the invoice rows that exist in
# Stripe: paid only, and only for customers Stripe holds.
contract_of_ref = {b["customer_ref"]: b["contract_type"] for b in bill_rows}
paid_by_month_cash = defaultdict(float)
recog_by_month = defaultdict(float)
for r in inv_rows:
    if r["status"] != "paid":
        continue
    d = date.fromisoformat(r["invoice_date"])
    amt = float(r["amount_usd"])
    paid_by_month_cash[month_of(d)] += amt
    if contract_of_ref[r["customer_ref"]] == "annual":
        for k in range(12):
            recog_by_month[add_months(month_of(d), k)] += amt / 12.0
    else:
        recog_by_month[month_of(d)] += amt

ADJUSTMENTS = {
    date(2023, 6, 1): (-14, "removed duplicate accounts per J.R. cleanup"),
    date(2024, 3, 1): (+9,  "reinstated annual accounts flagged inactive in error"),
    date(2024, 11, 1): (-22, "Pelham migration in progress, excl. until re-papered"),
    date(2025, 3, 1): (0,   "M.K. took over reporting; revenue now per Stripe recognized"),
    date(2025, 9, 1): (+11, "added Vireo accounts not yet in SFDC"),
    date(2026, 2, 1): (-6,  "removed test accounts"),
}
board_rows = []
for m in SIM_MONTHS[:-1]:
    nxt = add_months(m, 1)
    prepared_on = clamp_day(nxt.year, nxt.month, brng.randint(4, 9))
    prepared_by = "J.R." if m < CONTROLLER_CHANGED else "M.K."
    active = [c for c in companies if crm_says_active_on(c, prepared_on)]
    n_active = len(active)
    mrr_reported = sum(c["mrr_now"] if c["alive"] else c["mrr_now"] for c in active)
    adj, note = ADJUSTMENTS.get(m, (0, ""))
    rev = paid_by_month_cash[m] if m < CONTROLLER_CHANGED else recog_by_month[m]
    new_c = sum(1 for c in companies if c["cid"] in crm_pop and month_of(c["signed"]) == m)
    churned_c = sum(1 for c in companies if c["churn_date"] and month_of(c["churn_date"]) == m
                    and c.get("crm_status") == "Churned")
    board_rows.append({
        "month": m.isoformat()[:7],
        "active_customers": n_active + adj,
        "mrr_usd": "%.0f" % (mrr_reported * brng.uniform(0.995, 1.005)),
        "revenue_usd": "%.0f" % rev,
        "new_customers": new_c,
        "churned_customers": churned_c,
        "adjustment": adj if adj else "",
        "adjustment_note": note,
        "prepared_on": prepared_on.isoformat(),
        "prepared_by": prepared_by,
    })

# ------------------------------------------------------------------ the acquisition schedules
# The document the seller produces on request. The seller's spelling, not the CRM's.
sched_rows = []
for book, closed, n, product, city in ACQUISITIONS:
    for c in companies:
        if c["acq_book"] != book:
            continue
        name = c["canonical"]
        if srng.random() < 0.3:
            name = name.upper()
        sched_rows.append({
            "book": book, "closed": closed.isoformat(),
            "customer": strip_accents(name) if srng.random() < 0.5 else name,
            "original_contract_date": c["signed"].isoformat(),
            "acv_at_close_usd": "%.0f" % (c["mrr0"] * 12),
            "contract_type_at_close": c["contract"],
        })

# ------------------------------------------------------------------ write
def write(name, rows, fields):
    p = os.path.join(OUT, name)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return p, len(rows)

srng.shuffle(crm_rows)
srng.shuffle(bill_rows)
outputs = [
    write("crm_accounts.csv", crm_rows,
          ["account_id", "account_name", "email_domain", "sector", "created_date",
           "account_status", "plan_tier", "mrr_usd", "owner", "lead_source"]),
    write("billing_customers.csv", bill_rows,
          ["customer_ref", "company_name", "billing_email", "first_invoice_date",
           "last_paid_invoice_date", "contract_type"]),
    write("billing_invoices.csv", inv_rows,
          ["invoice_id", "customer_ref", "invoice_date", "amount_usd", "status", "currency"]),
    write("product_usage.csv", usage_rows, ["org_slug", "event_date", "active_users", "sessions"]),
    write("marketing_spend.csv", spend_rows, ["month", "channel", "spend_usd"]),
    write("board_kpis.csv", board_rows,
          ["month", "active_customers", "mrr_usd", "revenue_usd", "new_customers",
           "churned_customers", "adjustment", "adjustment_note", "prepared_on", "prepared_by"]),
    write("acquisition_schedules.csv", sched_rows,
          ["book", "closed", "customer", "original_contract_date", "acv_at_close_usd",
           "contract_type_at_close"]),
]

# ------------------------------------------------------------------ the referee
def report():
    live = [c for c in companies if c["alive"]]
    print("as of %s   seed %d" % (AS_OF.isoformat(), SEED))
    for p, n in outputs:
        print("  %-26s %8d rows" % (os.path.basename(p), n))
    print()
    print("THE REFEREE (appears in no file)")
    print("  companies ever                    %5d   (legacy %d, organic %d, acquired %d)" % (
        N, sum(c["kind"] == "legacy" for c in companies), sum(c["kind"] == "organic" for c in companies),
        sum(c["kind"] == "acquired" for c in companies)))
    print("  genuinely live                    %5d" % len(live))
    print("  dormant (paying, not using)       %5d" % sum(1 for c in live if c["dormant_from"]))
    print("  churned                           %5d" % (N - len(live)))
    mrr_live = sum(c["mrr_now"] for c in live)
    print("  live MRR                       $%9s   (ARR $%s)" % (format(round(mrr_live), ","), format(round(mrr_live * 12), ",")))
    for t in TIER_NAMES:
        lt = [c for c in live if c["tier"] == t]
        print("    %-11s live %4d  (%4.1f%% of logos)  MRR $%9s (%4.1f%% of MRR)  base hazard %.4f/mo" % (
            t, len(lt), 100.0 * len(lt) / len(live), format(round(sum(c["mrr_now"] for c in lt)), ","),
            100.0 * sum(c["mrr_now"] for c in lt) / mrr_live, BASE_HAZARD[t]))
    top = sorted((c["mrr_now"] for c in live), reverse=True)
    print("  top 1 / 10 customers, %% of live MRR   %4.1f / %4.1f" % (100 * top[0] / mrr_live, 100 * sum(top[:10]) / mrr_live))
    # twelve-month logo retention by tier, organic customers whose platform start is 13+ months old
    print("  12-month logo retention, organic, by tier (platform start 13-30 months before as-of):")
    for t in TIER_NAMES:
        base = [c for c in companies if c["kind"] == "organic" and c["tier"] == t
                and 13 <= months_between(month_of(c["platform_start"]), AS_OF_MONTH) <= 30]
        kept = [c for c in base if c["alive"] or months_between(month_of(c["platform_start"]), month_of(c["churn_date"])) > 12]
        print("    %-11s %4d in base   %5.1f%%" % (t, len(base), 100.0 * len(kept) / max(1, len(base))))
    for kind in ("legacy", "acquired"):
        base = [c for c in companies if c["kind"] == kind and 13 <= months_between(month_of(c["platform_start"]), AS_OF_MONTH) <= 48]
        kept = [c for c in base if c["alive"] or months_between(month_of(c["platform_start"]), month_of(c["churn_date"])) > 12]
        print("    %-11s %4d in base   %5.1f%%" % (kind, len(base), 100.0 * len(kept) / max(1, len(base))))
    # NRR by tier: MRR now from customers live 12 months ago, over their MRR then
    base_m = add_months(AS_OF_MONTH, -12)
    print("  12-month NRR by tier (MRR in %s to MRR now, same customers):" % base_m.isoformat()[:7])
    for t in TIER_NAMES + ["ALL"]:
        cs = [c for c in companies if (t == "ALL" or c["tier"] == t) and base_m in c["mrr_by_month"]]
        then = sum(c["mrr_by_month"][base_m] for c in cs)
        now = sum(c["mrr_by_month"].get(AS_OF_MONTH, 0.0) if c["alive"] else 0.0 for c in cs)
        print("    %-11s %4d customers  %6.1f%%" % (t, len(cs), 100.0 * now / max(1, then)))
    spend_total = sum(float(r["spend_usd"]) for r in spend_rows)
    organic = [c for c in companies if c["kind"] == "organic"]
    print("  marketing spend, %d months        $%s" % (len(SIM_MONTHS), format(round(spend_total), ",")))
    print("  spend per organic customer        $%s   (the honest blended CAC)" % format(round(spend_total / len(organic)), ","))
    print("  spend per company ever            $%s   (counts legacy and acquired, which cost nothing)" % format(round(spend_total / N), ","))
    new_mrr = sum(c["mrr0"] for c in organic) / len(organic)
    print("  mean first MRR, organic           $%s   -> blended payback %.1f months on revenue, %.1f at 80%% gross margin" % (
        format(round(new_mrr), ","), spend_total / len(organic) / new_mrr, spend_total / len(organic) / (0.8 * new_mrr)))
    for yr in (2023, 2024, 2025, 2026):
        cs = [c for c in organic if c["platform_start"].year == yr]
        s = sum(1 for c in cs if c["tier"] == "Starter")
        print("  %d organic cohort: %4d customers, Starter share %4.1f%%" % (yr, len(cs), 100.0 * s / max(1, len(cs))))

if __name__ == "__main__":
    report()
