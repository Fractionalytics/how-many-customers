# Solutions

**This spoils the exercise. Run it first.**

Every number below was verified against the generated files, seed 20260820.

## Ground truth

**758 companies are genuinely live** as of 2026-08-20. That number appears in no file and cannot be
derived from the data, which is the entire point. The generator knows it (`truly_live`) and never
writes it out. The full split is 758 live, 135 paused, 307 churned.

## The defensible answers

| Definition | Answer | Why it is wrong, and why it is defensible anyway |
|---|---|---|
| Product usage in last 30d | **770** | Closest to truth, and it OVERSHOOTS: churned accounts keep logging in for up to 40 days after the contract ends |
| CRM `account_status = 'Active'` (rows) | **756** | Right by accident. Two errors cancel: stale Active rows on churned accounts, minus 90 live accounts left blank |
| CRM Active, deduplicated to entities | **749** | A more rigorous method, and further from truth. Worth noticing |
| `mrr_usd > 0` and not Churned (rows) | **739** | |
| `mrr_usd > 0` and not Churned (entities) | **715** | Misses live customers whose MRR was never filled in |
| Paid invoice in last 90d (raw `customer_ref`) | **485** | |
| Paid invoice in last 90d (deduplicated) | **475** | The most rigorous-looking rule and the worst answer, off by 283 |

Note that the rows-versus-entities fork appears twice, and is silent both times.

### The 475 is the headline

It is low for a structural reason, not a data-quality one. **534 of the 1,144 billing rows are on
annual contracts, and 397 of those last paid more than 90 days ago.** A healthy customer who signed
an annual deal in November and paid up front is invisible to any 90-day rule in August.

A finance team would defend 475 to the death, and it would be wrong by more than a third of the
customer base. Nothing in the data is dirty. The rule is correct, the data is correct, and the
answer is badly wrong, because a fact that lives outside both (how this company treats an annual
customer between payments) was never written down.

## The traps

1. **No shared key.** `account_id` / `customer_ref` / `org_slug` share nothing. The only bridges are
   company name and email domain.

2. **The email domain is a trap dressed as a key.** It is derived from the FIRST WORD of the company
   name only, so there are **59 distinct domains across 1,209 CRM rows**. `whitmore.com` covers 38
   unrelated companies. Anything that joins on domain produces a plausible-looking result that is
   nonsense. Checking a candidate key's cardinality catches this in one query.

3. **Name variants across systems.** Suffix dropped, `Corp` expanded to `Corporation`, punctuation
   added, uppercased, `and` to `&`, and a `(DBA)` form. **407 of 1,097 billing rows (37%) differ
   from their CRM twin as raw strings, and 220 (20%) still differ after lowercasing, stripping
   punctuation and folding accents.** Those 220 are what actually break a join.

4. **DIACRITICS, and this is the one to watch hardest.** About 8% of companies carry accents (Peña,
   Muñoz, García, André, São, Núñez, Guimarães, Serviços). **CRM keeps them; billing strips them: 96
   accented CRM rows, 0 accented billing rows.** 74 companies match only if you fold before
   comparing. A matcher that filters to `[a-z]` before folding deletes the accented letter instead
   of folding it and drops those companies silently, with no error and no warning. They are
   overwhelmingly the Latin American and Iberian names, so the failure is both invisible and
   systematically biased against one part of the book.

   **There is a second-order trap here worth its own paragraph.** Folding accents recovers 79 more
   real matches. It also makes two folded keys collide, so a `join_one` fans out and the row count
   stops matching the source table. **The more correct join is the one that trips the alarm, and the
   accent-blind join is the one that looks validated.** Anything optimising for a clean,
   non-fanning join will prefer the worse answer. `join_one` is a declaration of belief, not an
   enforcement.

5. **Near-collisions: 15 planted, 276 present.** Genuinely different companies whose names differ by
   one token (same stem and middle, different suffix). `Harborview Supply LLC`, `Harborview Supply
   Group`, `Harborview Supply Holdings` and `Harborview Supply Labs` are four different companies.
   1,200 names drawn from 47 stems x 24 middles x 8 suffixes collide naturally far more often than
   the 15 that were deliberately planted.

   **A fuzzy matcher loose enough to catch trap 3 will merge these, and one tight enough to keep
   them apart will miss trap 3. Both errors cannot be avoided by tuning a threshold**, which is the
   point: the correct move is to surface the ambiguous pairs, not to pick a cutoff. Surfacing two
   hundred-odd ambiguous pairs is correct behaviour, not noise.

6. **60 companies have two CRM accounts** (re-entry and acquisition). The second row is usually the
   stale one. Counting rows instead of entities inflates by about 11.

   **The standard duplicate check does not catch this.** `group_by: pk, having: count() > 1` on
   `account_id` returns empty: 1,209 distinct ids for 1,209 rows, a clean primary key. The check
   finds row duplication, and the problem here is entity duplication, which no key can see.

7. **25 companies have two billing customers** (subsidiaries billed separately, marked EMEA / LATAM
   / Subsidiary / Div 2). **Whether that is one customer or two is a genuine business decision, not
   an error.** Neither answer is wrong. Someone has to choose.

8. **Annual contracts.** See the 475 above. The invoice cadence follows the contract type, not the
   CRM status.

9. **Paused customers.** Paying or recently paid, no usage for 60 to 150 days, contract still
   running. CRM usually still says Active. Live or not? Business decision.

10. **Invoice statuses.** 12,917 paid, 415 refunded, 306 void, 142 failed. Does a refunded invoice
    count toward revenue, or toward activity? Two defensible answers each.

11. **Blank `account_status`.** 90 rows, and not the same as `Inactive`. A blank means nobody ever
    touched the record, which correlates with self-serve signups that never got an owner. Treating
    blank as inactive loses real customers.

12. **Coverage cliffs.** 46 companies exist in billing but never in CRM, and 76 exist in CRM but
    were never billed. Prospects versus self-serve. Both are legitimately "not customers" or
    "customers" depending on the question. Separately, the invoice table holds only 1,042 distinct
    `customer_ref` against 1,144 billing customers, so 102 customers have never been invoiced.

13. **Marketing spend joins to nothing.** `marketing_spend.csv` is monthly and by channel: 282 rows,
    47 months, six channels, **$6,890,456 total**. There is no account-level cost anywhere, because
    real finance systems do not hold one. The only bridge to a customer is the CRM's `lead_source`,
    and traps 14 to 16 are about why that bridge does not hold weight.

    | Channel (finance's spelling) | Spend |
    |---|---|
    | Paid Search | $2,164,143 |
    | Outbound SDR | $1,315,361 |
    | Paid Social | $1,190,805 |
    | Events & Sponsorships | $971,731 |
    | Content & SEO | $759,378 |
    | Partner Program | $489,038 |

14. **The two sides do not share a vocabulary.** Finance books **six** channels. The CRM holds
    **23 distinct `lead_source` values**, because it is a free-text-ish picklist nobody normalised:
    `Google Ads`, `PPC`, `paid search` and `Paid Search` are four separate values for one channel,
    and events appear as `Event`, `Conference` and `Tradeshow`.

    **This is exactly trap 3, one system over.** Anyone who solved the company-name join and then
    joins spend to lead source on the raw channel string will silently drop most of the book. The
    mapping is a business decision (which CRM values roll up to which GL line) that exists in nobody's
    documentation.

15. **Last touch over-credits Direct and Organic, and `lead_source` is blank on half the book.**

    - **603 of 1,209 CRM rows have a blank `lead_source` (50%).** Of those, **520 predate
      2024-06-01**, when the field was added, and **83 are later rows nobody filled in.**
    - The blank half is not a random half. Mean `created_date` for a blank row is **2023-10-22**;
      for a tagged row it is **2025-06-09**. **Twenty months apart.** Mean MRR is nearly identical
      ($1,986 blank against $1,905 tagged), so the bias is not in deal size, it is in tenure: any
      channel analysis is computed entirely on the newest half of the customer base, and every
      conclusion about "what works" is a conclusion about the last fifteen months only.
    - Where a tag does exist, it is often the wrong one. Measured against the generator's ground
      truth, this share of each channel's genuinely-driven accounts is credited to `Direct` or an
      organic variant instead:

      | True channel | Misattributed | Rate |
      |---|---|---|
      | Events & Sponsorships | 22 of 62 | **35.5%** |
      | Paid Social | 25 of 71 | **35.2%** |
      | Paid Search | 37 of 140 | 26.4% |
      | Outbound SDR | 16 of 77 | 20.8% |
      | Partner Program | 13 of 88 | 14.8% |
      | Content & SEO | 7 of 112 | 6.2% |

      Events lose the most, which is the real-world pattern: somebody meets you at a conference and
      then signs up through a branded search three weeks later, so the conference gets no credit.
      **Content & SEO looks the most accurate and is not: it is the channel everything else leaks
      into, so it is flattered by the same mechanism that penalises events.**

16. **160 companies arrived by acquisition and cost nothing to acquire, and nothing flags them.**
    The company bought three smaller books: **Northgate (63), Pelham (52), Vireo (45)**. Those
    customers were never marketed to and belong in no CAC denominator.

    **The migration had to put something in the column, so 33 of them carry a marketing channel they
    never came from**, which inflates whichever channels they landed in. The rest are blank, and are
    therefore indistinguishable from trap 15's blanks.

    Consequence, and it is the one worth stating out loud:

    | Method | Result | Verdict |
    |---|---|---|
    | Spend / all 1,200 companies | **$5,742** | Wrong. Counts a book that cost nothing to acquire |
    | Spend / 1,040 non-acquired | **$6,625** | Better, and still not defensible |
    | Per channel | **not computable** | Traps 13, 14, 15 and 16 each independently break it |

    Even the $6,625 needs an agreed definition of "customer" in the denominator, which is question
    one. **CAC and payback inherit the definition problem rather than escaping it**, and payback
    fractures again on contract type: an annual customer who paid twelve months up front and a
    monthly customer at the same MRR have completely different payback curves, and a blended figure
    describes neither.

## The revenue question

The README suggests asking for a defensible trailing-twelve-month figure. Five answers:

| Definition | TTM |
|---|---|
| Cash, paid invoices only | $19,679,207 |
| Cash, paid + refunded | $20,414,502 |
| Cash, everything except failed | $20,683,219 |
| Amortized (annual invoices spread over 12 months) | $19,873,856 |
| ARR from CRM `Active` x `mrr_usd` x 12 | $18,365,859 |

**Spread: 12.6%.** Real, but much narrower than the customer count, where 475 to 770 is a 62% spread.
Treat revenue as the supporting exhibit and the customer count as the main one.

## What a good answer looks like

- surfaces the fork rather than picking a number
- catches the annual-contract interaction behind the 475
- folds diacritics without being told, and notices that doing so creates a fan-out
- refuses to merge the near-collisions, and says why
- asks who decides the parent-versus-subsidiary question
- checks the cardinality of a candidate join key before joining on it

## What a poor answer looks like

- returns one number with confidence
- silently drops the accented companies
- merges the near-collisions to raise its match rate
- treats blank status as inactive
- accepts an empty primary-key duplicate check as evidence there are no duplicate companies
