#!/usr/bin/env python3
"""
Synthetic fixture: two systems, no shared key, and several defensible answers to
"how many customers do we have?"

Built to test what a data agent, a semantic-modeling tool, or a person does when
a question has more than one correct answer.

DESIGN RULE, and it is the whole point: this fixture is NOT rigged to defeat
anything. A good agent SHOULD find the disagreements quickly. What it tests is
what happens AFTER they are found: every conflict here is resolvable only by a
business decision that is not present in any table, because the fact needed to
settle it was never recorded anywhere.

Deterministic. Same seed, same bytes, every run. Change SEED for a different
book with the same problems.

Usage:  python generate.py [outdir]
"""

import csv
import os
import random
import sys
import unicodedata
from datetime import date, timedelta

SEED = 20260820
AS_OF = date(2026, 8, 20)
N_COMPANIES = 1200

random.seed(SEED)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------- name material

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
# ~8% of the book carries diacritics, and they are the LatAm and Iberian names,
# which is exactly where a naive name join fails silently.
ACCENTED_STEMS = [
    "Grupo Pena", "Munoz Holdings", "Garcia Sistemas", "Andre Freres",
    "Lopez y Asociados", "Sao Bento", "Nunez Capital", "Perez Group",
    "Hernandez Retail", "Vasquez Media", "Guimaraes Log", "Ferreira Servicos",
]
ACCENT_MAP = {
    "Grupo Pena": "Grupo Peña",
    "Munoz Holdings": "Muñoz Holdings",
    "Garcia Sistemas": "García Sistemas",
    "Andre Freres": "André Frères",
    "Lopez y Asociados": "López y Asociados",
    "Sao Bento": "São Bento",
    "Nunez Capital": "Núñez Capital",
    "Perez Group": "Pérez Group",
    "Hernandez Retail": "Hernández Retail",
    "Vasquez Media": "Vásquez Media",
    "Guimaraes Log": "Guimarães Log",
    "Ferreira Servicos": "Ferreira Serviços",
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


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def slugify(s):
    s = strip_accents(s).lower()
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")


def crm_id(i):
    return "001Qy%011d" % i


def bill_ref(i):
    return "cus_%012d" % i


def vary_name(canonical, mode):
    """Same company, spelled the way a different system happens to hold it."""
    base = canonical
    if mode == "exact":
        return base
    if mode == "drop_suffix":
        parts = base.split()
        return " ".join(parts[:-1]) if len(parts) > 2 else base
    if mode == "expand":
        return base.replace(" Corp", " Corporation").replace(" Inc", " Incorporated")
    if mode == "punct":
        return base.replace(" Inc", " Inc.").replace(" Corp", " Corp.") + ""
    if mode == "upper":
        return base.upper()
    if mode == "dba":
        return base.split()[0] + " (DBA)"
    if mode == "amp":
        return base.replace(" and ", " & ")
    return base


# ----------------------------------------------------------- ground truth pass

companies = []
used_names = set()
# 15 deliberate near-collisions: genuinely DIFFERENT companies whose names differ
# by one token. Real books are full of these and they are the trap that punishes
# an over-eager fuzzy match. Documented in ANSWER-KEY.md.
near_collision_at = set(random.sample(range(40, N_COMPANIES), 15))
last_name = None

for i in range(N_COMPANIES):
    if i % 100 < 8 and ACCENTED_STEMS:
        plain = ACCENTED_STEMS[i % len(ACCENTED_STEMS)]
        # Accented families need to stay unique too, so give each a middle word.
        canonical = "%s %s" % (ACCENT_MAP[plain], random.choice(MIDDLES))
        accented = True
    elif i in near_collision_at and last_name:
        parts = last_name.split()
        canonical = " ".join(parts[:-1] + [random.choice(
            [s for s in SUFFIXES if s != parts[-1]])])
        accented = False
    else:
        canonical = None
        accented = False
        while canonical is None or canonical in used_names:
            canonical = "%s %s %s" % (random.choice(STEMS),
                                      random.choice(MIDDLES),
                                      random.choice(SUFFIXES))
    while canonical in used_names:
        canonical = canonical + " II"
    used_names.add(canonical)
    last_name = canonical

    signed = AS_OF - timedelta(days=random.randint(30, 1400))

    # The lifecycle facts that the two systems will later disagree about.
    contract = random.choices(["monthly", "annual", "annual", "usage"],
                              weights=[45, 30, 15, 10])[0]
    truly_live = random.random() < 0.62
    paused = (not truly_live) and random.random() < 0.28
    churned_on = None
    if not truly_live and not paused:
        churned_on = AS_OF - timedelta(days=random.randint(5, 700))

    companies.append({
        "cid": i,
        "canonical": canonical,
        "accented": accented,
        "sector": random.choice(SECTORS),
        "signed": signed,
        "contract": contract,
        "truly_live": truly_live,
        "paused": paused,
        "churned_on": churned_on,
        "mrr": round(random.choice([0, 0, 250, 400, 750, 1200, 2400, 5000, 9000])
                     * random.uniform(0.85, 1.15), 2),
    })

# ------------------------------------------------------------------ CRM system
# Salesforce-shaped. Owns "status" as a hand-maintained picklist, which is the
# single most common source of a wrong customer count in real life: nobody's job
# is to close a record when a customer quietly stops.

crm_rows = []
crm_by_cid = {}
next_crm = 100000

crm_pop = set(random.sample(range(N_COMPANIES), int(N_COMPANIES * 0.958)))
dupe_in_crm = set(random.sample(sorted(crm_pop), 60))

for c in companies:
    if c["cid"] not in crm_pop:
        continue
    n_rows = 2 if c["cid"] in dupe_in_crm else 1
    for k in range(n_rows):
        next_crm += 1
        mode = random.choices(
            ["exact", "drop_suffix", "expand", "punct", "upper", "dba", "amp"],
            weights=[62, 9, 8, 8, 5, 4, 4])[0]
        name = vary_name(c["canonical"], "exact" if k == 0 else mode)

        # Status drifts from reality. This is deliberate and it is realistic.
        if c["churned_on"] is not None:
            status = random.choices(["Churned", "Active", "Inactive", ""],
                                    weights=[64, 22, 10, 4])[0]
        elif c["paused"]:
            status = random.choices(["Active", "Inactive", "", "Churned"],
                                    weights=[55, 28, 12, 5])[0]
        else:
            status = random.choices(["Active", "", "Inactive"],
                                    weights=[88, 8, 4])[0]

        # The duplicate row is usually the stale one.
        if k == 1:
            status = random.choices(["Inactive", "Churned", "Active", ""],
                                    weights=[40, 30, 22, 8])[0]

        mrr = c["mrr"] if (k == 0 and status == "Active") else (
            c["mrr"] if k == 0 else round(c["mrr"] * random.uniform(0, 0.4), 2))

        crm_rows.append({
            "account_id": crm_id(next_crm),
            "account_name": name,
            "email_domain": slugify(c["canonical"].split()[0]) + ".com",
            "sector": c["sector"],
            "created_date": (c["signed"] - timedelta(days=random.randint(0, 45))).isoformat(),
            "account_status": status,
            "plan_tier": random.choice(["Starter", "Growth", "Growth", "Enterprise"]),
            "mrr_usd": "%.2f" % mrr,
            "owner": random.choice(["a.reyes", "j.whitfield", "s.okoro", "m.tan",
                                    "d.castellanos", "p.lindqvist"]),
            "_cid": c["cid"],
        })
        crm_by_cid.setdefault(c["cid"], []).append(crm_rows[-1])

# -------------------------------------------------------------- billing system
# Stripe-shaped. Owns money, knows nothing about intent. No key back to CRM.

bill_rows = []
inv_rows = []
next_bill = 500000
next_inv = 1

bill_pop = set(random.sample(range(N_COMPANIES), int(N_COMPANIES * 0.933)))
split_billing = set(random.sample(sorted(bill_pop), 25))

for c in companies:
    if c["cid"] not in bill_pop:
        continue
    n_rows = 2 if c["cid"] in split_billing else 1
    for k in range(n_rows):
        next_bill += 1
        mode = random.choices(
            ["exact", "drop_suffix", "expand", "punct", "upper", "amp"],
            weights=[40, 16, 14, 14, 8, 8])[0]
        name = vary_name(c["canonical"], mode)
        # Billing strips diacritics. This is the silent killer on a name join.
        if c["accented"]:
            name = strip_accents(name)
        if k == 1:
            name = name + " - " + random.choice(["EMEA", "LATAM", "Subsidiary", "Div 2"])

        ref = bill_ref(next_bill)
        first = c["signed"] + timedelta(days=random.randint(0, 20))

        # Invoice cadence follows the CONTRACT, not the CRM status. An annual
        # customer who paid ten months ago looks dead to a 90-day rule and is not.
        step = {"monthly": 30, "annual": 365, "usage": 30}[c["contract"]]
        end = c["churned_on"] if c["churned_on"] else AS_OF
        if c["paused"]:
            end = min(end, AS_OF - timedelta(days=random.randint(95, 260)))

        d = first
        last_paid = None
        while d <= end:
            amt = max(0.0, (c["mrr"] if c["mrr"] else 300) *
                      (12 if c["contract"] == "annual" else 1) *
                      random.uniform(0.9, 1.1) / (n_rows if n_rows > 1 else 1))
            status = random.choices(["paid", "paid", "paid", "paid", "paid",
                                     "refunded", "void", "failed"],
                                    weights=[70, 8, 7, 5, 4, 3, 2, 1])[0]
            inv_rows.append({
                "invoice_id": "in_%09d" % next_inv,
                "customer_ref": ref,
                "invoice_date": d.isoformat(),
                "amount_usd": "%.2f" % amt,
                "status": status,
                "currency": "USD",
            })
            next_inv += 1
            if status == "paid":
                last_paid = d
            d = d + timedelta(days=step + random.randint(-3, 3))

        bill_rows.append({
            "customer_ref": ref,
            "company_name": name,
            "billing_email": "ap@" + slugify(c["canonical"].split()[0]) + ".com",
            "first_invoice_date": first.isoformat(),
            "last_paid_invoice_date": last_paid.isoformat() if last_paid else "",
            "contract_type": c["contract"],
            "_cid": c["cid"],
        })

# ------------------------------------------------------------ product telemetry
# Third opinion, and the one that most often disagrees with both. Keyed on an
# org slug that matches NEITHER system.

usage_rows = []
for c in companies:
    if c["cid"] not in bill_pop and c["cid"] not in crm_pop:
        continue
    slug = slugify(c["canonical"])
    if c["truly_live"]:
        days_back, density = 400, 0.55
    elif c["paused"]:
        days_back, density = 400, 0.06
    else:
        days_back, density = 400, 0.10
    for back in range(days_back):
        d = AS_OF - timedelta(days=back)
        if c["churned_on"] and d > c["churned_on"] + timedelta(days=random.randint(0, 40)):
            continue
        if c["paused"] and back < random.randint(60, 150):
            continue
        if random.random() < density:
            usage_rows.append({
                "org_slug": slug,
                "event_date": d.isoformat(),
                "active_users": random.randint(1, 40),
                "sessions": random.randint(1, 120),
            })

# ------------------------------------------------------------------------ write

def write(name, rows, fields):
    p = os.path.join(OUT, name)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return p, len(rows)


random.shuffle(crm_rows)
random.shuffle(bill_rows)

outputs = [
    write("crm_accounts.csv", crm_rows,
          ["account_id", "account_name", "email_domain", "sector", "created_date",
           "account_status", "plan_tier", "mrr_usd", "owner"]),
    write("billing_customers.csv", bill_rows,
          ["customer_ref", "company_name", "billing_email", "first_invoice_date",
           "last_paid_invoice_date", "contract_type"]),
    write("billing_invoices.csv", inv_rows,
          ["invoice_id", "customer_ref", "invoice_date", "amount_usd", "status", "currency"]),
    write("product_usage.csv", usage_rows,
          ["org_slug", "event_date", "active_users", "sessions"]),
]

# ------------------------------------------------- the four defensible answers

crm_active = sum(1 for r in crm_rows if r["account_status"] == "Active")
crm_active_dedup = len({r["_cid"] for r in crm_rows if r["account_status"] == "Active"})

paid90 = set()
for r in inv_rows:
    if r["status"] == "paid" and date.fromisoformat(r["invoice_date"]) >= AS_OF - timedelta(days=90):
        paid90.add(r["customer_ref"])
bill_cid = {b["customer_ref"]: b["_cid"] for b in bill_rows}
billing_active = len(paid90)
billing_active_dedup = len({bill_cid[r] for r in paid90})

used30 = {u["org_slug"] for u in usage_rows
          if date.fromisoformat(u["event_date"]) >= AS_OF - timedelta(days=30)}
product_active = len(used30)

mrr_active = len({r["_cid"] for r in crm_rows
                  if float(r["mrr_usd"]) > 0 and r["account_status"] != "Churned"})

truth = sum(1 for c in companies if c["truly_live"])

print("as of %s   seed %d" % (AS_OF.isoformat(), SEED))
for p, n in outputs:
    print("  %-24s %7d rows" % (os.path.basename(p), n))
print()
print("HOW MANY CUSTOMERS DO YOU HAVE?")
print("  CRM status = Active (rows)            %5d" % crm_active)
print("  CRM status = Active (dedup entities)  %5d" % crm_active_dedup)
print("  Billing: paid invoice in last 90d     %5d   (dedup %d)" % (billing_active, billing_active_dedup))
print("  Product: any usage in last 30d        %5d" % product_active)
print("  MRR > 0 and not Churned               %5d" % mrr_active)
print("  --- ground truth (answer key only) -- %5d" % truth)
