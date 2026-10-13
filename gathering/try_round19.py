#!/usr/bin/env python3
"""Fresh read-only trials using the assigned relay and public provenance alias."""
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gathering/checks/round-19'
PUBLIC = 'https://ethereum-rpc.publicnode.com'
RELAY = 'http://127.0.0.1:39931/rpc/1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def save(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    if len(data) >= 100000:
        raise ValueError('evidence exceeds submission file bound')
    (OUT / (name + '.json')).write_bytes(data)
    print(name, len(data), flush=True)


def main():
    proof = load('round19_proof', 'line-1/tools/account-proof-check/account_proof_check.py')
    pinned = proof.seal.pinned
    selected_block = json.loads((OUT / 'pinned-zto-supply.json').read_bytes())['block']['number']
    snapshot = pinned.capture(PUBLIC, tag=selected_block, read=lambda m,p: pinned.public_read(RELAY,m,p))
    save('public-zto-snapshot', snapshot)
    path = OUT / 'public-zto-snapshot.json'
    bundle = proof.capture(path, PUBLIC, read=lambda m,p: proof.public_read(RELAY,m,p))
    save('public-zto-proof', bundle)
    save('public-zto-proof-check', proof.verify_bundle(path, bundle))
    audit = load('round19_audit', 'line-4/tools/transfer-anchor-audit/audit.py')
    capture = audit.reader.read_capture(ROOT / 'line-4/tools/transfer-crosscheck/publicnode.json')
    native_rpc = audit.window.rpc
    with patch.object(audit.window, 'rpc', side_effect=lambda _endpoint,m,p: native_rpc(RELAY,m,p)):
        evidence = audit.collect(capture, PUBLIC)
    save('public-anchor-evidence', evidence)
    save('public-anchor-check', audit.report(capture, evidence))
    save('transport-note', {'network':'Ethereum mainnet','public_source_alias':PUBLIC,
         'transport':'Assigned contributor relay; alias is supplied by the task and does not authenticate the upstream provider.',
         'methods':['eth_chainId','eth_getBlockByNumber','eth_call','eth_getProof'],
         'keys_wallets_signing_or_submission':False})

if __name__ == '__main__':
    main()
