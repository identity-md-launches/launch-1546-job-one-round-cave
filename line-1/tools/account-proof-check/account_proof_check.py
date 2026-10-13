#!/usr/bin/env python3
"""Check a ZTO EIP-1186 account inclusion proof against a pinned snapshot offline."""
import argparse
import datetime as dt
import hashlib
import http.client
import json
from pathlib import Path
import re
import sys
import urllib.request

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'header-hash-check'))
try:
    import header_hash_check as header
finally:
    sys.path.pop(0)
seal = header.seal
rpc = seal.pinned.rpc
ZTO = seal.pinned.ZTO
SCHEMA = 'pinned-zto-account-proof/1'
MAX_FILE = 4 * 1024 * 1024
MAX_NODES = 65
MAX_NODE = 4096
MAX_PROOF = 32768
USER_AGENT = 'Pepeolithic-Account-Proof/1.0 (read-only public Ethereum)'


def quantity(value):
    if (not isinstance(value, str) or len(value) > 66 or
            not re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)', value)):
        raise ValueError('expected canonical uint256 quantity')
    return int(value, 16)


def data(value, length=None, maximum=MAX_NODE):
    if (not isinstance(value, str) or len(value) > 2 + maximum * 2 or
            not rpc.hex_data(value, length)):
        raise ValueError('invalid hex bytes')
    return bytes.fromhex(value[2:])


def decode_rlp(raw):
    """Decode exactly one canonical RLP item with bounded size and nesting."""
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_NODE:
        raise ValueError('RLP size outside bounds')
    items = 0

    def take(offset, end, depth):
        nonlocal items
        items += 1
        if depth > 8 or items > 256 or offset >= end:
            raise ValueError('RLP nesting, item count or truncation')
        first = raw[offset]
        if first < 128:
            return raw[offset:offset + 1], offset + 1
        is_list = first >= 192
        short = 192 if is_list else 128
        long = 247 if is_list else 183
        if first <= long:
            size, start = first - short, offset + 1
        else:
            width = first - long
            start = offset + 1 + width
            if width > 4 or start > end or raw[offset + 1] == 0:
                raise ValueError('noncanonical or truncated RLP length')
            size = int.from_bytes(raw[offset + 1:start], 'big')
            if size < 56:
                raise ValueError('noncanonical long RLP form')
        finish = start + size
        if finish > end:
            raise ValueError('truncated RLP payload')
        if not is_list:
            if size == 1 and raw[start] < 128:
                raise ValueError('noncanonical single-byte RLP')
            return raw[start:finish], finish
        result = []
        while start < finish:
            item, start = take(start, finish, depth + 1)
            result.append(item)
        return result, finish

    result, consumed = take(0, len(raw), 0)
    if consumed != len(raw):
        raise ValueError('trailing RLP bytes')
    return result


def encode_rlp(value):
    """Encode already bounded decoded nodes, including embedded child lists."""
    if isinstance(value, bytes):
        return header.rlp_bytes(value)
    if not isinstance(value, list):
        raise ValueError('invalid RLP value')
    payload = b''.join(encode_rlp(item) for item in value)
    if len(payload) < 56:
        return bytes([192 + len(payload)]) + payload
    width = (len(payload).bit_length() + 7) // 8
    return bytes([247 + width]) + len(payload).to_bytes(width, 'big') + payload


def nibbles(raw):
    return [digit for byte in raw for digit in (byte >> 4, byte & 15)]


def compact_path(raw):
    if not isinstance(raw, bytes) or not raw:
        raise ValueError('missing compact trie path')
    path = nibbles(raw)
    flag = path[0]
    if flag > 3 or (not flag & 1 and path[1] != 0):
        raise ValueError('noncanonical compact trie path')
    return bool(flag & 2), path[1 if flag & 1 else 2:]


def valid_reference(value):
    if isinstance(value, bytes):
        if len(value) not in (0, 32):
            raise ValueError('child must be empty, a hash or an embedded list')
    elif isinstance(value, list):
        if len(encode_rlp(value)) >= 32:
            raise ValueError('large child must be hashed')
    else:
        raise ValueError('invalid trie child')


def inclusion(root, key, proof):
    """Return the included value; absent keys and unused proof nodes are refused."""
    if (not isinstance(root, bytes) or len(root) != 32 or
            not isinstance(key, bytes) or len(key) != 32):
        raise ValueError('root and secure key must be 32 bytes')
    if not isinstance(proof, list) or not 1 <= len(proof) <= MAX_NODES:
        raise ValueError('proof node count outside bounds')
    nodes = [data(node) for node in proof]
    if sum(map(len, nodes)) > MAX_PROOF:
        raise ValueError('proof exceeds total byte bound')
    path, position, cursor, reference = nibbles(key), 0, 0, root
    for _step in range(130):
        if isinstance(reference, list):
            node = reference
        else:
            if not reference or cursor >= len(nodes):
                raise ValueError('account absent or proof incomplete')
            raw = nodes[cursor]
            if header.keccak256(raw) != reference:
                raise ValueError('trie node hash mismatch')
            if cursor and len(raw) < 32:
                raise ValueError('short child should be embedded')
            cursor += 1
            node = decode_rlp(raw)
        if not isinstance(node, list):
            raise ValueError('trie node must be an RLP list')
        value = None
        if len(node) == 17:
            for child in node[:16]:
                valid_reference(child)
            if not isinstance(node[16], bytes):
                raise ValueError('branch value must be bytes')
            if position == len(path):
                value = node[16]
            else:
                reference = node[path[position]]
                position += 1
        elif len(node) == 2:
            leaf, segment = compact_path(node[0])
            if not leaf and not segment:
                raise ValueError('empty extension path')
            if path[position:position + len(segment)] != segment:
                raise ValueError('account path mismatch')
            position += len(segment)
            if leaf:
                if position != len(path) or not isinstance(node[1], bytes):
                    raise ValueError('leaf does not terminate at account key')
                value = node[1]
            else:
                if position >= len(path):
                    raise ValueError('extension exhausts account key')
                valid_reference(node[1])
                reference = node[1]
        else:
            raise ValueError('trie node must have 2 or 17 items')
        if value is not None:
            if not value or cursor != len(nodes):
                raise ValueError('absent value or unused proof nodes')
            return value
    raise ValueError('trie traversal limit exceeded')


def account_check(root, proof):
    if not isinstance(proof, dict) or set(proof) != {
            'address', 'accountProof', 'balance', 'codeHash', 'nonce',
            'storageHash', 'storageProof'}:
        raise ValueError('unexpected account proof fields')
    if data(proof['address'], 20) != data(ZTO, 20) or proof['storageProof'] != []:
        raise ValueError('only the ZTO account with no storage slots is supported')
    nonce, balance = quantity(proof['nonce']), quantity(proof['balance'])
    storage, code = data(proof['storageHash'], 32), data(proof['codeHash'], 32)
    key = header.keccak256(data(ZTO, 20))
    account = decode_rlp(inclusion(root, key, proof['accountProof']))
    if (not isinstance(account, list) or len(account) != 4 or
            any(not isinstance(item, bytes) for item in account)):
        raise ValueError('account must contain four byte fields')
    for integer in account[:2]:
        if len(integer) > 32 or (integer and integer[0] == 0):
            raise ValueError('account integers must be canonical uint256')
    if len(account[2]) != 32 or len(account[3]) != 32:
        raise ValueError('account roots must be 32 bytes')
    if [int.from_bytes(account[0], 'big'), int.from_bytes(account[1], 'big'),
            account[2], account[3]] != [nonce, balance, storage, code]:
        raise ValueError('RPC claims differ from the proved account')
    return {'nonce': str(nonce), 'native_balance_wei': str(balance),
            'storage_root': '0x' + storage.hex(), 'code_hash': '0x' + code.hex(),
            'account_key': '0x' + key.hex(), 'proof_nodes': len(proof['accountProof'])}


def snapshot_anchor(path):
    raw, snapshot, facts = seal.load_snapshot(path)
    checks = [header.check_header(snapshot[name]) for name in ('block', 'block_after')]
    if not all(item['matches'] for item in checks):
        raise ValueError('both snapshot headers must recompute to their reported hashes')
    if data(snapshot['block']['stateRoot'], 32) != data(snapshot['block_after']['stateRoot'], 32):
        raise ValueError('snapshot state roots differ')
    return raw, snapshot, facts


def verify_bundle(snapshot_path, bundle):
    raw, snapshot, facts = snapshot_anchor(snapshot_path)
    if not isinstance(bundle, dict) or set(bundle) != {
            'schema', 'captured_at', 'endpoint', 'chain_id', 'snapshot_sha256',
            'block_number', 'block_hash', 'state_root', 'proof', 'block_after'}:
        raise ValueError('unexpected proof bundle fields')
    if bundle['schema'] != SCHEMA or bundle['chain_id'] != '0x1':
        raise ValueError('unsupported proof schema or chain')
    rpc.validate_endpoint(bundle['endpoint'])
    stamp = bundle['captured_at']
    if not isinstance(stamp, str) or not stamp.endswith('Z'):
        raise ValueError('capture time must be UTC')
    dt.datetime.fromisoformat(stamp[:-1] + '+00:00')
    if bundle['snapshot_sha256'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('proof belongs to different snapshot bytes')
    block = snapshot['block']
    if (bundle['block_number'] != block['number'] or
            data(bundle['block_hash'], 32) != data(block['hash'], 32) or
            data(bundle['state_root'], 32) != data(block['stateRoot'], 32)):
        raise ValueError('proof anchor differs from snapshot')
    after = bundle['block_after']
    if (not header.check_header(after)['matches'] or after['number'] != block['number'] or
            data(after['hash'], 32) != data(block['hash'], 32) or
            data(after['stateRoot'], 32) != data(block['stateRoot'], 32)):
        raise ValueError('post-proof header differs from snapshot')
    account = account_check(data(bundle['state_root'], 32), bundle['proof'])
    return {'schema': 'pinned-zto-account-proof-check/1', 'verified': True,
            'snapshot_sha256': bundle['snapshot_sha256'],
            'token': ZTO, 'block_number': facts['block_number'],
            'block_hash': block['hash'], 'state_root': bundle['state_root'],
            'reported_provenance': {
                'snapshot_endpoint': snapshot['endpoint'],
                'snapshot_captured_at': snapshot['captured_at'],
                'proof_endpoint': bundle['endpoint'],
                'proof_captured_at': bundle['captured_at']},
            'account': account, 'network_used': False,
            'reported_total_supply_base_units': facts['total_supply_base_units'],
            'evidence_limits': ('Account inclusion relative to a provider-supplied, '
                'self-consistent Prague header. No trusted mainnet anchor, consensus or '
                'finality verification. The account native ETH balance is not a ZTO '
                'token balance. No storage slot, bytecode preimage or eth_call result '
                'is proved; totalSupply remains an unproved provider observation.')}


def load_bundle(path):
    return rpc.strict_json(seal.read_bytes(path))


def validate_request(method, params):
    if method == 'eth_chainId' and params == []:
        return
    if (method == 'eth_getProof' and isinstance(params, list) and len(params) == 3
            and params[:2] == [ZTO, []]):
        quantity(params[2])
        return
    if (method == 'eth_getBlockByNumber' and isinstance(params, list) and len(params) == 2
            and params[1] is False):
        quantity(params[0])
        return
    raise ValueError('only fixed read-only account-proof requests are allowed')


def public_read(endpoint, method, params):
    rpc.validate_endpoint(endpoint)
    validate_request(method, params)
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                       'params': params}, allow_nan=False).encode('ascii')
    request = urllib.request.Request(endpoint, data=body, headers={
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'Accept-Encoding': 'identity', 'User-Agent': USER_AGENT})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), rpc.NoRedirect())
    with opener.open(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError('RPC requires HTTP 200')
        if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
            raise ValueError('compressed response refused')
        raw = response.read(MAX_FILE + 1)
    if len(raw) > MAX_FILE:
        raise ValueError('RPC response exceeds bound')
    value = rpc.strict_json(raw)
    if not isinstance(value, dict) or set(value) != {'jsonrpc', 'id', 'result'}:
        raise ValueError('expected exact successful JSON-RPC envelope')
    return rpc.validate_response(value)


def capture(snapshot_path, endpoint=rpc.DEFAULT_RPC, read=None):
    raw, snapshot, _ = snapshot_anchor(snapshot_path)
    rpc.validate_endpoint(endpoint)
    read = read or (lambda method, params: public_read(endpoint, method, params))
    if read('eth_chainId', []) != '0x1':
        raise ValueError('Ethereum mainnet chain ID required')
    block = snapshot['block']
    proof = read('eth_getProof', [ZTO, [], block['number']])
    after = read('eth_getBlockByNumber', [block['number'], False])
    bundle = {'schema': SCHEMA,
              'captured_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
              'endpoint': endpoint, 'chain_id': '0x1',
              'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
              'block_number': block['number'], 'block_hash': block['hash'],
              'state_root': block['stateRoot'], 'proof': proof, 'block_after': after}
    verify_bundle(snapshot_path, bundle)
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo', help='offline retained real Ethereum proof')
    check = sub.add_parser('check', help='offline check of a saved proof bundle')
    check.add_argument('snapshot')
    check.add_argument('proof_bundle')
    cap = sub.add_parser('capture', help='read public proof at the exact snapshot block')
    cap.add_argument('snapshot')
    cap.add_argument('--rpc', default=rpc.DEFAULT_RPC)
    args = parser.parse_args()
    try:
        if args.command == 'capture':
            result = capture(args.snapshot, args.rpc)
        elif args.command == 'demo':
            folder = Path(__file__).resolve().parent
            result = verify_bundle(folder / 'live-zto.json', load_bundle(folder / 'live-proof.json'))
        else:
            result = verify_bundle(args.snapshot, load_bundle(args.proof_bundle))
        output = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
        if len(output.encode('utf-8')) > MAX_FILE:
            raise ValueError('output exceeds bound')
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, RecursionError,
            http.client.HTTPException):
        print('account-proof-check: invalid evidence or public RPC failure; no result emitted',
              file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
