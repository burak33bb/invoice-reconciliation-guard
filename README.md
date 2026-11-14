# Invoice Reconciliation Guard

Invoice Reconciliation Guard is a standalone GenLayer Intelligent Contract primitive for checking public supplier invoices against one registered purchase order. It is designed for procurement automation, milestone purchasing, and small-business accounts-payable workflows where invoices may be split across multiple bills.

It is not a payment contract or an accounting system. A `MATCH` is not proof of payment or proof that an invoice is authentic. It never transfers funds. It produces a consensus-backed review record for a human or downstream system.

## Why GenLayer

Invoices are semi-structured documents: supplier and buyer names, purchase-order references, currency, tax-inclusive totals, and line-item descriptions appear in different layouts. Each validator independently fetches the same allowlisted HTTPS invoice page and extracts the same stable fields. A comparative equivalence principle requires agreement on the identifiers, amount, currency, and scope classification; evidence wording may differ only when it supports those fields.

The contract then applies ordinary deterministic rules. It normalizes legal-name suffixes and PO punctuation, rejects identity/currency conflicts, detects previously matched invoice numbers, and computes a cumulative purchase-order cap plus a configured basis-point tolerance. Ambiguous or incomplete evidence remains `NEEDS_REVIEW`; only a supported scope and a within-cap amount become `MATCH`.

## Decision Model

- `MATCH`: the source supports the invoice identity, PO reference, parties, currency, and authorized scope; the cumulative total remains within the configured cap.
- `MISMATCH`: a hard conflict exists, the invoice number was already matched, or the cumulative PO cap would be exceeded.
- `NEEDS_REVIEW`: a required field is absent, the invoice scope is unclear, or the total cannot be established.

The decision is advisory. A matching public page does not prove issuer authenticity, payment, tax compliance, delivery, or legal enforceability. Users should verify documents through their normal supplier channel before paying.

## State Design

- Immutable PO reference, buyer, supplier, authorized scope, currency, decimal precision, total, tolerance, and invoice-domain allowlist.
- The deploying wallet is recorded as the sole reviewer. Other callers revert before invoice fetching or consensus.
- `approved_total_minor`: deterministic cumulative total for matched invoices only.
- `matched_invoice_ids`: bounded duplicate protection for invoices already matched.
- `reports`: append-only JSON archive of `MATCH` invoices only, capped at 100 matched invoices per PO.
- `latest_report`: latest assessment of any outcome. `NEEDS_REVIEW`, `MISMATCH`, and duplicate attempts update this field but do not occupy history slots or appear in `get_report`.

Amounts are integer minor units, never floating point. For USD with two decimal places, `$1,250.00` is `125000` minor units. Partial invoices are supported; the contract prevents accepted invoices from exceeding the PO total plus its explicitly configured tolerance.

## Consensus Design

`review_invoice(invoice_url)` can be called only by the deploying wallet and accepts only HTTPS URLs on the deployment-configured invoice domain. Authorization and URL checks happen before invoice fetching or consensus. Within `gl.eq_principle.prompt_comparative`, the leader and validators independently render the invoice page and extract the PO reference, invoice number, parties, currency, total in minor units, line-item summary, scope status, and short excerpts. The page is treated as untrusted data, not instructions.

Consensus is not asked to perform arithmetic or silently decide whether money should move. The contract deterministically performs party/PO/currency matching, duplicate checks, and cumulative cap calculations after consensus. State updates happen only after the nondeterministic result is accepted.

## Example Deployment

Use a controlled public invoice page hosted on the configured domain. Do not publish private customer information solely to use this demo. The repository includes a fictional fixture at `examples/sample_invoice.txt` for reproducible testing after the repository is public.

```text
purchase_order_ref: PO-2026-001
buyer_name: Example Studio LLC
supplier_name: Northstar Hosting Inc.
purchase_order_scope: Twelve months of managed hosting and daily backups for the staging environment.
currency: USD
currency_decimals: 2
purchase_order_total_minor: 125000
tolerance_bps: 100
allowed_invoice_domain: raw.githubusercontent.com
```

Write input:

```text
invoice_url: https://raw.githubusercontent.com/burak33bb/invoice-reconciliation-guard/main/examples/sample_invoice.txt
```

Read methods: `get_config`, `get_report_count`, `get_latest_report`, `get_report`.

## Limits

- Invoice pages must be public, text-renderable, and hosted on the configured HTTPS domain. Scanned PDFs, login-only pages, and inaccessible documents should yield no usable assessment and must not be treated as a match.
- One contract tracks one purchase order and one configured supplier/buyer pair.
- Currency decimals are explicitly configured at deployment; the contract does not infer exchange rates or convert currencies.
- Scope evaluation is a semantic consensus signal, not a substitute for invoice verification or procurement approval.
- Matched-invoice history is bounded to 100 per deployed PO contract. Non-matches, unclear results, and duplicates do not consume its slots. After 100 matches, another `MATCH` cannot be archived; deploy a replacement contract for a new PO/history lifecycle.
- Reviewer authorization is immutable and set to the deploying wallet. If reviewer access must change, deploy a replacement instance and update the application to its address.

## Studio Verification

- The earlier Studionet address contains the old permissionless version. Deploy this corrected source as a new instance; state does not migrate automatically.
- After deploying, record the new address and verify the `reviewer` returned by `get_config` before submitting deployment evidence.
- The fixture is fictional and demonstrates extraction and deterministic reconciliation only; it is not payment or issuer-authenticity evidence.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

The focused tests check source parsing, consensus-path presence, scope separation, normalization, amount representation, state invariants, and documented examples. A successful test suite is not a substitute for a live consensus transaction in GenLayer Studio.
