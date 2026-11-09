# Submission Summary

**Invoice Reconciliation Guard** is a reusable GenLayer Intelligent Contract primitive for reconciling public supplier invoices against a registered purchase order, including split invoices.

The leader and validators independently render an allowlisted invoice page and extract invoice number, PO reference, buyer, supplier, currency, tax-inclusive integer total, line-item summary, scope assessment, and evidence excerpts. A comparative equivalence principle requires validators to verify the same stable identity, amount, and scope fields against their independently fetched page. After consensus, deterministic contract logic performs exact normalized identity checks, duplicate-invoice protection, and cumulative minor-unit arithmetic against the PO cap and configured tolerance. It stores an append-only report only after the assessment has been accepted; ambiguous evidence is `NEEDS_REVIEW`.

The primitive does not transfer funds and does not claim to prove invoice authenticity, payment, delivery, tax compliance, or legal validity. The repository includes contract source, documentation, and focused tests. A live Studio consensus transaction should be attached as evidence after deployment and testing.
