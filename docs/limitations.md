# Limitations

- NETTED_NOT_PAID records instructions, not receipt of funds. Integrations must execute and reconcile payments themselves. Do not interpret NETTED invoices as paid invoices.
- Amounts and commercial validity are declared by counterparties. Their wallet signatures do not establish legal enforceability, tax validity or identity beyond the wallet address. This prototype is not a debt-collection or legal certification system.
- Only GBP integer pence and the GOV.UK England-and-Wales calendar policy are supported. No exchange rate, cross-currency rounding or regional substitution is permitted.
- The rule uses UTC dates, weekends and listed bank holidays. It does not model bank-specific outages, opening hours, clearing cutoffs, DST/local-time cutoffs or settlement finality of an external payment rail.
- GOV.UK can revise its calendar. Independently agreeing validators cannot correct a consistently wrong official source; source failure, incomplete coverage or disagreement stops netting until retry. There is no fallback to a caller-provided calendar.
- Netting is opt-in per invoice through the debtor signature, then permissionless for any due accepted subset. This does not promise the best global subset or minimum total number of external payments.
- Capacity is 512 invoices and 32 invoices per batch. There is no economic Sybil resistance, unbounded ledger, pruning or administrator override. Applications should scope instances appropriately; full instances require a new deployment and explicit migration.
- All invoice data is public. Do not post private customer information. Disposable live-test signing keys are deleted after acceptance; they are not production account backups.
- Studionet is a development network and may reset. Local mocked-host tests are not chain evidence. Real success requires FINALIZED plus successful execution and an actual finalized state readback; intentional rejection cases retain their real failure receipts separately.
