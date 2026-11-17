# BankDayNet

A counterparty-signed invoice netting primitive for GBP obligations. GenLayer validators agree on the current UTC date's classification using the official GOV.UK England-and-Wales bank-holiday feed; only a covered weekday without a listed holiday may produce a netting batch.

Small counterparties can owe each other money in opposite directions. A unilateral spreadsheet can omit an invoice, include an unsigned amount or net an obligation twice. BankDayNet requires the named debtor's signature on each fixed invoice, consumes accepted invoices atomically and derives an exact integer-pence settlement plan. The resulting instructions conserve each participant's net position.

## Network and source

- **Stable Studionet only:** chain 61999, RPC `https://studio.genlayer.com/api`.
- Exact SDK: `genlayer-js@1.1.8`.
- Contract: `0xBf2cCF2CA36e3fc1DB5Fe86A73EAc88a3Def5D94`.
- Deployment transaction: `0x0773577c8cf1ee76ae0ad83060ca118af223e02e615e327cc3e084b746e830b0`.
- Deployment metadata: [`deployment.json`](deployment.json).
- Source: [`contracts/bankday_net.py`](contracts/bankday_net.py).
- Actual receipts, negative cases and readbacks: [`evidence/live.json`](evidence/live.json).
- Independent source/receipt/readback verification: [`evidence/verification.json`](evidence/verification.json).

## Business flow

1. Creditor calls `propose(reference, debtor, pence, due)` to declare an immutable GBP invoice. The invoice ID is `lowercase-creditor-address:reference`. Self-invoices, zero amounts and duplicate references are rejected.
2. Only the named debtor can `accept(id)`. Acceptance authorizes permissionless netting after the due date, including with other accepted invoices. The creditor can cancel only while PROPOSED; an accepted amount cannot be withdrawn unilaterally.
3. Anyone calls `clear(invoice_ids_json)` with 2–32 distinct ACCEPTED invoices that are all due. The date comes from deterministic GenLayer transaction context, not a caller-supplied clock.
4. Leader and validators independently obtain GOV.UK's official calendar. The response must cover the relevant year and contain valid, nonduplicated holiday dates. Exact agreement is required on the selected year's holiday list and the business-day result. Weekends and bank holidays cannot clear.
5. The contract computes each address's credits minus debits in integer pence, verifies a zero sum, and deterministically matches debtors to creditors. It consumes every invoice once and stores the immutable batch. Zero-net cycles need no transfers; nonzero positions produce the transfer instructions.
6. Consumers read `get_batch(id)` and execute any payment separately. Batch state is deliberately **NETTED_NOT_PAID**. The contract does not hold or transfer GBP, GEN or any other assets, and never claims that money has been paid.

| Invoice state | Allowed transition |
| --- | --- |
| PROPOSED | ACCEPTED by debtor, or CANCELLED by creditor |
| ACCEPTED | NETTED in one successful batch |
| CANCELLED | Terminal |
| NETTED | Terminal; cannot enter a second batch |

## Run and call

Node.js 22+ and Python 3.12+ are recommended.

```sh
npm ci
npm test
npm run check
node examples/usage.mjs read get_batch '[0]'
node examples/usage.mjs read snapshot '[]'
```

Generic signed calls use `PRIVATE_KEY` from a secure environment mechanism. For example, replace the debtor with the actual counterparty wallet:

```sh
node examples/usage.mjs write propose '["invoice-2026-001","0xYOUR_COUNTERPARTY",12500,"2026-11-17"]'
node examples/usage.mjs write accept '["0xcreditor:invoice-2026-001"]'
node examples/usage.mjs write clear '["[\"0xcreditor:invoice-2026-001\",\"0xother:invoice-2026-002\"]"]'
```

These address placeholders must be replaced before signing. The debtor runs `accept` with its own key. `clear` requires at least two independently accepted invoices; it cannot create an obligation or bypass a signature. The example waits for FINALIZED and successful execution and then reads the finalized business state.

## Deploy and reproduce

```sh
npm run deploy
npm run live
npm run verify
```

The published checkout already contains a completed acceptance journal. In that checkout, deployment/live commands retain the recorded instance. To create a fresh instance, use a separate working directory with the source, scripts, examples and package files but no existing `evidence/live.json`; keep the published evidence intact.

The scripts enforce chain 61999 and use the official Studio faucet for disposable test accounts. They never send value with contract calls. Pending hashes are journaled before polling. Mode-0600 signing keys remain in ignored `artifacts/signers.json` only for resuming an incomplete run and are deleted after successful acceptance. Re-running a completed live run performs no writes; `npm run verify` re-fetches public evidence without signing.

The live case has three independently signing test accounts and four accepted obligations: A is owed 10,000 pence by B; B is owed 7,000 by C; C is owed 4,000 by A; A is owed 2,000 by C. Gross 23,000 pence becomes 8,000 pence of instructions, with A +8,000, B −3,000 and C −5,000. Two instructions preserve those exact net positions. These are test declarations, not evidence of real commercial debt or executed payments.

See [mechanism](docs/mechanism.md) and [limitations](docs/limitations.md). The calendar is published by GOV.UK under the [Open Government Licence](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/); see the [official API catalogue](https://www.api.gov.uk/gds/bank-holidays/). Code is MIT licensed. No frontend, relayer, paid API or backend subscription is required.
