import ast
import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "contracts" / "invoice_reconciliation_guard.py").read_text(encoding="utf-8")


class Decorator:
    def __call__(self, function):
        return function


class FakeAddress:
    def __init__(self, value):
        self.as_hex = value


def load_contract():
    class FakeContract:
        def __getattr__(self, name):
            if name in {"matched_invoice_ids", "reports"}:
                value = []
                setattr(self, name, value)
                return value
            raise AttributeError(name)

    public = types.SimpleNamespace(write=Decorator(), view=Decorator())
    nondet = types.SimpleNamespace(
        web=types.SimpleNamespace(render=lambda url, mode: "invoice page"),
        exec_prompt=lambda prompt: "{}",
    )
    eq_principle = types.SimpleNamespace(
        prompt_comparative=lambda function, principle: function()
    )
    message = types.SimpleNamespace(
        sender_address=FakeAddress("0x0000000000000000000000000000000000000001")
    )
    fake_genlayer = types.ModuleType("genlayer")
    fake_genlayer.gl = types.SimpleNamespace(
        Contract=FakeContract, public=public, nondet=nondet, eq_principle=eq_principle,
        message=message,
    )
    fake_genlayer.DynArray = list
    fake_genlayer.u8 = int
    fake_genlayer.u16 = int
    fake_genlayer.u256 = int
    fake_genlayer.__all__ = ["gl", "DynArray", "u8", "u16", "u256"]
    with _temporary_module(fake_genlayer):
        spec = importlib.util.spec_from_file_location("invoice_contract_under_test", ROOT / "contracts" / "invoice_reconciliation_guard.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module, nondet, eq_principle


class _temporary_module:
    def __init__(self, module):
        self.module = module
        self.previous = None

    def __enter__(self):
        self.previous = sys.modules.get("genlayer")
        sys.modules["genlayer"] = self.module

    def __exit__(self, exc_type, exc_value, traceback):
        if self.previous is None:
            sys.modules.pop("genlayer", None)
        else:
            sys.modules["genlayer"] = self.previous


def normalize_domain(value: str) -> str:
    value = value.strip().lower()
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        return ""
    return parsed.hostname.lower().removeprefix("www.")


def normalize_identifier(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def test_source_parses_and_declares_consensus_contract():
    tree = ast.parse(SOURCE)
    assert any(isinstance(node, ast.ClassDef) and node.name == "InvoiceReconciliationGuard" for node in tree.body)
    assert "gl.eq_principle.prompt_comparative" in SOURCE
    assert "gl.nondet.web.render(invoice_url, mode=\"text\")" in SOURCE


def test_scope_is_invoice_reconciliation_not_generic_claim_review():
    assert "purchase_order_ref" in SOURCE
    assert "approved_total_minor" in SOURCE
    assert "DUPLICATE_INVOICE_NUMBER" in SOURCE
    assert "PURCHASE_ORDER_CAP_EXCEEDED" in SOURCE
    assert "MAX_REPORTS = 100" in SOURCE
    assert "self.approved_total_minor = u256(report[\"cumulative_total_minor\"])" in SOURCE


def test_domain_and_reference_normalization():
    assert normalize_domain("https://www.invoices.example/path") == "invoices.example"
    assert normalize_domain("http://invoices.example") == ""
    assert normalize_domain("https://notinvoices.example") != "invoices.example"
    assert normalize_identifier("PO-2026 / 001") == "po2026001"


def test_minor_unit_and_consensus_constraints_are_explicit():
    assert '"total_minor"' in SOURCE
    assert "configured currency's smallest unit" in SOURCE
    assert "The scope_status must match exactly" in SOURCE
    assert "gl.storage" not in SOURCE


def test_readme_explains_state_and_limitations():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "State Design" in readme
    assert "Consensus Design" in readme
    assert "not proof of payment" in readme.lower()
    assert "partial invoices" in readme.lower()


def test_deploy_examples_use_minor_units_and_public_invoice_source():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "purchase_order_total_minor: 125000" in readme
    assert "currency_decimals: 2" in readme
    assert "review_invoice" in readme
    assert re.search(r"https://[a-z0-9.-]+/.*invoice", readme)


def test_sample_invoice_is_consistent_with_deployment_example():
    invoice = (ROOT / "examples" / "sample_invoice.txt").read_text(encoding="utf-8")
    assert "Invoice number: INV-2026-044" in invoice
    assert "Purchase order reference: PO-2026-001" in invoice
    assert "Total including tax: USD 1,025.00" in invoice
    assert "fictional invoice" in invoice.lower()


def test_json_canonicalization_example_is_valid():
    sample = {"decision": "MATCH", "total_minor": 12000}
    assert json.loads(json.dumps(sample, sort_keys=True)) == sample


def build_extraction(**changes):
    result = {
        "invoice_number": "INV-044",
        "purchase_order_ref": "PO-2026-001",
        "buyer_name": "Example Studio, LLC",
        "supplier_name": "Northstar Hosting Incorporated",
        "currency": "USD",
        "total_minor": 80000,
        "line_items": "Managed hosting and daily backups",
        "scope_status": "SUPPORTED",
        "evidence": ["Invoice INV-044; PO-2026-001; Total USD 800.00"],
    }
    result.update(changes)
    return result


def new_contract(total=100000, tolerance=100):
    module, nondet, eq_principle = load_contract()
    contract = module.InvoiceReconciliationGuard(
        "PO-2026-001",
        "Example Studio LLC",
        "Northstar Hosting Inc.",
        "Managed hosting and daily backups for staging.",
        "USD",
        2,
        total,
        tolerance,
        "invoices.example.com",
    )
    return contract, nondet, eq_principle


def test_consensus_invoice_is_recorded_and_cumulative_total_updates():
    contract, nondet, _ = new_contract()
    nondet.exec_prompt = lambda prompt: json.dumps(build_extraction())

    report = contract.review_invoice("https://invoices.example.com/invoice/INV-044")

    assert report["decision"] == "MATCH"
    assert report["cumulative_total_minor"] == 80000
    assert contract.approved_total_minor == 80000
    assert contract.get_report_count() == 1
    assert contract.get_latest_report()["decision"] == "MATCH"


def test_duplicate_matched_invoice_is_rejected_without_double_counting():
    contract, nondet, _ = new_contract()
    current = build_extraction()
    nondet.exec_prompt = lambda prompt: json.dumps(current)
    contract.review_invoice("https://invoices.example.com/invoice/INV-044")
    current.update(invoice_number="inv 044")

    result = contract.review_invoice("https://invoices.example.com/invoice/INV-044-copy")

    assert result["decision"] == "MISMATCH"
    assert "DUPLICATE_INVOICE_NUMBER" in result["reason_codes"]
    assert contract.approved_total_minor == 80000


def test_cumulative_tolerance_is_applied_deterministically():
    contract, nondet, _ = new_contract(total=100000, tolerance=100)
    current = build_extraction()
    nondet.exec_prompt = lambda prompt: json.dumps(current)
    contract.review_invoice("https://invoices.example.com/invoice/INV-044")
    current.update(invoice_number="INV-045", total_minor=22000)

    report = contract.review_invoice("https://invoices.example.com/invoice/INV-045")

    assert report["decision"] == "MISMATCH"
    assert "PURCHASE_ORDER_CAP_EXCEEDED" in report["reason_codes"]
    assert contract.approved_total_minor == 80000


def test_unclear_scope_is_stored_for_review_not_counted_as_approved():
    contract, nondet, _ = new_contract()
    nondet.exec_prompt = lambda prompt: json.dumps(build_extraction(scope_status="UNCLEAR"))

    report = contract.review_invoice("https://invoices.example.com/invoice/INV-044")

    assert report["decision"] == "NEEDS_REVIEW"
    assert contract.approved_total_minor == 0
    assert contract.get_report_count() == 0
    assert contract.get_latest_report()["decision"] == "NEEDS_REVIEW"


def test_mismatched_purchase_order_is_not_approved():
    contract, nondet, _ = new_contract()
    nondet.exec_prompt = lambda prompt: json.dumps(
        build_extraction(purchase_order_ref="PO-OTHER")
    )

    report = contract.review_invoice("https://invoices.example.com/invoice/INV-044")

    assert report["decision"] == "MISMATCH"
    assert "PURCHASE_ORDER_REFERENCE_MISMATCH" in report["reason_codes"]
    assert contract.approved_total_minor == 0


def test_missing_evidence_cannot_produce_match():
    contract, nondet, _ = new_contract()
    nondet.exec_prompt = lambda prompt: json.dumps(build_extraction(evidence=[]))

    report = contract.review_invoice("https://invoices.example.com/invoice/INV-044")

    assert report["decision"] == "NEEDS_REVIEW"
    assert contract.approved_total_minor == 0


def test_off_domain_invoice_is_rejected_before_consensus_or_storage():
    contract, nondet, _ = new_contract()

    try:
        contract.review_invoice("https://invoices.attacker.example/invoice/INV-044")
    except ValueError as error:
        assert "configured HTTPS domain" in str(error)
    else:
        raise AssertionError("Off-domain invoice URL was accepted.")

    assert contract.get_report_count() == 0
