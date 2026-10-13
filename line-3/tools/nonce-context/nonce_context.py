#!/usr/bin/env python3
"""Explain an unsigned proposal's nonce against explicit offline account context."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'zto-eip1559-decoder'))
import tx_decode

UINT256_MAX = 2**256 - 1


def decimal(text, name):
    if not isinstance(text, str) or len(text) > 78 or re.fullmatch(r'0|[1-9][0-9]*', text) is None:
        raise ValueError(name + ' must be canonical nonnegative decimal text')
    number = int(text)
    if number > UINT256_MAX:
        raise ValueError(name + ' exceeds uint256')
    return number


def inspect(transaction, chain_id, latest_nonce, pending_nonce):
    chain = decimal(chain_id, 'context chain ID')
    latest = decimal(latest_nonce, 'latest nonce')
    pending = decimal(pending_nonce, 'pending nonce')
    if chain == 0:
        raise ValueError('context chain ID must be positive')
    if pending < latest:
        raise ValueError('pending nonce must not be below latest nonce')
    tx = tx_decode.decode(transaction)
    if tx['chainId'] != chain:
        raise ValueError('transaction chain ID does not match asserted context')
    nonce = tx['nonce']
    if nonce > UINT256_MAX:
        raise ValueError('transaction nonce exceeds uint256')
    if nonce < latest:
        status = 'below-latest'
        meaning = 'Proposal nonce precedes the asserted next confirmed-account nonce.'
    elif nonce < pending:
        status = 'within-pending-window'
        meaning = 'Proposal nonce lies in the asserted pending window; it may compete with another proposal.'
    elif nonce == pending:
        status = 'at-pending-frontier'
        meaning = 'Proposal nonce equals the asserted next pending-account nonce.'
    else:
        status = 'above-pending-frontier'
        meaning = 'Proposal nonce leaves a gap after the asserted pending-account frontier.'
    raw = bytes.fromhex(transaction[2:] if transaction.startswith('0x') else transaction)
    return {
        'schema': 'nonce-context/v1',
        'chainId': str(chain),
        'proposalNonce': str(nonce),
        'assertedLatestNonce': str(latest),
        'assertedPendingNonce': str(pending),
        'pendingWindowWidth': str(pending - latest),
        'distanceFromLatest': str(nonce - latest),
        'distanceFromPending': str(nonce - pending),
        'missingNoncesBeforeProposal': str(max(nonce - pending, 0)),
        'status': status,
        'meaning': meaning,
        'destination': tx['to'],
        'calldataSelector': tx['calldataSelector'],
        'unsignedBytesSha256': hashlib.sha256(raw).hexdigest(),
        'limitations': [
            'Counts and chain ID are caller assertions, not fetched or authenticated observations.',
            'An unsigned envelope has no recoverable sender. Caller must ensure both counts refer to the intended account on this chain.',
            'Pending counts are provider-local and can change; this does not discover queued transactions or identify a replacement.',
            'No protocol-validity, fee sufficiency, execution, inclusion, finality or signing-safety claim is made.',
            'Fingerprint is SHA-256 of unsigned bytes, not an Ethereum transaction hash.',
        ],
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--demo', action='store_true', help='synthetic unsigned real-ZTO totalSupply call')
    source.add_argument('--transaction', help='complete unsigned type-2 hex')
    source.add_argument('--stdin', action='store_true', help='read bounded hex text from stdin')
    parser.add_argument('--chain-id', required=True)
    parser.add_argument('--latest-nonce', required=True)
    parser.add_argument('--pending-nonce', required=True)
    args = parser.parse_args(argv)
    try:
        if args.demo:
            transaction = tx_decode.demo_transaction()
        elif args.stdin:
            # Check before stripping so whitespace cannot bypass the text limit.
            transaction = sys.stdin.read(2 * tx_decode.MAX_TRANSACTION_BYTES + 3)
            if len(transaction) > 2 * tx_decode.MAX_TRANSACTION_BYTES + 2:
                raise ValueError('stdin exceeds transaction text limit')
            transaction = transaction.strip()
        else:
            transaction = args.transaction
        report = inspect(transaction, args.chain_id, args.latest_nonce, args.pending_nonce)
    except (ValueError, UnicodeError) as error:
        print('error: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
