# Submission Summary

**Invoice Reconciliation Guard** is a reusable GenLayer Intelligent Contract primitive for reconciling public supplier invoices against a registered purchase order, including split invoices.

The leader and validators independently render an allowlisted invoice page and extract invoice number, PO reference, buyer, supplier, currency, tax-inclusive integer total, line-item summary, scope assessment, and evidence excerpts. A comparative equivalence principle requires validators to verify the same stable identity, amount, and scope fields against their independently fetched page. After consensus, deterministic contract logic performs exact normalized identity checks, duplicate-invoice protection, and cumulative minor-unit arithmetic against the PO cap and configured tolerance. It stores an append-only report only after the assessment has been accepted; ambiguous evidence is `NEEDS_REVIEW`.

The primitive does not transfer funds and does not claim to prove invoice authenticity, payment, delivery, tax compliance, or legal validity. The repository includes contract source, documentation, focused tests, and a fictional public invoice fixture.

Studionet verification: contract `0x7B61BE67E9434d7360116B7Ad635565348FEE7af`; the fixture invoice `INV-2026-044` against PO `PO-2026-001` produced `MATCH` with a tax-inclusive total of `102500` USD minor units (`USD 1,025.00`). [Studio Explorer contract page](https://explorer-studio.genlayer.com/address/0x7B61BE67E9434d7360116B7Ad635565348FEE7af).
