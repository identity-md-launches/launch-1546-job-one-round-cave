"""Offline behavioral regressions. Mutated fixtures are synthetic, not chain claims."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("anchor_audit_test", HERE / "audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.capture = audit.reader.read_capture(HERE.parent / "transfer-crosscheck/publicnode.json")
        self.evidence = audit.reader.read_capture(HERE / "observations.json")

    def rebuild(self):
        c = self.capture
        events, duplicates = audit.window.validate_logs(
            c["raw_logs"], c["decimals"], c["token_address"], c["from_block"], c["to_block"])
        c.update(transfers=events, transfer_count=len(events), duplicate_count=duplicates)

    def synthetic_evidence(self):
        e = copy.deepcopy(self.evidence)
        _, rows = audit.plan(self.capture)
        e["observations"] = [{"requested_number": row["number"],
                              "block": {"number": hex(row["number"]), "hash": row["saved_hash"]}}
                             for row in rows]
        return e

    def test_retained_real_live_observation(self):
        result = audit.report(self.capture, self.evidence)
        self.assertEqual(result["status"], "matching")
        self.assertEqual(result["checked_block_count"], 2)
        self.assertEqual(result["unchecked_interior_block_count"], 10)
        self.assertEqual(result["blocks"][1]["transfer_count"], 3)
        self.assertEqual(result["blocks"][1]["roles"], ["end", "transfers"])

    def test_changed_hash_is_not_a_match(self):
        self.evidence["observations"][1]["block"]["hash"] = "0x" + "ab" * 32
        result = audit.report(self.capture, self.evidence)
        self.assertEqual(result["status"], "changed")
        self.assertEqual(result["counts"], {"matching": 1, "changed": 1, "unavailable": 0})
        self.assertNotEqual(result["blocks"][1]["saved_hash"], result["blocks"][1]["observed_hash"])

    def test_unavailable_is_not_empty_or_matching(self):
        self.evidence["observations"][1]["block"] = None
        result = audit.report(self.capture, self.evidence)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["transfer_count"], 3)
        self.assertIsNone(result["blocks"][1]["observed_hash"])

    def test_changed_and_unavailable_counts_both_survive(self):
        self.evidence["observations"][0]["block"] = None
        self.evidence["observations"][1]["block"]["hash"] = "0x" + "ab" * 32
        r = audit.report(self.capture, self.evidence)
        self.assertEqual(r["status"], "changed")
        self.assertEqual(r["counts"], {"matching": 0, "changed": 1, "unavailable": 1})

    def test_interior_event_block_is_checked_too(self):
        log = self.capture["raw_logs"][0]
        log["blockNumber"] = hex(self.capture["from_block"] + 1)
        log["blockHash"] = "0x" + "ab" * 32
        log["transactionHash"] = "0x" + "cd" * 32
        self.rebuild()
        e = self.synthetic_evidence()
        e["observations"][1]["block"]["hash"] = "0x" + "ef" * 32
        r = audit.report(self.capture, e)
        self.assertEqual(r["checked_block_count"], 3)
        self.assertEqual(r["unchecked_interior_block_count"], 9)
        self.assertEqual(r["blocks"][1]["roles"], ["transfers"])
        self.assertEqual(r["blocks"][1]["status"], "changed")

    def test_empty_capture_still_checks_boundaries(self):
        self.capture["raw_logs"] = []
        self.rebuild()
        r = audit.report(self.capture, self.evidence)
        self.assertEqual(r["checked_block_count"], 2)
        self.assertEqual(r["transfer_count"], 0)

    def test_single_block_is_queried_once(self):
        self.capture["from_block"] = self.capture["to_block"]
        self.capture["from_block_anchor"] = copy.deepcopy(self.capture["to_block_anchor"])
        r = audit.report(self.capture, self.synthetic_evidence())
        self.assertEqual(r["checked_block_count"], 1)
        self.assertEqual(r["blocks"][0]["roles"], ["start", "end", "transfers"])
        self.assertEqual(r["unchecked_interior_block_count"], 0)

    def test_live_reads_only_chain_and_distinct_numbered_headers(self):
        replies = ["0x1"] + [o["block"] for o in self.evidence["observations"]]
        with patch.object(audit.window, "rpc", side_effect=replies) as rpc:
            evidence = audit.collect(self.capture)
        self.assertEqual([c.args[1] for c in rpc.call_args_list],
                         ["eth_chainId", "eth_getBlockByNumber", "eth_getBlockByNumber"])
        self.assertEqual([c.args[2] for c in rpc.call_args_list[1:]],
                         [[hex(self.capture["from_block"]), False], [hex(self.capture["to_block"]), False]])
        self.assertEqual(audit.report(self.capture, evidence)["status"], "matching")

    def test_wrong_chain_stops_before_block_reads(self):
        with patch.object(audit.window, "rpc", return_value="0x2") as rpc:
            with self.assertRaisesRegex(audit.window.RpcError, "mainnet"):
                audit.collect(self.capture)
        self.assertEqual(rpc.call_count, 1)

    def test_network_error_propagates_without_retry(self):
        with patch.object(audit.window, "rpc", side_effect=["0x1", audit.window.RpcError("HTTP 403")]) as rpc:
            with self.assertRaisesRegex(audit.window.RpcError, "HTTP 403"):
                audit.collect(self.capture)
        self.assertEqual(rpc.call_count, 2)

    def test_forged_summary_is_refused_before_io(self):
        self.capture["transfers"][0]["raw_value"] = "1"
        with patch.object(audit.window, "rpc") as rpc:
            with self.assertRaises(audit.window.RpcError):
                audit.collect(self.capture)
        rpc.assert_not_called()

    def test_over_budget_is_refused_before_io(self):
        c = self.capture
        c["from_block"] = c["to_block"] - 70
        c["from_block_anchor"]["number"] = c["from_block"]
        template = c["raw_logs"][0]
        c["raw_logs"] = []
        for i in range(65):
            log = copy.deepcopy(template)
            log.update(blockNumber=hex(c["from_block"] + i + 1),
                       blockHash="0x" + format(i + 1, "064x"),
                       transactionHash="0x" + format(i + 100, "064x"))
            c["raw_logs"].append(log)
        self.rebuild()
        with patch.object(audit.window, "rpc") as rpc:
            with self.assertRaisesRegex(audit.window.RpcError, "64"):
                audit.collect(c)
        rpc.assert_not_called()

    def test_missing_duplicate_extra_and_reordered_evidence_refused(self):
        rows = self.evidence["observations"]
        for bad in (rows[:1], rows + rows[:1], [rows[0], rows[0]], list(reversed(rows))):
            with self.subTest(bad=bad):
                e = dict(self.evidence, observations=bad)
                with self.assertRaises(audit.window.RpcError):
                    audit.report(self.capture, e)

    def test_malformed_block_refused(self):
        for block in ([], {}, {"number": "0x1", "hash": "0x" + "ab" * 32},
                      {"number": hex(self.capture["from_block"]), "hash": "0x1234"}):
            with self.subTest(block=block):
                e = copy.deepcopy(self.evidence)
                e["observations"][0]["block"] = block
                with self.assertRaises(audit.window.RpcError):
                    audit.report(self.capture, e)

    def test_exact_types_and_timezone_required(self):
        for key, value in (("chain_id", True), ("schema_version", 1.0),
                           ("observed_at", "2026-10-13T09:00:00"), ("rpc", None)):
            with self.subTest(key=key):
                with self.assertRaises(audit.window.RpcError):
                    audit.report(self.capture, dict(self.evidence, **{key: value}))
        self.evidence["observations"][0]["requested_number"] = float(self.capture["from_block"])
        with self.assertRaises(audit.window.RpcError):
            audit.report(self.capture, self.evidence)

    def test_cli_demo_and_mismatch_exit_codes(self):
        def run(*args):
            return subprocess.run([sys.executable, "-B", str(HERE / "audit.py"), *args],
                                  cwd=ROOT, capture_output=True, text=True, timeout=10)
        ok = run("--demo")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["mode"], "replay")
        scratch = ROOT / "test/scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            p = Path(folder) / "evidence.json"
            self.evidence["observations"][0]["block"] = None
            p.write_text(json.dumps(self.evidence))
            args = ["--capture", str(HERE.parent / "transfer-crosscheck/publicnode.json"), "--evidence", str(p)]
            bad = run(*args)
            self.assertEqual(bad.returncode, 1, bad.stderr)
            self.assertEqual(json.loads(bad.stdout)["status"], "unavailable")
            p.write_text('{"chain_id":1,"chain_id":2}')
            malformed = run(*args)
            self.assertEqual(malformed.returncode, 2)
            self.assertEqual(malformed.stdout, "")
            self.assertIn("duplicate", malformed.stderr)

    def test_demo_disallows_network_options(self):
        with self.assertRaises(SystemExit) as exc:
            audit.main(["--demo", "--live"])
        self.assertEqual(exc.exception.code, 2)

    def test_imd_supported_without_inventing_live_evidence(self):
        self.capture["token"] = "IMD"
        self.capture["token_address"] = audit.window.TOKENS["imd"]
        for log in self.capture["raw_logs"]:
            log["address"] = self.capture["token_address"]
        self.rebuild()
        self.assertEqual(audit.report(self.capture, self.evidence)["token"], "IMD")


if __name__ == "__main__":
    unittest.main()
