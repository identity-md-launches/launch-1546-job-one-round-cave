"""Behavior tests on dated mainnet evidence; mutations are explicitly test-only."""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import proof_handoff as kit


class ProofHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = (kit.HERE / 'examples/zto-snapshot.json').read_bytes()
        cls.proof = (kit.HERE / 'examples/zto-proof.json').read_bytes()
        cls.archive = kit.build(cls.snapshot, cls.proof)
        Path('test/scratch').mkdir(parents=True, exist_ok=True)

    def files(self):
        with zipfile.ZipFile(io.BytesIO(self.archive)) as z:
            return {name:z.read(name) for name in kit.PATHS}

    def test_real_proof_offline_and_exact_bytes(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network')):
            report = kit.inspect_bytes(self.archive)
        self.assertTrue(report['account_proof_recomputed'])
        self.assertEqual(report['account']['account']['nonce'], '1')
        self.assertEqual(self.files()[kit.SNAPSHOT], self.snapshot)
        self.assertEqual(self.files()[kit.PROOF], self.proof)
        self.assertFalse(report['trusted_digest_matched'])

    def test_reproducible_and_native_inspector(self):
        self.assertEqual(self.archive, kit.build(self.snapshot, self.proof))
        r = kit.inspector.inspect_stream(io.BytesIO(self.archive), kit.LIMITS)
        self.assertEqual(r['file_count'], 3)
        self.assertLess(len(self.archive), 99001)

    def test_trusted_digest(self):
        digest = hashlib.sha256(self.archive).hexdigest()
        self.assertTrue(kit.inspect_bytes(self.archive, digest)['trusted_digest_matched'])
        with self.assertRaises(ValueError):
            kit.inspect_bytes(self.archive, 'f' * 64)

    def test_validly_rehashed_false_report_rejected(self):
        files = self.files()
        report = json.loads(files[kit.REPORT])
        report['account']['nonce'] = '999'
        files[kit.REPORT] = kit.canonical(report)
        forged = kit.writer.build(files)
        self.assertTrue(kit.inspector.inspect_stream(io.BytesIO(forged), kit.LIMITS)['verified'])
        with self.assertRaises(ValueError):
            kit.inspect_bytes(forged)

    def test_snapshot_exact_byte_binding(self):
        with self.assertRaises(ValueError):
            kit.build(self.snapshot + b'\n', self.proof)

    def test_mutated_proof_and_claim_rejected(self):
        original = json.loads(self.proof)
        for field in ('nonce', 'balance', 'codeHash', 'storageHash'):
            value = copy.deepcopy(original)
            old = value['proof'][field]
            value['proof'][field] = old[:-1] + ('1' if old[-1] != '1' else '2')
            with self.subTest(field=field), self.assertRaises(ValueError):
                kit.build(self.snapshot, kit.canonical(value))
        value = copy.deepcopy(original)
        old = value['proof']['accountProof'][0]
        value['proof']['accountProof'][0] = old[:-1] + ('1' if old[-1]!='1' else '2')
        with self.assertRaises(ValueError):
            kit.build(self.snapshot, kit.canonical(value))

    def test_missing_and_extra_payloads(self):
        for field in kit.PATHS:
            files = self.files(); del files[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                kit.inspect_bytes(kit.writer.build(files))
        files = self.files(); files['surprise.py'] = b'print("never executed")'
        with self.assertRaises(ValueError):
            kit.inspect_bytes(kit.writer.build(files))

    def test_strict_json_and_input_bounds(self):
        for raw in (b'{"schema":1,"schema":2}', b'{"x":NaN}', b'[]'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, TypeError)):
                kit.build(self.snapshot, raw)
        for raw in (b'', b'x'*99001, bytearray(self.snapshot)):
            with self.assertRaises(ValueError):
                kit.build(raw, self.proof)

    def test_unproved_supply_stays_unproved(self):
        snapshot = json.loads(self.snapshot)
        snapshot['result'] = '0x' + '0'*63 + '1'
        raw = kit.canonical(snapshot)
        bundle = json.loads(self.proof)
        bundle['snapshot_sha256'] = hashlib.sha256(raw).hexdigest()
        report = kit.inspect_bytes(kit.build(raw, kit.canonical(bundle)))
        self.assertEqual(report['account']['reported_total_supply_base_units'], '1')
        self.assertIn('unproved', report['account']['evidence_limits'])

    def test_corruption_and_noncanonical_archive(self):
        bad = bytearray(self.archive); bad[1000] ^= 1
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            kit.inspect_bytes(bytes(bad))
        stream = io.BytesIO(self.archive)
        with zipfile.ZipFile(stream, 'a') as z:
            z.comment = b'valid zip but noncanonical HANDOFF'
        with self.assertRaises(ValueError):
            kit.inspect_bytes(stream.getvalue())

    def test_cli_exclusive_output_and_path_guards(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as folder:
            out = str((Path(folder).resolve() / 'proof.zip').relative_to(Path.cwd()))
            cmd = [sys.executable, '-B', str(kit.HERE/'proof_handoff.py'), 'pack',
                   str((kit.HERE/'examples/zto-snapshot.json').relative_to(Path.cwd())),
                   str((kit.HERE/'examples/zto-proof.json').relative_to(Path.cwd())), out]
            first = subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            before = Path(out).read_bytes()
            second = subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(second.returncode,1)
            self.assertEqual(second.stdout,'')
            self.assertEqual(Path(out).read_bytes(),before)
            link = Path(folder)/'link'; link.symlink_to(Path(out).resolve())
            with self.assertRaises(OSError): kit.read_workspace(str(link.relative_to(Path.cwd()) if link.is_absolute() else link))
            for bad in ('../outside', '/outside'):
                with self.assertRaises(ValueError): kit.read_workspace(bad)

    def test_complete_folder_is_portable(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as folder:
            dest = Path(folder)/'kit'
            shutil.copytree(kit.HERE,dest,ignore=shutil.ignore_patterns('__pycache__'))
            result = subprocess.run([sys.executable,'-B',str(dest.resolve()/'proof_handoff.py'),'demo'],
                                    cwd=folder,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['verified'])

    def test_vendor_provenance(self):
        for item in json.loads((kit.HERE/'PROVENANCE.json').read_bytes())['dependencies']:
            self.assertEqual(hashlib.sha256((kit.HERE/item['copy']).read_bytes()).hexdigest(),item['copy_sha256'])

if __name__ == '__main__':
    unittest.main()
