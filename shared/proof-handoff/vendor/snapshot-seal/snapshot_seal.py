#!/usr/bin/env python3
"""Make and verify deterministic offline receipts for pinned ZTO snapshots."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / 'pinned-snapshot' / 'pinned_snapshot.py'
spec = importlib.util.spec_from_file_location('pinned_snapshot', PINNED)
pinned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pinned)
MAX_BYTES = 4 * 1024 * 1024
SCHEMA = 'pinned-zto-seal/1'
WORKSPACE = Path.cwd()


def read_bytes(path):
    # Walk from an already-open workspace directory. Reject symlinks at every
    # component; dir_fd and O_NOFOLLOW also protect against path-swap races.
    candidate = Path(os.path.abspath(path))
    try:
        parts = candidate.relative_to(WORKSPACE).parts
    except ValueError as exc:
        raise ValueError('input must be inside this workspace') from exc
    if not parts:
        raise ValueError('input must be a regular file')
    directory = os.open(WORKSPACE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        info = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError('input must be a regular file of at most 4 MiB')
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ValueError('input must be a regular file of at most 4 MiB')
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('file exceeds 4 MiB')
        return data
    finally:
        os.close(directory)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True).encode('ascii')


def load_snapshot(path):
    raw = read_bytes(path)
    try:
        value = pinned.rpc.strict_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('snapshot is not valid JSON') from exc
    facts = pinned.inspect(value)
    return raw, value, facts


def seal(path):
    raw, snapshot, facts = load_snapshot(path)
    return {
        'schema': SCHEMA,
        'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
        'canonical_snapshot_sha256': hashlib.sha256(canonical(snapshot)).hexdigest(),
        'observation': {
            'block_number': facts['block_number'],
            'block_hash': facts['block_hash'],
            'token': facts['token'],
            'total_supply_base_units': facts['total_supply_base_units'],
        },
        'evidence_limits': ('Integrity receipt for bytes and the pinned snapshot structure; '
                            'not a signature, proof of provider honesty, finality, or current state.'),
    }


def verify(snapshot_path, receipt_path):
    receipt_raw = read_bytes(receipt_path)
    try:
        receipt = pinned.rpc.strict_json(receipt_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('receipt is not valid JSON') from exc
    expected = seal(snapshot_path)
    if receipt != expected:
        raise ValueError('receipt does not exactly match this snapshot')
    return {'verified': True, **expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    seal_parser = commands.add_parser('seal', help='print a deterministic receipt')
    seal_parser.add_argument('snapshot')
    verify_parser = commands.add_parser('verify', help='check a saved receipt offline')
    verify_parser.add_argument('snapshot')
    verify_parser.add_argument('receipt')
    args = parser.parse_args()
    try:
        result = seal(args.snapshot) if args.command == 'seal' else verify(args.snapshot, args.receipt)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, RecursionError):
        print('snapshot-seal: invalid pinned snapshot or receipt', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
