#!/usr/bin/env python3
"""
Charts for the customer base audit, rendered from <company>/out/*.csv to <company>/charts/*.png.

    pip install matplotlib pandas
    python audit/charts.py company2

Every chart reads a CSV that audit/run.py wrote; nothing is computed here beyond reshaping.
Sized for a 16:9 slide. Fonts: Archivo and Oswald when the TTFs are found (set FONT_DIR or
drop them in audit/fonts/), else the system sans.
"""
import os
import sys
import pathlib
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
if len(sys.argv) < 2 or not (REPO / sys.argv[1]).is_dir():
    sys.exit("usage: python audit/charts.py <company-dir>")
COMPANY = REPO / sys.argv[1]
OUT = COMPANY / "out"
CHARTS = COMPANY / "charts"
CHARTS.mkdir(exist_ok=True)

# ------------------------------------------------------------------ palette (validated)
SURFACE = "#FAF9F7"
INK = "#0A2838"
INK2 = "#565350"
MUTED = "#97928A"
GRID = "#E4E2DD"
BLUE, ORANGE, VIOLET, GREEN = "#1F84B2", "#E07A2F", "#8A6BC1", "#1E9E5A"
BLUE_DEEP = "#1A658F"
CONTRACT = {"annual": BLUE, "monthly": ORANGE, "usage": VIOLET, "(unmatched)": MUTED}
TIER = {"Enterprise": BLUE, "Growth": VIOLET, "Starter": ORANGE, "(unmatched)": MUTED}
SEQ = ["#EAF2F7", "#CADEEB", "#9CC2D8", "#6BA3C2", "#3E83A6", "#1A658F", "#114561", "#0A2838"]

# ------------------------------------------------------------------ fonts
def register_fonts():
    candidates = [os.environ.get("FONT_DIR"), HERE / "fonts",
                  pathlib.Path.home() / "GitHub/fra-strategy/brand/fractionalytics/glow-up/fonts"]
    for d in candidates:
        if d and pathlib.Path(d).is_dir():
            for f in pathlib.Path(d).glob("*.ttf"):
                font_manager.fontManager.addfont(str(f))
            return True
    return False

HAVE_BRAND_FONTS = register_fonts()
BODY = "Archivo" if HAVE_BRAND_FONTS else "DejaVu Sans"
DISPLAY = "Oswald" if HAVE_BRAND_FONTS else "DejaVu Sans"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": BODY, "font.size": 11, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": GRID, "axes.linewidth": 1, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 10, "ytick.labelsize": 10,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1, "axes.axisbelow": True,
    "legend.frameon": False, "legend.fontsize": 10,
})

def read(name):
    return pd.read_csv(OUT / f"{name}.csv")

def fig(w=12, h=6.75):
    return plt.figure(figsize=(w, h), dpi=160)

import textwrap

def title(ax, text, sub=None):
    f = ax.figure
    f.suptitle(text, fontfamily=DISPLAY, fontsize=19, fontweight="semibold", x=0.01, y=0.985, ha="left", va="top", color=INK)
    if sub:
        f.text(0.01, 0.925, textwrap.fill(sub, 150), fontsize=10.5, color=INK2, va="top", linespacing=1.4)

def head(f, text, sub):
    f.suptitle(text, fontfamily=DISPLAY, fontsize=19, fontweight="semibold", x=0.01, y=0.985, ha="left", va="top", color=INK)
    f.text(0.01, 0.925, textwrap.fill(sub, 170), fontsize=10.5, color=INK2, va="top", linespacing=1.4)

def finish(name):
    plt.tight_layout(rect=(0, 0, 1, 0.88))
    p = CHARTS / f"{name}.png"
    plt.savefig(p, dpi=160)
    plt.close()
    print("  wrote", p.name)

def money(x, _=None):
    return f"${x/1e6:.1f}M" if abs(x) >= 1e6 else (f"${x/1e3:.0f}K" if abs(x) >= 1e3 else f"${x:.0f}")

def pct(x, _=None):
    return f"{x:.0f}%"

def months_last(df, n=24, col="month"):
    df = df.copy()
    df[col] = pd.to_datetime(df[col])
    df = df[df[col] < df[col].max()]            # drop the partial as-of month
    return df[df[col] >= df[col].max() - pd.DateOffset(months=n - 1)]

def stacked_ga(ax, d, pos, neg, colors, xcol="month"):
    """Stacked growth-accounting columns: positives up from zero, negatives down."""
    x = range(len(d))
    bottom = pd.Series(0.0, index=d.index)
    for c in pos:
        v = d[c].fillna(0)
        ax.bar(x, v, bottom=bottom, color=colors[c], width=0.72, label=c.replace("_", " "), linewidth=0)
        bottom = bottom + v
    bottom = pd.Series(0.0, index=d.index)
    for c in neg:
        v = d[c].fillna(0)
        ax.bar(x, v, bottom=bottom, color=colors[c], width=0.72, label=c.replace("_", " "), linewidth=0)
        bottom = bottom + v
    ax.axhline(0, color=MUTED, linewidth=1)
    labels = [t.strftime("%b %y") if i % 6 == 0 else "" for i, t in enumerate(d[xcol])]
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.grid(axis="x", visible=False)

# ------------------------------------------------------------------ 1. the counts
def chart_count_rules():
    r = read("01_customer_count__count_rules")
    board = read("08_data_condition__board_vs_systems_monthly")
    if len(board):
        r = pd.concat([r, pd.DataFrame([{"ord": 12, "rule": "Board pack, latest month", "n": int(board.iloc[-1]["board_customers"])}])])
    r = r.sort_values("n")
    f = fig(); ax = f.add_subplot(111)
    defended = r["rule"].str.startswith("Billing: contract-aware")
    colors = [BLUE if d else "#BBB7AD" for d in defended]
    ax.barh(r["rule"], r["n"], color=colors, height=0.62, linewidth=0)
    for y, (v, d) in enumerate(zip(r["n"], defended)):
        ax.text(v + 12, y, f"{v:,}", va="center", fontsize=10.5, color=INK, fontweight="bold" if d else "normal")
    ax.set_xlim(0, r["n"].max() * 1.12)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    title(ax, "How many customers? Twelve answers, all defensible",
          "Each rule is true under its own definition. The highlighted one is the count the audit defends, with the definition written next to it.")
    finish("01_count_rules")

# ------------------------------------------------------------------ 2. concentration
def chart_lorenz():
    d = read("02_concentration__lorenz_curve")
    top = read("02_concentration__top_n_share")
    f = fig(11, 6.75); ax = f.add_subplot(111)
    x = [0] + list(d["top_pct_of_customers"]); y = [0] + list(d["revenue_share_pct"])
    ax.plot(x, y, color=BLUE, linewidth=2.2)
    ax.plot([0, 100], [0, 100], color=GRID, linewidth=1)
    ax.fill_between(x, y, [i for i in x], color=BLUE, alpha=0.08, linewidth=0)
    ax.scatter([20], [d.loc[d.top_pct_of_customers == 20, "revenue_share_pct"].iloc[0]], s=70, color=BLUE, zorder=5, edgecolor=SURFACE, linewidth=2)
    v20 = d.loc[d.top_pct_of_customers == 20, "revenue_share_pct"].iloc[0]
    v10 = d.loc[d.top_pct_of_customers == 10, "revenue_share_pct"].iloc[0]
    ax.annotate(f"Top 20% of customers carry {v20:.0f}% of revenue", (20, v20), (30, v20 - 14), fontsize=11, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
    ax.annotate(f"Top 10%: {v10:.0f}%", (10, v10), (22, v10 - 22), fontsize=10.5, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
    t10 = top.loc[top.top_n == 10, "share_by_customer_ref_pct"].iloc[0]
    t1 = top.loc[top.top_n == 1, "share_by_customer_ref_pct"].iloc[0]
    ax.text(62, 12, f"Top 10 customers: {t10:.1f}%\nLargest customer: {t1:.1f}%", fontsize=11, color=INK, va="bottom",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=SURFACE, edgecolor=GRID))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel("Customers, ranked largest first (%)"); ax.set_ylabel("Share of trailing-twelve-month paid revenue")
    ax.xaxis.set_major_formatter(FuncFormatter(pct)); ax.yaxis.set_major_formatter(FuncFormatter(pct))
    title(ax, "Concentration first: a normal mid-market book", "Trailing twelve months of paid invoices, billing grain. The diagonal is perfectly even revenue.")
    finish("02_lorenz")

def chart_top10():
    d = read("02_concentration__top_10_customers").iloc[::-1]
    f = fig(12, 6.5); ax = f.add_subplot(111)
    colors = [CONTRACT[c] for c in d["contract_type"]]
    ax.barh(d["company_name"].str.title(), d["ttm_usd"], color=colors, height=0.62, linewidth=0)
    for y, (v, s) in enumerate(zip(d["ttm_usd"], d["share_pct"])):
        ax.text(v + 15000, y, f"{money(v)}  ({s:.1f}%)", va="center", fontsize=10.5, color=INK)
    ax.set_xlim(0, d["ttm_usd"].max() * 1.28)
    ax.xaxis.set_major_formatter(FuncFormatter(money)); ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=CONTRACT[k]) for k in ("annual", "monthly", "usage")]
    ax.legend(handles, ["Annual contract", "Monthly contract", "Usage contract"], loc="lower right")
    n_not_annual = int((d["contract_type"] != "annual").sum())
    title(ax, "The ten largest customers, and how they are held",
          f"{n_not_annual} of the ten are not on annual contracts. Trailing twelve months of paid invoices.")
    finish("03_top10")

# ------------------------------------------------------------------ 3. revenue growth accounting
def chart_rev_ga_by_contract():
    d = read("03_revenue_growth_accounting__rev_ga_by_contract_monthly")
    d["month"] = pd.to_datetime(d["month"])
    d = d[d["month"] < d["month"].max()]
    d = d[d["month"] >= d["month"].max() - pd.DateOffset(months=23)]
    colors = {"new_rev": BLUE, "expansion_rev": GREEN, "resurrected_rev": VIOLET, "contraction_rev": "#C7882B", "churned_rev": ORANGE}
    f = fig(14, 7)
    for i, ct in enumerate(["annual", "monthly", "usage"]):
        ax = f.add_subplot(1, 3, i + 1)
        s = d[d.contract_type == ct].reset_index(drop=True)
        stacked_ga(ax, s, ["new_rev", "expansion_rev", "resurrected_rev"], ["contraction_rev", "churned_rev"], colors)
        ax.yaxis.set_major_formatter(FuncFormatter(money))
        qr = (s["new_rev"].fillna(0) + s["expansion_rev"].fillna(0) + s["resurrected_rev"].fillna(0)).sum() / -(s["churned_rev"].fillna(0) + s["contraction_rev"].fillna(0)).sum()
        ax.set_title(f"{ct.title()} contracts   quick ratio {qr:.1f}", fontfamily=DISPLAY, fontsize=14, loc="left", color=INK)
        if i == 1:
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=5, frameon=False)
    head(f, "Revenue growth accounting, by contract type. Recognized basis, last 24 complete months", "New, expansion and resurrected revenue above the line; contraction and churn below. Annual revenue only moves at renewal; usage revenue moves every month.")
    plt.tight_layout(rect=(0, 0.04, 1, 0.88))
    p = CHARTS / "04_rev_ga_by_contract.png"; plt.savefig(p, dpi=160); plt.close(); print("  wrote", p.name)

def chart_nrr_by_contract():
    d = read("03_revenue_growth_accounting__nrr_by_contract_monthly")
    d["base_month"] = pd.to_datetime(d["base_month"])
    d = d[d["base_month"] >= d["base_month"].max() - pd.DateOffset(months=23)]
    f = fig(); ax = f.add_subplot(111)
    ax.axhspan(90, 110, color=BLUE, alpha=0.06, linewidth=0)
    ax.text(d["base_month"].min(), 110.6, "Lenny's benchmark for mid-market SaaS: 90% good, 110% great", fontsize=9.5, color=INK2, va="bottom")
    for ct in ("annual", "usage", "monthly"):
        s = d[d.contract_type == ct]
        ax.plot(s["base_month"], s["nrr_pct"], color=CONTRACT[ct], linewidth=2.2, label=f"{ct.title()} contracts")
        ax.text(s["base_month"].iloc[-1] + pd.Timedelta(days=12), s["nrr_pct"].iloc[-1], f"{ct} {s['nrr_pct'].iloc[-1]:.0f}%", fontsize=10, color=INK, va="center")
    ax.set_ylim(50, 140); ax.yaxis.set_major_formatter(FuncFormatter(pct))
    ax.set_xlim(d["base_month"].min(), d["base_month"].max() + pd.Timedelta(days=150))
    ax.legend(loc="lower left")
    ax.set_xlabel("Base month (retention measured twelve months later)")
    title(ax, "Net revenue retention by contract type", "Revenue twelve months later from the customers paying in the base month, recognized basis. Usage contracts are 62 customers, so their line is noisy by construction.")
    finish("05_nrr_by_contract")

def chart_cash_vs_recognized():
    d = read("03_revenue_growth_accounting__nrr_cash_vs_recognized")
    d["base_month"] = pd.to_datetime(d["base_month"])
    f = fig(); ax = f.add_subplot(111)
    ax.plot(d["base_month"], d["nrr_recognized_pct"], color=BLUE, linewidth=2.4, label="Recognized basis")
    ax.plot(d["base_month"], d["nrr_cash_pct"], color=ORANGE, linewidth=2, label="Cash basis, same invoices")
    ax.yaxis.set_major_formatter(FuncFormatter(pct)); ax.legend(loc="lower left")
    ax.set_xlabel("Base month")
    title(ax, "Same invoices, two answers: NRR on cash against recognized revenue",
          "An annual customer pays once a year. On cash, every renewal month is a churn and a resurrection.")
    finish("06_cash_vs_recognized")

# ------------------------------------------------------------------ 4. cohorts
def chart_cohort_heatmap():
    d = read("05_cohorts__cohort_quarterly_logo_retention")
    d = d[d.cohort_q != d.cohort_q.max()]
    cols = [c for c in d.columns if c.startswith("m")]
    m = d.set_index("cohort_q")[cols]
    f = fig(12, 7.5); ax = f.add_subplot(111)
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", SEQ[1:])
    vals = m.values.astype(float)
    ax.imshow(np.where(np.isnan(vals), np.nan, vals), cmap=cmap, vmin=30, vmax=100, aspect="auto")
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9.5, color=SURFACE if v > 72 else INK)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels([f"m{int(c[1:])}" for c in cols])
    ax.set_yticks(range(len(m))); ax.set_yticklabels([pd.to_datetime(q).strftime("%Y Q") + str((pd.to_datetime(q).month - 1) // 3 + 1) for q in m.index])
    ax.grid(False); ax.set_xlabel("Months since first revenue")
    for s in ax.spines.values():
        s.set_visible(False)
    title(ax, "Logo retention by quarterly cohort (%)", "Recognized basis, months since first revenue. A horizon shows only when every monthly cohort in the quarter has reached it. 2022 Q4 is the legacy migration.")
    finish("07_cohort_heatmap")

def chart_retention_by_tier():
    d = read("07_segments__retention_by_plan_tier")
    d = d[d.segment.isin(["Starter", "Growth", "Enterprise"])].set_index("segment").loc[["Starter", "Growth", "Enterprise"]]
    f = fig(11, 6.5); ax = f.add_subplot(111)
    metrics = [("logo_retention_12m_pct", "Logo retention", BLUE), ("grr_12m_pct", "Gross revenue retention", VIOLET), ("nrr_12m_pct", "Net revenue retention", ORANGE)]
    w = 0.24
    for k, (col, lab, color) in enumerate(metrics):
        xs = [i + (k - 1) * w for i in range(len(d))]
        ax.bar(xs, d[col], width=w - 0.02, color=color, label=lab, linewidth=0)
        for x, v in zip(xs, d[col]):
            ax.text(x, v + 1.2, f"{v:.0f}%", ha="center", fontsize=10, color=INK)
    ax.set_xticks(range(len(d))); ax.set_xticklabels([f"{t}\n({n} in base)" for t, n in zip(d.index, d["customers_in_base"])])
    ax.set_ylim(0, 118); ax.yaxis.set_major_formatter(FuncFormatter(pct)); ax.grid(axis="x", visible=False)
    ax.axhline(100, color=MUTED, linewidth=1, linestyle=(0, (4, 4)))
    ax.legend(loc="upper left", ncol=3)
    title(ax, "Twelve-month retention rises with customer size", "Base months in the last 24; plan tier from the CRM through the entity resolver.")
    finish("08_retention_by_tier")

# ------------------------------------------------------------------ 5. telemetry
def chart_org_and_seat_ga():
    o = months_last(read("04_user_growth_accounting__user_ga_monthly"), 24).reset_index(drop=True)
    s = months_last(read("04_user_growth_accounting__seat_ga_monthly"), 24).reset_index(drop=True)
    f = fig(14, 6.75)
    ax = f.add_subplot(1, 2, 1)
    stacked_ga(ax, o, ["new_orgs", "resurrected_orgs"], ["churned_orgs"], {"new_orgs": BLUE, "resurrected_orgs": VIOLET, "churned_orgs": ORANGE})
    ax.set_title(f"Organizations   {int(o['active_orgs'].iloc[-1]):,} active in {o['month'].iloc[-1]:%b %Y}", fontfamily=DISPLAY, fontsize=14, loc="left", color=INK)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    ax = f.add_subplot(1, 2, 2)
    stacked_ga(ax, s, ["new_seats", "expansion_seats", "resurrected_seats"], ["contraction_seats", "churned_seats"],
               {"new_seats": BLUE, "expansion_seats": GREEN, "resurrected_seats": VIOLET, "contraction_seats": "#C7882B", "churned_seats": ORANGE})
    ax.set_title(f"Seats in use   {int(s['seats'].iloc[-1]):,} in {s['month'].iloc[-1]:%b %Y}", fontfamily=DISPLAY, fontsize=14, loc="left", color=INK)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=5)
    head(f, "Growth accounting from the product telemetry, last 24 complete months", "Left: organizations that logged in. Right: each organization's peak daily active users, the closest the log gets to an end-user count. New above the line, lost below.")
    plt.tight_layout(rect=(0, 0.04, 1, 0.88))
    p = CHARTS / "09_org_and_seat_ga.png"; plt.savefig(p, dpi=160); plt.close(); print("  wrote", p.name)

# ------------------------------------------------------------------ 6. CAC and payback
def chart_cac_payback():
    c = read("06_clv_payback__cac_by_quarter_two_denominators"); c["quarter"] = pd.to_datetime(c["quarter"])
    c = c[c["quarter"] > c["quarter"].min()]          # drop the migration quarter
    p = read("06_clv_payback__payback_by_cohort_quarter"); p["quarter"] = pd.to_datetime(p["quarter"])
    p = p[p["quarter"] > p["quarter"].min()]
    f = fig(14, 6.75)
    ax = f.add_subplot(1, 2, 1)
    ax.plot(c["quarter"], c["cac_per_billing_customer"], color=BLUE, linewidth=2.2, marker="o", markersize=5, markeredgecolor=SURFACE, label="Spend per new billing customer")
    ax.plot(c["quarter"], c["cac_per_crm_account"], color=ORANGE, linewidth=2, marker="o", markersize=5, markeredgecolor=SURFACE, label="Spend per new CRM account")
    ax.yaxis.set_major_formatter(FuncFormatter(money)); ax.set_ylim(0, None); ax.legend(loc="lower right")
    ax.set_title("Cohort CAC, two denominators", fontfamily=DISPLAY, fontsize=14, loc="left", color=INK)
    ax = f.add_subplot(1, 2, 2)
    pb = p.dropna(subset=["payback_months"])
    ax.bar(range(len(pb)), pb["payback_months"], color=BLUE, width=0.62, linewidth=0)
    for x, v in enumerate(pb["payback_months"]):
        ax.text(x, v + 0.3, f"{int(v)}", ha="center", fontsize=10, color=INK)
    ax.set_xticks(range(len(pb))); ax.set_xticklabels([f"{q.year} Q{(q.month-1)//3+1}" for q in pb["quarter"]], rotation=45, ha="right")
    ax.grid(axis="x", visible=False); ax.set_ylabel("Months")
    ax.set_title("Payback, months to recover cohort CAC from recognized revenue", fontfamily=DISPLAY, fontsize=14, loc="left", color=INK)
    head(f, "What it costs to acquire a customer, and how long it takes to earn it back", "Marketing spend lagged one month over new customers in the quarter. The two denominators disagree by up to 65 percent; neither excludes the acquired books, because nothing in the files flags them.")
    plt.tight_layout(rect=(0, 0.04, 1, 0.88))
    q = CHARTS / "10_cac_payback.png"; plt.savefig(q, dpi=160); plt.close(); print("  wrote", q.name)

# ------------------------------------------------------------------ 7. mix shift
def chart_mix_shift():
    d = read("07_segments__new_customers_by_quarter_and_tier"); d["quarter"] = pd.to_datetime(d["quarter"])
    d = d[(d["quarter"] > d["quarter"].min()) & (d["quarter"] < d["quarter"].max())]
    m = d.pivot(index="quarter", columns="plan_tier", values="new_customers").fillna(0)
    share = m.div(m.sum(axis=1), axis=0) * 100
    order = [t for t in ["Starter", "Growth", "Enterprise", "(unmatched)"] if t in share.columns]
    f = fig(); ax = f.add_subplot(111)
    bottom = pd.Series(0.0, index=share.index)
    x = range(len(share))
    for t in order:
        ax.bar(x, share[t], bottom=bottom, color=TIER[t], width=0.72, label=t if t != "(unmatched)" else "Unmatched to CRM", linewidth=0)
        bottom = bottom + share[t]
    for i, q in enumerate(share.index):
        ax.text(i, share.loc[q, "Starter"] / 2, f"{share.loc[q, 'Starter']:.0f}%", ha="center", va="center", fontsize=9.5, color=SURFACE)
    ax.set_xticks(list(x)); ax.set_xticklabels([f"{q.year} Q{(q.month-1)//3+1}" for q in share.index], rotation=45, ha="right")
    ax.set_ylim(0, 100); ax.yaxis.set_major_formatter(FuncFormatter(pct)); ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", ncol=4, bbox_to_anchor=(0, -0.18))
    title(ax, "New customers by plan tier: the mix is moving down-market", "Share of each quarter's new billing customers by CRM plan tier. Retention inside a tier is flat; the blended number moves because this does.")
    finish("11_mix_shift")

# ------------------------------------------------------------------ 8. the board pack
def chart_board_vs_systems():
    d = read("08_data_condition__board_vs_systems_monthly")
    if not len(d):
        return
    d["month"] = pd.to_datetime(d["month"])
    f = fig(14, 6.75)
    ax = f.add_subplot(1, 2, 1)
    ax.plot(d["month"], d["board_customers"], color=ORANGE, linewidth=2.4, label="Board pack: customers")
    ax.plot(d["month"], d["billing_recognized_payers"], color=BLUE, linewidth=2, label="Billing: customers with recognized revenue")
    ax.plot(d["month"], d["telemetry_active_orgs"], color=VIOLET, linewidth=2, label="Telemetry: active organizations")
    ax.legend(loc="upper left"); ax.set_ylim(0, None)
    gap = d["board_over_billing_pct"].iloc[-6:].mean()
    ax.set_title(f"Customer count: the pack runs {gap:.0f}% above billing", fontfamily=DISPLAY, fontsize=14, loc="left", color=INK)
    ax = f.add_subplot(1, 2, 2)
    ax.plot(d["month"], d["board_revenue"], color=ORANGE, linewidth=2.4, label="Board pack: revenue")
    ax.plot(d["month"], d["billing_cash_rev"], color=MUTED, linewidth=1.6, label="Billing: cash collected")
    ax.plot(d["month"], d["billing_recognized_rev"], color=BLUE, linewidth=2, label="Billing: recognized")
    sw = d.loc[d["board_revenue_basis"].ne(d["board_revenue_basis"].shift()) & (d.index > 0), "month"]
    for m in sw:
        ax.axvline(m, color=INK2, linewidth=1, linestyle=(0, (4, 4)))
        ax.text(m + pd.Timedelta(days=10), ax.get_ylim()[1] * 0.02 if False else d["board_revenue"].max() * 0.06, f"basis switches\n{m:%b %Y}", fontsize=9.5, color=INK2)
    ax.yaxis.set_major_formatter(FuncFormatter(money)); ax.legend(loc="upper left"); ax.set_ylim(0, None)
    ax.set_title("Revenue: cash for 29 months, then recognized, and nothing says so", fontfamily=DISPLAY, fontsize=14, loc="left", color=INK)
    head(f, "The board pack against the systems it was built from", "Forty-six monthly packs, each assembled by hand from whatever the CRM said on the day. No month can be reproduced from any system.")
    plt.tight_layout(rect=(0, 0.04, 1, 0.88))
    p = CHARTS / "12_board_vs_systems.png"; plt.savefig(p, dpi=160); plt.close(); print("  wrote", p.name)

# ------------------------------------------------------------------ 9. the acquired books
def chart_acquired():
    d = read("07_segments__retention_acquired_vs_organic")
    if len(d) < 2:
        return
    order = ["organic"] + [s for s in d.segment if s != "organic"]
    d = d.set_index("segment").loc[order]
    f = fig(11, 6.5); ax = f.add_subplot(111)
    w = 0.36
    for k, (col, lab, color) in enumerate([("logo_retention_12m_pct", "Logo retention", BLUE), ("nrr_12m_pct", "Net revenue retention", ORANGE)]):
        xs = [i + (k - 0.5) * w for i in range(len(d))]
        ax.bar(xs, d[col], width=w - 0.03, color=color, label=lab, linewidth=0)
        for x, v in zip(xs, d[col]):
            ax.text(x, v + 1.2, f"{v:.0f}%", ha="center", fontsize=10, color=INK)
    ax.set_xticks(range(len(d))); ax.set_xticklabels([f"{s.title()}\n({n} in base)" for s, n in zip(d.index, d["customers_in_base"])])
    ax.set_ylim(0, 118); ax.yaxis.set_major_formatter(FuncFormatter(pct)); ax.grid(axis="x", visible=False)
    ax.axhline(100, color=MUTED, linewidth=1, linestyle=(0, (4, 4))); ax.legend(loc="upper right", ncol=2)
    title(ax, "The acquired books retain worse, and only the schedules show it", "Twelve-month retention, base months in the last 24. Nothing in the five system files identifies an acquired customer; the seller's schedules do.")
    finish("13_acquired_vs_organic")

# ------------------------------------------------------------------ 0. the shape of the business
def chart_revenue_shape():
    d = read("03_revenue_growth_accounting__rev_ga_recognized_monthly"); d["month"] = pd.to_datetime(d["month"])
    d = d[d["month"] < d["month"].max()]
    f = fig(); ax = f.add_subplot(111)
    ax.fill_between(d["month"], d["revenue"], color=BLUE, alpha=0.1, linewidth=0)
    ax.plot(d["month"], d["revenue"], color=BLUE, linewidth=2.2)
    ax.text(d["month"].iloc[-1], d["revenue"].iloc[-1] * 1.03, f"{money(d['revenue'].iloc[-1])} / month\n{int(d['paying_customers'].iloc[-1]):,} paying customers", fontsize=10.5, color=INK, ha="right", va="bottom")
    ax.yaxis.set_major_formatter(FuncFormatter(money)); ax.set_ylim(0, d["revenue"].max() * 1.25)
    title(ax, "Monthly recognized revenue, rebuilt from the invoices", "Annual invoices spread over their twelve months. This is the series every customer metric below is computed on.")
    finish("00_revenue_shape")

if __name__ == "__main__":
    print(f"charts for {COMPANY.name} (brand fonts: {HAVE_BRAND_FONTS})")
    for fn in (chart_revenue_shape, chart_count_rules, chart_lorenz, chart_top10, chart_rev_ga_by_contract, chart_nrr_by_contract,
               chart_cash_vs_recognized, chart_cohort_heatmap, chart_retention_by_tier, chart_org_and_seat_ga, chart_cac_payback,
               chart_mix_shift, chart_board_vs_systems, chart_acquired):
        try:
            fn()
        except Exception as e:      # keep going; report what failed
            print(f"  FAILED {fn.__name__}: {e!r}")
