#!/usr/bin/env python3
"""Carry a real ZTO account proof and its exact pinned snapshot in a HANDOFF ZIP."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import zipfile

from workspace_io import file_parts, read_workspace, save_new

HERE = Path(__file__).resolve().parent
MAX_BYTES = 99000
SNAPSHOT = 'evidence/snapshot.json'
PROOF = 'evidence/account-proof.json'
REPORT = 'review/account.json'
PATHS = {SNAPSHOT, PROOF, REPORT}


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, HERE / 'vendor' / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


proof = load('proof_handoff_verifier', 'account-proof-check/account_proof_check.py')
writer = load('proof_handoff_writer', 'handoff/handoff.py')
inspector = load('proof_handoff_inspector', 'handoff-inspect/inspect_handoff.py')
LIMITS = inspector.Limits(archive_bytes=MAX_BYTES, payload_bytes=MAX_BYTES,
                         manifest_bytes=4096, metadata_bytes=4096, files=3)


def canonical(value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    if len(raw) > MAX_BYTES:
        raise ValueError('report exceeds byte limit')
    return raw


def bounded(raw):
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValueError('nonempty immutable bytes of at most 99000 required')
    return raw


def recompute(snapshot, bundle):
    bounded(snapshot)
    bounded(bundle)
    # Native validator checks exact snapshot digest, all three headers, MPT
    # inclusion and the four account claims. No file or network read is needed.
    result = proof.verify_bundle(snapshot, proof.rpc.strict_json(bundle))
    result['proof_sha256'] = hashlib.sha256(bundle).hexdigest()
    return result


def inspect_bytes(data, expected=None):
    bounded(data)
    receipt = inspector.inspect_stream(io.BytesIO(data), LIMITS, expected)
    if {entry['path'] for entry in receipt['files']} != PATHS:
        raise ValueError('exact snapshot, proof and report required')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = {name: archive.read(name) for name in PATHS}
    report = recompute(files[SNAPSHOT], files[PROOF])
    if files[REPORT] != canonical(report):
        raise ValueError('stored report differs from recomputed proof')
    if writer.build(files) != data:
        raise ValueError('archive does not reproduce under HANDOFF writer')
    result = {'schema': 'zto-account-proof-handoff/1', 'verified': True,
              'account_proof_recomputed': True, 'byte_reproducible': True,
              'archive_sha256': receipt['archive_sha256'],
              'archive_bytes': len(data), 'trusted_digest_matched': expected is not None,
              'network_used': False, 'payloads_extracted_or_executed': False,
              'account': report,
              'limitations': 'Inclusion relative to a supplied state root, not an authenticated mainnet root. '
              'No consensus, finality, storage slot, token balance or totalSupply proof. '
              'ZIP integrity and reproduction do not authenticate its sender.'}
    canonical(result)
    return result


def build(snapshot, bundle):
    report = recompute(snapshot, bundle)
    files = {SNAPSHOT: snapshot, PROOF: bundle, REPORT: canonical(report)}
    if sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError('combined payload exceeds 99000 bytes; choose a smaller complete capture')
    data = writer.build(files)
    inspect_bytes(data)
    return data


def demo():
    snapshot = (HERE / 'examples/zto-snapshot.json').read_bytes()
    bundle = (HERE / 'examples/zto-proof.json').read_bytes()
    data = build(snapshot, bundle)
    if data != build(snapshot, bundle):
        raise ValueError('nondeterministic build')
    result = inspect_bytes(data)
    result['demo'] = 'Dated real ZTO account proof; no network, writes or extraction.'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    pack = commands.add_parser('pack')
    pack.add_argument('snapshot')
    pack.add_argument('proof')
    pack.add_argument('archive')
    check = commands.add_parser('check')
    check.add_argument('archive')
    check.add_argument('--sha256', help='independently retained archive digest')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            result = demo()
        elif args.command == 'pack':
            file_parts(args.archive)
            data = build(read_workspace(args.snapshot), read_workspace(args.proof))
            result = inspect_bytes(data)
            result['output'] = args.archive
            encoded = canonical(result)
            save_new(args.archive, data)
            sys.stdout.write(encoded.decode('ascii'))
            return 0
        else:
            result = inspect_bytes(read_workspace(args.archive), args.sha256)
        sys.stdout.write(canonical(result).decode('ascii'))
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, UnicodeError,
            RecursionError, OverflowError, zipfile.BadZipFile, EOFError,
            NotImplementedError, struct.error):
        print('proof-handoff: invalid, over-limit or inconsistent evidence; no receipt', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
