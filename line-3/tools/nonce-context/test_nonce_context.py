"""Behavioral checks; fixtures are unsigned and never executed."""
import contextlib
import io
import unittest
import nonce_context as n


def proposal(nonce, chain=1):
    return '0x02' + n.tx_decode.rlp_encode([
        chain, nonce, 1_000_000_000, 2_000_000_000, 100000,
        bytes.fromhex(n.tx_decode.ZTO[2:]), 0, bytes.fromhex('18160ddd'), []
    ]).hex()


class Checks(unittest.TestCase):
    def test_demo_real_destination(self):
        r = n.inspect(n.tx_decode.demo_transaction(), '1', '0', '0')
        self.assertEqual(r['status'], 'at-pending-frontier')
        self.assertEqual(r['destination'], n.tx_decode.ZTO)
        self.assertEqual(r['calldataSelector'], '0x18160ddd')

    def test_below_latest(self):
        r = n.inspect(proposal(4), '1', '5', '8')
        self.assertEqual(r['status'], 'below-latest')
        self.assertEqual(r['distanceFromLatest'], '-1')
        self.assertEqual(r['missingNoncesBeforeProposal'], '0')

    def test_pending_boundaries(self):
        for nonce in (5, 7):
            with self.subTest(nonce=nonce):
                r = n.inspect(proposal(nonce), '1', '5', '8')
                self.assertEqual(r['status'], 'within-pending-window')
                self.assertEqual(r['pendingWindowWidth'], '3')

    def test_frontier(self):
        self.assertEqual(n.inspect(proposal(8), '1', '5', '8')['status'], 'at-pending-frontier')

    def test_gap_exact(self):
        r = n.inspect(proposal(12), '1', '5', '8')
        self.assertEqual(r['status'], 'above-pending-frontier')
        self.assertEqual(r['missingNoncesBeforeProposal'], '4')

    def test_empty_window(self):
        self.assertEqual(n.inspect(proposal(5), '1', '5', '5')['status'], 'at-pending-frontier')

    def test_large_exact_integers(self):
        value = 2**200
        r = n.inspect(proposal(value + 7), '1', str(value), str(value + 2))
        self.assertEqual(r['missingNoncesBeforeProposal'], '5')
        self.assertEqual(r['proposalNonce'], str(value + 7))

    def test_inconsistent_context(self):
        for chain, latest, pending in [('2', '0', '0'), ('1', '3', '2'), ('0', '0', '0')]:
            with self.subTest(context=(chain, latest, pending)), self.assertRaises(ValueError):
                n.inspect(proposal(0), chain, latest, pending)

    def test_invalid_counts(self):
        for value in ('', '-1', '+1', '01', ' 1', '1.0', '0x1', str(2**256), True, 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                n.inspect(proposal(0), '1', value, '0')

    def test_oversized_proposal_nonce(self):
        with self.assertRaises(ValueError):
            n.inspect(proposal(2**256), '1', '0', '0')

    def test_reject_malformed_or_signed(self):
        fields, _ = n.tx_decode.rlp_item(bytes.fromhex(proposal(0)[2:]), 1)
        signed = '0x02' + n.tx_decode.rlp_encode(fields + [0, 1, 1]).hex()
        for value in ('0x', proposal(0) + '00', signed, '0x01c0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                n.inspect(value, '1', '0', '0')

    def test_hex_spelling_same_fingerprint(self):
        text = proposal(0)
        a = n.inspect(text, '1', '0', '0')
        b = n.inspect(text[2:].upper(), '1', '0', '0')
        self.assertEqual(a, b)

    def test_cli_invalid_no_partial_report(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = n.main(['--demo', '--chain-id', '2', '--latest-nonce', '0', '--pending-nonce', '0'])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertIn('chain ID', err.getvalue())

    def test_stdin_bound_before_strip(self):
        from unittest.mock import patch
        with patch('sys.stdin', io.StringIO(' ' * (2 * n.tx_decode.MAX_TRANSACTION_BYTES + 3))):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(n.main(['--stdin', '--chain-id', '1', '--latest-nonce', '0', '--pending-nonce', '0']), 2)


if __name__ == '__main__':
    unittest.main()
