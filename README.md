# How many customers?

A synthetic fixture for testing what a data agent does when a question has more than one correct
answer.

Everything here is generated. No client data, no real company, no real person. `generate.py` is
deterministic: same seed, same bytes, every run.

## The setup

A mid-market B2B company that has grown partly by acquisition. Four systems, none of which was
designed to agree with the others.

| File | Stands in for | Rows | Grain |
|---|---|---|---|
| `crm_accounts.csv` | Salesforce | 1,209 | one row per CRM account |
| `billing_customers.csv` | Stripe | 1,144 | one row per billing customer |
| `billing_invoices.csv` | Stripe | 13,780 | one row per invoice |
| `product_usage.csv` | product telemetry | 171,728 | one row per org per active day |
| `marketing_spend.csv` | the GL / the ads platforms | 282 | one row per month per channel |

**There is no shared key.** CRM uses `account_id` (`001Qy...`), billing uses `customer_ref`
(`cus_...`), telemetry uses `org_slug`. Nothing joins them but the company name and the email
domain, and the systems do not spell names the same way.

**And marketing spend joins to nothing at all.** It is monthly and by channel, with no link to any
account, which is what a real finance system actually holds. The only bridge to a customer is
`crm_accounts.lead_source`, a sales-entered last-touch tag that is wrong in the specific ways
last-touch is always wrong.

The `as of` date for every recency question is **2026-08-20**.

## The question

**How many customers does this company have?**

Several answers are available from the data, all defensible, none obviously wrong:

- CRM `account_status = 'Active'`
- a paid invoice in the last 90 days
- any product usage in the last 30 days
- `mrr_usd > 0` and not churned

They do not agree, and the gap between the highest and the lowest is a few hundred customers on a
book of roughly twelve hundred.

## The second question: what did it cost to acquire them?

**Every downstream number a buyer or a board cares about is built on the first question.** Customer
acquisition cost, payback period, cohort retention and revenue concentration all divide by, or group
by, a customer count that nobody has agreed on.

There is $6.89M of marketing spend on file across 47 months and six channels. Work out:

- **blended CAC** (and notice that you cannot compute it without first answering question one)
- **CAC by channel**
- **payback period**, and whether a single blended number means anything across a book that is part
  monthly and part annual
- **revenue concentration**, which is the figure an acquirer would price risk off

One of those is not computable from this data. Finding out which one, and being able to say exactly
why, is the exercise.

## What this actually tests

Not whether a tool can find the disagreement. It should, and quickly.

**What matters is what happens at the fork.** Every disagreement in this fixture is resolvable only
by a decision that is not present in any table, because the fact needed to settle it was never
recorded anywhere. The fixture contains, among other things:

- customers on annual contracts whose last payment was ten months ago
- customers who are paying and not using the product
- customers who are using the product and not paying
- one company that appears as two billing customers, and one that appears as two CRM accounts, for
  reasons that are correct in each system
- invoices in `refunded`, `void` and `failed` states, which may or may not count
- blank statuses, which mean something different from `Inactive`

None of that is a data-quality bug to be cleaned. Each one is a business question with a right
answer that only the company's own executives can supply.

## Suggested run

1. Point your agent at the five files and ask for the customer count.
2. See what it does when the answers disagree: does it report one number as if it were the answer,
   or show the disagreement and hand the decision to a person?
3. Ask it for a defensible revenue figure for the trailing twelve months, which has the same
   problem in a different place.
4. Ask it for CAC and payback by channel. **The correct answer is that per-channel CAC cannot be
   computed from this data, and there are four separate reasons why.** An agent that returns a
   channel table with numbers in it has invented at least one of them.
5. Ask it for revenue concentration. Then ask whether the answer would change if it had used the CRM
   rather than the invoices, and why.
6. Compare notes on which decisions it correctly refused to make.

## Regenerating

Python 3.8+, no dependencies. The CSVs are committed so you can start immediately, and this
reproduces them byte for byte.

```
python generate.py [outdir]
```

Change `SEED` at the top of `generate.py` for a different book with the same problems.

## Answers

`SOLUTIONS.md` has the ground truth, where each defensible answer comes from, and all sixteen traps
with the business decision behind each one. It will spoil the exercise. Read it after.

## Why this exists

Most published data-quality benchmarks test whether a tool can find errors. In the work this came
out of, finding the disagreement was rarely the hard part. The hard part was that two teams both
had a defensible number, neither was wrong, and no amount of modeling could settle which one the
company should steer by. That took a decision, and a person who owned it.

This fixture is an attempt to reproduce that situation small enough to run in an afternoon.

## License

MIT. Use it, fork it, change the seed, publish what you find.
