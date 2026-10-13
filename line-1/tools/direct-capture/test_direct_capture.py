#!/usr/bin/env python3
"""Offline transport and legacy-format interoperability regressions."""
import contextlib
import copy
import io
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import direct_capture as tool

EXAMPLE = tool.parse(Path(__file__).with_name('example-pinned-zto.json').read_bytes())
RELAY = EXAMPLE['endpoint']


class Response(io.BytesIO):
    def __init__(self, raw, status=200, headers=None):
        super().__init__(raw)
        self.status = status
        self.headers = headers or {}


class Tests(unittest.TestCase):
    def reply(self, value):
        return json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': value}).encode()

    def test_no_proxy_discovery_or_default_urlopen(self):
        # Fail on urllib's actual discovery function, rather than reading any env.
        with patch.object(urllib.request, 'getproxies', side_effect=AssertionError('proxy discovery')), \
             patch.object(urllib.request, 'urlopen', side_effect=AssertionError('default transport')), \
             patch.object(urllib.request.OpenerDirector, 'open',
                          return_value=Response(self.reply('0x1'))) as opened:
            self.assertEqual(tool.public_read(RELAY, 'eth_chainId', []), '0x1')
            request = opened.call_args.args[0]
            self.assertEqual(request.full_url, RELAY)
            self.assertEqual(request.get_method(), 'POST')
            self.assertEqual(opened.call_args.kwargs['timeout'], 20)
            self.assertEqual(request.get_header('User-agent'), tool.USER_AGENT)
            self.assertEqual(request.get_header('Accept-encoding'), 'identity')
            self.assertEqual(json.loads(request.data),
                             {'jsonrpc': '2.0', 'id': 1, 'method': 'eth_chainId', 'params': []})

    def test_real_opener_has_empty_proxy_handler_and_redirect_refusal(self):
        handlers = []
        real_build = urllib.request.build_opener
        def build(*supplied):
            handlers.extend(supplied)
            return real_build(*supplied)
        with patch.object(urllib.request, 'getproxies', side_effect=AssertionError('discovery')), \
             patch.object(urllib.request, 'build_opener', side_effect=build), \
             patch.object(urllib.request.OpenerDirector, 'open', return_value=Response(self.reply('0x1'))):
            tool.public_read(RELAY, 'eth_chainId', [])
        proxies = [h for h in handlers if isinstance(h, urllib.request.ProxyHandler)]
        self.assertEqual(len(proxies), 1)
        self.assertEqual(proxies[0].proxies, {})
        self.assertTrue(any(isinstance(h, tool.NoRedirect) for h in handlers))

    def test_redirect_http_handlers_cannot_reissue_request(self):
        request = urllib.request.Request(RELAY, data=b'{}')
        opener = urllib.request.OpenerDirector()
        opener.add_handler(tool.NoRedirect())
        opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
        # Exercise urllib's actual error dispatch. Python 3.10 has no dedicated
        # http_error_308 method and rejects 308 through the default handler.
        with patch.object(opener, 'open', side_effect=AssertionError('redirect reissued')) as reopened:
            for code in (301, 302, 303, 307, 308):
                with self.subTest(code=code), io.BytesIO() as response, \
                     self.assertRaises((ValueError, urllib.error.HTTPError)):
                    opener.error('http', request, response, code, 'redirect',
                                 {'location': 'https://eth.drpc.org'})
            reopened.assert_not_called()

    def test_rejected_endpoint_and_method_before_opener(self):
        requests = [('http://example.com', 'eth_chainId', []),
                    (RELAY + '?key=not-used', 'eth_chainId', []),
                    (RELAY, 'eth_sendRawTransaction', ['0x']),
                    (RELAY, 'eth_sendTransaction', [{}]),
                    (RELAY, 'personal_listAccounts', []),
                    (RELAY, 'eth_call', [{'to': tool.pinned.ZTO, 'data': '0x', 'from': tool.pinned.ZTO}, 'latest'])]
        with patch.object(urllib.request, 'build_opener') as opener:
            for endpoint, method, params in requests:
                with self.subTest(method=method), self.assertRaises(ValueError):
                    tool.public_read(endpoint, method, params)
            opener.assert_not_called()

    def test_response_bound_applies_before_json_parsing(self):
        with patch.object(tool, 'MAX_BYTES', 32), \
             patch.object(urllib.request.OpenerDirector, 'open', return_value=Response(b' ' * 33)):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                tool.public_read(RELAY, 'eth_chainId', [])

    def test_request_bound_applies_before_opener(self):
        with patch.object(urllib.request, 'build_opener') as opener:
            with self.assertRaisesRegex(ValueError, '64 KiB'):
                tool.public_read(RELAY, 'eth_call', [{'to': tool.pinned.ZTO, 'data': '0x' + 'ab' * 65536}, 'latest'])
            opener.assert_not_called()

    def test_strict_response_envelopes(self):
        bad = [b'null', b'[]', b'{', b'\xff',
               b'{"jsonrpc":"2.0","id":1,"id":1,"result":"0x1"}',
               b'{"jsonrpc":"2.0","id":1,"result":NaN}',
               self.reply('0x1').replace(b'"id": 1', b'"id": true'),
               self.reply('0x1').replace(b'"id": 1', b'"id": 2'),
               b'{"jsonrpc":"2.0","id":1,"result":"0x1","extra":0}',
               b'{"jsonrpc":"2.0","id":1,"error":{"code":-1,"message":"not echoed"}}']
        for raw in bad:
            with self.subTest(raw=raw), \
                 patch.object(urllib.request.OpenerDirector, 'open', return_value=Response(raw)), \
                 self.assertRaises((ValueError, RuntimeError)):
                tool.public_read(RELAY, 'eth_chainId', [])

    def test_bad_http_status_or_compression(self):
        for status, headers in ((204, {}), (201, {}), (200, {'Content-Encoding': 'gzip'})):
            with patch.object(urllib.request.OpenerDirector, 'open',
                              return_value=Response(self.reply('0x1'), status, headers)), \
                 self.assertRaises(ValueError):
                tool.public_read(RELAY, 'eth_chainId', [])

    def test_single_capture_ancestor_inspection(self):
        original = tool.parse(Path(__file__).with_name('example-zto.json').read_bytes())
        with patch.object(tool, 'public_read', return_value=original['result']):
            snapshot = tool.capture(RELAY, original['method'], original['params'])
        self.assertEqual(tool.check.summarize(snapshot)['result'], original['result'])
        self.assertEqual(snapshot['endpoint'], RELAY)
        self.assertEqual(set(snapshot), set(original))

    def replay_pinned(self, change=None):
        results = copy.deepcopy([EXAMPLE['chain_id'], EXAMPLE['block'], EXAMPLE['result'], EXAMPLE['block_after']])
        if change:
            change(results)
        calls = []
        def read(endpoint, method, params):
            calls.append((endpoint, method, copy.deepcopy(params)))
            return results[len(calls) - 1]
        return read, calls

    def test_pinned_reuses_transport_and_original_inspector(self):
        read, calls = self.replay_pinned()
        with patch.object(tool, 'public_read', side_effect=read):
            snapshot = tool.capture_pinned(RELAY)
        self.assertEqual(tool.pinned.inspect(snapshot), tool.pinned.inspect(EXAMPLE))
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(call[0] == RELAY for call in calls))
        self.assertEqual(calls[2][2], [tool.pinned.CALL, EXAMPLE['block']['number']])

    def test_pinned_wrong_chain_and_reorg_refused(self):
        for change in (lambda r: r.__setitem__(0, '0x2'),
                       lambda r: r[3].__setitem__('hash', r[1]['parentHash'])):
            read, calls = self.replay_pinned(change)
            with patch.object(tool, 'public_read', side_effect=read), self.assertRaises(ValueError):
                tool.capture_pinned(RELAY)
            self.assertIn(len(calls), (1, 4))

    def test_demo_with_network_creation_disabled(self):
        out = io.StringIO()
        with patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             patch.object(tool, 'public_read', side_effect=AssertionError('network')), \
             patch.object(sys, 'argv', ['direct', 'demo']), contextlib.redirect_stdout(out):
            self.assertEqual(tool.main(), 0)
        summary = json.loads(out.getvalue())
        self.assertFalse(summary['network_used'])
        self.assertEqual(summary['block_hash'], EXAMPLE['block']['hash'])

    def test_cli_failure_emits_no_snapshot_or_provider_text(self):
        for argv in (['direct', 'capture', '--rpc', RELAY, 'eth_sendRawTransaction', '["0x"]'],
                     ['direct', 'capture', '--rpc', RELAY, 'eth_chainId', '[NaN]'],
                     ['direct', 'capture', '--rpc', RELAY]):
            out, err = io.StringIO(), io.StringIO()
            with patch.object(sys, 'argv', argv), \
                 patch.object(urllib.request.OpenerDirector, 'open', side_effect=OSError('private-provider-text')), \
                 contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(tool.main(), 1)
            self.assertEqual(out.getvalue(), '')
            self.assertNotIn('private-provider-text', err.getvalue())
            self.assertNotIn(RELAY, err.getvalue())

    def test_serialized_output_bound(self):
        with patch.object(tool, 'MAX_BYTES', 8), self.assertRaises(ValueError):
            tool.encode({'result': '0x12345678'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
