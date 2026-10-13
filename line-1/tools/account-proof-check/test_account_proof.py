"""Real retained proof, adversarial encodings, anchor binding and transport checks."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import account_proof_check as tool

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'live-zto.json'
PROOF = HERE / 'live-proof.json'


def packed(path, leaf):
    flag = (2 if leaf else 0) + len(path) % 2
    digits = [flag] + path if len(path) % 2 else [flag, 0] + path
    return bytes((digits[i] << 4) | digits[i + 1] for i in range(0, len(digits), 2))


def singleton(value, path=None):
    key = tool.header.keccak256(tool.data(tool.ZTO, 20))
    node = tool.encode_rlp([packed(tool.nibbles(key) if path is None else path, True), value])
    return tool.header.keccak256(node), key, ['0x' + node.hex()]


class ProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = tool.load_bundle(PROOF)
        cls.raw, cls.snapshot, cls.facts = tool.snapshot_anchor(SOURCE)

    def test_real_proof_with_socket_forbidden(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('offline')):
            result = tool.verify_bundle(SOURCE, self.bundle)
        self.assertTrue(result['verified'])
        self.assertFalse(result['network_used'])
        self.assertEqual(result['snapshot_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(result['account']['nonce'], str(int(self.bundle['proof']['nonce'], 16)))
        self.assertEqual(result['account']['code_hash'], self.bundle['proof']['codeHash'])
        self.assertEqual(result['account']['storage_root'], self.bundle['proof']['storageHash'])
        self.assertIn('totalSupply remains an unproved', result['evidence_limits'])

    def test_cli_demo_offline(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('offline')), \
                patch.object(sys, 'argv', ['account_proof_check.py', 'demo']), \
                patch.object(sys, 'stdout', new_callable=io.StringIO) as output:
            self.assertEqual(tool.main(), 0)
        self.assertTrue(json.loads(output.getvalue())['verified'])

    def test_cli_check(self):
        with patch.object(sys, 'argv', ['account_proof_check.py', 'check', str(SOURCE), str(PROOF)]), \
                patch.object(sys, 'stdout', new_callable=io.StringIO) as output:
            self.assertEqual(tool.main(), 0)
        self.assertTrue(json.loads(output.getvalue())['verified'])

    def test_snapshot_bytes_bound(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['snapshot_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            tool.verify_bundle(SOURCE, bundle)

    def test_every_claim_bound_to_leaf(self):
        for field in ('nonce', 'balance', 'codeHash', 'storageHash'):
            bundle = copy.deepcopy(self.bundle)
            bundle['proof'][field] = ('0x2' if field in ('nonce', 'balance')
                                      else '0x' + '12' * 32)
            with self.subTest(field=field), self.assertRaises(ValueError):
                tool.verify_bundle(SOURCE, bundle)

    def test_wrong_account_and_storage_slots_refused(self):
        for field, value in (('address', '0x' + '12' * 20), ('storageProof', [{}]),
                             ('storageProof', None), ('accountProof', [])):
            bundle = copy.deepcopy(self.bundle)
            bundle['proof'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                tool.verify_bundle(SOURCE, bundle)

    def test_every_real_node_hash_checked(self):
        for index in range(len(self.bundle['proof']['accountProof'])):
            bundle = copy.deepcopy(self.bundle)
            node = bytearray.fromhex(bundle['proof']['accountProof'][index][2:])
            node[-1] ^= 1
            bundle['proof']['accountProof'][index] = '0x' + node.hex()
            with self.subTest(index=index), self.assertRaises(ValueError):
                tool.verify_bundle(SOURCE, bundle)

    def test_missing_reordered_or_extra_nodes_refused(self):
        original = self.bundle['proof']['accountProof']
        for nodes in (original[:-1], original[1:], list(reversed(original)), original + [original[-1]]):
            bundle = copy.deepcopy(self.bundle)
            bundle['proof']['accountProof'] = nodes
            with self.assertRaises(ValueError):
                tool.verify_bundle(SOURCE, bundle)

    def test_bundle_anchor_fields_bound(self):
        for field, value in (('block_number', '0x1'), ('block_hash', '0x' + '12' * 32),
                             ('state_root', '0x' + '12' * 32), ('chain_id', '0x2'),
                             ('schema', 'unknown'), ('captured_at', 'bad')):
            bundle = copy.deepcopy(self.bundle)
            bundle[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                tool.verify_bundle(SOURCE, bundle)

    def test_both_snapshot_headers_recomputed(self):
        for name in ('block', 'block_after'):
            snapshot = copy.deepcopy(self.snapshot)
            snapshot[name]['stateRoot'] = '0x' + '12' * 32
            with patch.object(tool.seal, 'load_snapshot', return_value=(self.raw, snapshot, self.facts)):
                with self.subTest(header=name), self.assertRaises(ValueError):
                    tool.verify_bundle(SOURCE, self.bundle)

    def test_after_proof_header_recomputed(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['block_after']['stateRoot'] = '0x' + '12' * 32
        with self.assertRaises(ValueError):
            tool.verify_bundle(SOURCE, bundle)

    def test_unexpected_fields_refused(self):
        for target in ('bundle', 'proof'):
            bundle = copy.deepcopy(self.bundle)
            (bundle if target == 'bundle' else bundle['proof'])['surprise'] = True
            with self.assertRaises(ValueError):
                tool.verify_bundle(SOURCE, bundle)

    def test_supply_is_not_authenticated(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['result'] = '0x' + '00' * 32
        raw = (json.dumps(snapshot) + '\n').encode()
        bundle = copy.deepcopy(self.bundle)
        bundle['snapshot_sha256'] = hashlib.sha256(raw).hexdigest()
        facts = tool.seal.pinned.inspect(snapshot)
        with patch.object(tool.seal, 'load_snapshot', return_value=(raw, snapshot, facts)):
            result = tool.verify_bundle(SOURCE, bundle)
        self.assertTrue(result['verified'])
        self.assertEqual(result['reported_total_supply_base_units'], '0')

    def test_outside_workspace_refused_without_open(self):
        with patch.object(tool.seal.os, 'open', side_effect=AssertionError('must not open')):
            with self.assertRaises(ValueError):
                tool.load_bundle('/not-in-workspace/proof.json')

    def test_duplicate_json_and_nonfinite_values(self):
        for raw in (b'{"proof":1,"proof":2}', b'{"x":NaN}', b'{"x":1e10000}'):
            with patch.object(tool.seal, 'read_bytes', return_value=raw):
                with self.assertRaises(ValueError):
                    tool.load_bundle(PROOF)

    def test_workspace_file_guards(self):
        scratch = tool.seal.WORKSPACE / 'test/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='account-proof-', dir=scratch) as directory:
            folder = Path(directory)
            (folder / 'linked-file').symlink_to(PROOF)
            (folder / 'linked-directory').symlink_to(HERE, target_is_directory=True)
            (folder / 'oversize').write_bytes(b' ' * (tool.MAX_FILE + 1))
            os.mkfifo(folder / 'fifo')
            for path in (folder / 'linked-file', folder / 'linked-directory/live-proof.json',
                         folder / 'oversize', folder / 'fifo', folder):
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    tool.load_bundle(path)

    def test_cli_failure_emits_no_partial_json(self):
        with patch.object(sys, 'argv', ['account_proof_check.py', 'check', str(SOURCE), str(PROOF)]), \
                patch.object(tool, 'load_bundle', side_effect=ValueError('bad proof')), \
                patch.object(sys, 'stdout', new_callable=io.StringIO) as output, \
                patch.object(sys, 'stderr', new_callable=io.StringIO) as errors:
            self.assertEqual(tool.main(), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('no result emitted', errors.getvalue())


class EncodingTests(unittest.TestCase):
    def test_canonical_rlp_vectors(self):
        vectors = [(b'\x80', b''), (b'\x00', b'\x00'), (b'\x7f', b'\x7f'),
                   (b'\x81\x80', b'\x80'), (b'\xc0', []),
                   (b'\xc2\x01\x02', [b'\x01', b'\x02']),
                   (b'\xb8\x38' + b'x' * 56, b'x' * 56)]
        for encoded, decoded in vectors:
            self.assertEqual(tool.decode_rlp(encoded), decoded)
            self.assertEqual(tool.encode_rlp(decoded), encoded)

    def test_noncanonical_truncated_and_trailing_rlp(self):
        for raw in (b'', b'\x81\x01', b'\xb8\x01a', b'\xb9\x00\x38' + b'a' * 56,
                    b'\xb8', b'\x82a', b'\xc2\x01', b'\xf8\x01\x80',
                    b'\xf9\x00\x38' + b'\x80' * 56, b'\x80\x80',
                    b'\xc1\x82ab', b'\xbb\xff\xff\xff\xff'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                tool.decode_rlp(raw)

    def test_rlp_depth_item_and_byte_bounds(self):
        value = b''
        for _ in range(10):
            value = [value]
        for raw in (tool.encode_rlp(value), tool.encode_rlp([b''] * 256), b'a' * 4097):
            with self.assertRaises(ValueError):
                tool.decode_rlp(raw)

    def test_quantity_bounds(self):
        for value in ('0x', '0x00', '0x01', '0x' + '1' * 65, True, 1, None, 'latest', '0xg'):
            with self.assertRaises(ValueError):
                tool.quantity(value)
        self.assertEqual(tool.quantity('0x0'), 0)
        self.assertEqual(tool.quantity('0x' + 'f' * 64), 2 ** 256 - 1)

    def test_compact_path_flags_and_padding(self):
        for raw in (b'', b'\x40', b'\x01', b'\x21', []):
            with self.assertRaises(ValueError):
                tool.compact_path(raw)
        for leaf in (False, True):
            for path in ([], [1], [1, 2], list(range(16))):
                self.assertEqual(tool.compact_path(packed(path, leaf)), (leaf, path))

    def test_single_leaf_and_wrong_key(self):
        root, key, proof = singleton(b'account')
        self.assertEqual(tool.inclusion(root, key, proof), b'account')
        for bad_key in (bytes(32), key[:-1] + bytes([key[-1] ^ 1])):
            with self.assertRaises(ValueError):
                tool.inclusion(root, bad_key, proof)

    def test_leaf_must_consume_whole_key(self):
        key = tool.header.keccak256(tool.data(tool.ZTO, 20))
        for path in (tool.nibbles(key)[:-1], tool.nibbles(key) + [1]):
            root, key, proof = singleton(b'account', path)
            with self.assertRaises(ValueError):
                tool.inclusion(root, key, proof)

    def test_extension_branch_and_hashed_children(self):
        key = tool.header.keccak256(tool.data(tool.ZTO, 20))
        path = tool.nibbles(key)
        value = b'a' * 80
        leaf = tool.encode_rlp([packed(path[5:], True), value])
        branch = [b''] * 17
        branch[path[4]] = tool.header.keccak256(leaf)
        branch[(path[4] + 1) % 16] = b'x' * 32
        encoded_branch = tool.encode_rlp(branch)
        extension = tool.encode_rlp([packed(path[:4], False), tool.header.keccak256(encoded_branch)])
        proof = ['0x' + node.hex() for node in (extension, encoded_branch, leaf)]
        self.assertEqual(tool.inclusion(tool.header.keccak256(extension), key, proof), value)

    def test_embedded_child_and_noncanonical_hashed_short_child(self):
        key = tool.header.keccak256(tool.data(tool.ZTO, 20))
        path = tool.nibbles(key)
        leaf = [packed(path[-2:], True), b'a']
        parent = tool.encode_rlp([packed(path[:-2], False), leaf])
        self.assertEqual(tool.inclusion(tool.header.keccak256(parent), key,
                                       ['0x' + parent.hex()]), b'a')
        raw_leaf = tool.encode_rlp(leaf)
        parent = tool.encode_rlp([packed(path[:-2], False), tool.header.keccak256(raw_leaf)])
        with self.assertRaises(ValueError):
            tool.inclusion(tool.header.keccak256(parent), key,
                           ['0x' + parent.hex(), '0x' + raw_leaf.hex()])

    def test_child_reference_exact_31_32_byte_boundary(self):
        key = tool.header.keccak256(tool.data(tool.ZTO, 20))
        path = tool.nibbles(key)
        for length in (31, 32):
            leaf = [b'\x20', b'a' * (length - 3)]
            raw_leaf = tool.encode_rlp(leaf)
            self.assertEqual(len(raw_leaf), length)
            for hashed in (False, True):
                branch = [b''] * 17
                branch[path[-1]] = tool.header.keccak256(raw_leaf) if hashed else leaf
                branch[(path[-1] + 1) % 16] = b'x' * 32
                raw_branch = tool.encode_rlp(branch)
                root = tool.encode_rlp([packed(path[:-1], False), tool.header.keccak256(raw_branch)])
                proof = ['0x' + raw.hex() for raw in [root, raw_branch] + ([raw_leaf] if hashed else [])]
                with self.subTest(length=length, hashed=hashed):
                    if hashed == (length >= 32):
                        self.assertEqual(tool.inclusion(tool.header.keccak256(root), key, proof), leaf[1])
                    else:
                        with self.assertRaises(ValueError):
                            tool.inclusion(tool.header.keccak256(root), key, proof)

    def test_invalid_node_types_references_and_extensions(self):
        key = tool.header.keccak256(tool.data(tool.ZTO, 20))
        for node in (b'x', [], [b'x'] * 3, [b'\x00', b'x' * 32],
                     [packed(tool.nibbles(key), False), b'x' * 32],
                     [packed([tool.nibbles(key)[0]], False), b'x'],
                     [packed([tool.nibbles(key)[0]], False), [b'a' * 40, b'x']]):
            raw = tool.encode_rlp(node)
            with self.subTest(node=node), self.assertRaises(ValueError):
                tool.inclusion(tool.header.keccak256(raw), key, ['0x' + raw.hex()])

    def test_node_and_total_proof_limits(self):
        for proof in ([], ['0x80'] * 66, ['0x' + '11' * 4097], ['0x' + '11' * 4096] * 9):
            with self.assertRaises(ValueError):
                tool.inclusion(bytes(32), bytes(32), proof)

    def test_account_leaf_integer_canonicality(self):
        bundle = tool.load_bundle(PROOF)
        proof = copy.deepcopy(bundle['proof'])
        storage, code = tool.data(proof['storageHash'], 32), tool.data(proof['codeHash'], 32)
        for fields in ([b'\x00', b'', storage, code], [b'', b'\x00', storage, code],
                       [b'\x01' * 33, b'', storage, code], [b'', b'', b'bad', code],
                       [b'', b'', storage, code, b'']):
            root, _, nodes = singleton(tool.encode_rlp(fields))
            proof['accountProof'] = nodes
            with self.assertRaises(ValueError):
                tool.account_check(root, proof)


class TransportTests(unittest.TestCase):
    def test_fixed_request_allowlist(self):
        for method, params in [('eth_sendRawTransaction', ['0x01']), ('eth_call', []),
                               ('eth_getProof', [tool.ZTO, [], 'latest']),
                               ('eth_getProof', [tool.ZTO, ['0x0'], '0x1']),
                               ('eth_getProof', ['0x' + '12' * 20, [], '0x1']),
                               ('eth_getBlockByNumber', ['0x1', True]),
                               ('eth_getBlockByNumber', ['pending', False]),
                               ('eth_chainId', [1])]:
            with patch.object(tool.urllib.request, 'build_opener', side_effect=AssertionError('transport')):
                with self.subTest(method=method, params=params), self.assertRaises(ValueError):
                    tool.public_read(tool.rpc.DEFAULT_RPC, method, params)

    def test_capture_exact_call_sequence_and_identity(self):
        bundle = tool.load_bundle(PROOF)
        calls = []

        def read(method, params):
            calls.append((method, params))
            return {'eth_chainId': '0x1', 'eth_getProof': bundle['proof'],
                    'eth_getBlockByNumber': bundle['block_after']}[method]

        result = tool.capture(SOURCE, read=read)
        self.assertTrue(tool.verify_bundle(SOURCE, result)['verified'])
        self.assertEqual(calls, [('eth_chainId', []),
                                ('eth_getProof', [tool.ZTO, [], bundle['block_number']]),
                                ('eth_getBlockByNumber', [bundle['block_number'], False])])

    def test_wrong_chain_stops_before_proof(self):
        reader = Mock(return_value='0x2')
        with self.assertRaises(ValueError):
            tool.capture(SOURCE, read=reader)
        self.assertEqual(reader.call_count, 1)

    def test_transport_uses_empty_proxy_handler_and_own_user_agent(self):
        response = Mock(status=200, headers={})
        response.read.return_value = b'{"jsonrpc":"2.0","id":1,"result":"0x1"}'
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = context
        with patch.object(tool.urllib.request, 'build_opener', return_value=opener) as build, \
                patch.object(tool.urllib.request, 'getproxies', side_effect=AssertionError('environment')):
            self.assertEqual(tool.public_read(tool.rpc.DEFAULT_RPC, 'eth_chainId', []), '0x1')
        self.assertEqual(build.call_args.args[0].proxies, {})
        self.assertIsInstance(build.call_args.args[1], tool.rpc.NoRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header('User-agent'), tool.USER_AGENT)
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 20)
        self.assertEqual(response.read.call_args.args, (tool.MAX_FILE + 1,))

    def test_transport_response_rejections(self):
        for status, headers, raw in [(302, {}, b'{}'), (200, {'Content-Encoding': 'gzip'}, b'{}'),
                                    (200, {}, b'{"jsonrpc":"2.0","id":true,"result":1}'),
                                    (200, {}, b'{"jsonrpc":"2.0","id":1,"error":{}}'),
                                    (200, {}, b'{"jsonrpc":"2.0","id":1,"result":1,"extra":2}'),
                                    (200, {}, b'x' * (tool.MAX_FILE + 1))]:
            response = Mock(status=status, headers=headers)
            response.read.return_value = raw
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            opener = Mock()
            opener.open.return_value = context
            with patch.object(tool.urllib.request, 'build_opener', return_value=opener):
                with self.assertRaises((ValueError, RuntimeError)):
                    tool.public_read(tool.rpc.DEFAULT_RPC, 'eth_chainId', [])

    def test_redirect_refused(self):
        with self.assertRaises(ValueError):
            tool.rpc.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid')


if __name__ == '__main__':
    unittest.main()
