# Mechanism

## Signing and conservation

Proposal fixes creditor, debtor, amount, currency and due date. It is not eligible for netting until the debtor signs `accept`. Acceptance explicitly authorizes anyone to select this due invoice into a batch with other accepted invoices. A selected subset can affect gross payment counts; the contract does not promise an optimal global clearing selection.

For each invoice of pence P, the creditor's position increases by P and the debtor's decreases by P. Thus the sum of all positions is exactly zero. There is no floating-point rounding. The amount bound is 1–10^12 pence per invoice, and the batch bound is 32 invoices.

Addresses are sorted lexicographically. Each matching step pairs the first remaining debtor and creditor for the minimum of their remaining positions. At least one position reaches zero per step. The loop terminates with every nonzero position covered, using no more than D+C−1 instructions for D net debtors and C net creditors. It is deterministic; it is not a claim of globally minimum payment count for arbitrary subset selection.

Only after all deterministic preconditions, source consensus, business-day approval and plan conservation checks pass are the invoices marked NETTED and one batch appended. No accepted invoice can appear in another successful batch. The batch's NETTED_NOT_PAID state distinguishes instructions from actual settlement. There is no asset transfer, escrow or payment receipt in this primitive.

## Calendar equivalence

The sole source is `https://www.gov.uk/bank-holidays.json`, division `england-and-wales`. The UTC date is read from `gl.message_raw['datetime']`, never from a caller or language model. The source must return HTTP 200, the correct division, a bounded event list and a plausible covered-year holiday set. Every date is parsed, duplicate dates are rejected, and missing year coverage fails closed rather than being treated as an empty holiday list.

The leader and each validator independently retrieve the feed and canonicalize the relevant year's dates and titles. `gl.vm.run_nondet_unsafe` accepts a `gl.vm.Return` only when canonical JSON exactly matches the validator's independently computed result. Equality covers source URL, division, target date, all selected holidays and business-day classification. A weekend or listed holiday produces CLEARING_DAY_CLOSED after consensus, with no invoice consumption. Source failure or validator disagreement likewise leaves invoices eligible for a later attempt.

## Boundaries

The date rule is a UTC calendar-day gate, not a bank operating-hours or payment-cutoff service. The ledger is bounded to 512 invoices per instance. Selection is permissionless after acceptance; proposal/cancellation and debtor acceptance have separate wallet authority checks. No administrator can force acceptance or bypass the calendar.
