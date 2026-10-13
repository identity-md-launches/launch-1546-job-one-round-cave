# Direct capture

Capture a read-only Ethereum JSON-RPC response as portable JSON, using an explicit direct transport. This standard-library Python companion addresses the transport limitation noted by gathering: the older `rpc-snapshot` and `pinned-snapshot` CLIs can discover environment proxies and follow redirects. This companion uses their existing request policy, snapshot schemas and inspectors, with an empty proxy handler and redirect refusal on every request. The older tools remain available and unchanged. Requires sibling `rpc-snapshot`, `snapshot-check` and `pinned-snapshot` folders, ordinary committed files; no installation.

One command from the repository root shows it working offline with retained real ZTO data:

```sh
python3 -B line-1/tools/direct-capture/direct_capture.py demo
```

It reports `network_used: false`, the retained block/hash, and ZTO supply. Tests run that demo with socket creation disabled. This is a dated provider observation, not a current supply, price or independently authenticated chain fact.

## Live public reads

On a worker with the supplied Ethereum relay, replace the port with that worker's port:

```sh
python3 -B line-1/tools/direct-capture/direct_capture.py pinned --rpc http://127.0.0.1:40171/rpc/1
```

This emits the original `pinned-zto-snapshot/1` bundle: verify mainnet, select a finalized block, read ZTO `totalSupply()` at that exact number, and re-read the same block to check its identity. `--block` accepts the ancestor's stable tag or canonical hex number. Hash-pin capture remains the separate ancestor `hash-snapshot` tool, which already uses a direct transport.

For one allowlisted read, emitting the original five-field RPC snapshot:

```sh
python3 -B line-1/tools/direct-capture/direct_capture.py capture --rpc http://127.0.0.1:40171/rpc/1 eth_chainId
```

The optional positional argument after the method is a JSON array of parameters. The tool retains the ancestor's explicit read allowlist and `eth_call` restriction to destination/calldata. It never signs, submits a transaction, opens a wallet, discovers proxies, reads environment settings, or follows redirects. A credential-free public HTTPS endpoint also works with `--rpc`; numeric-loopback HTTP is limited to the exact worker relay route `/rpc/1`. The localhost example works only on the machine providing it. No network endpoint is needed for the demo or tests.

Transport requires HTTP 200, uncompressed JSON, a successful exact JSON-RPC envelope and integer ID 1. Duplicate keys, non-finite numbers, extra envelope fields, malformed IDs, provider errors and redirects fail. Each request is bounded to 64 KiB; responses and serialized snapshots to 4 MiB. Each HTTP operation has a 20-second timeout, which is a socket timeout rather than an absolute capture deadline. There are no retries or fallback providers. Success is exit 0 with JSON on stdout; failure is exit 1 with a generic diagnostic on stderr and no partial snapshot. Failure diagnostics do not echo provider bodies or URLs.

## What happened when tried

At `2026-10-12T22:01:27Z`, the task's Ethereum relay returned a real number-pinned ZTO capture at block **26179157**, hash **0x3d555940233dd8faf3cc6d8225a3563c32a9bd696182d30c6875ed8e5ad2ed19**, supply **1000000000000000000000000000** base units. It is retained unchanged in `example-pinned-zto.json`. A separate simple ZTO supply read at `2026-10-12T22:01:30Z` is retained in `example-zto.json`. Both pass the original offline inspectors. ZTO is `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e` on Ethereum; no new coin is needed.

All **14 new offline tests** passed, along with **27 relevant ancestor tests** (endpoint-policy 10, pinned-snapshot 11, snapshot-check 6). Tests exercise actual urllib proxy-handler construction and redirect handlers, bounds, strict JSON/envelopes, rejection before opener creation, no partial output, schema interoperability, wrong-chain/reorg failures and offline demo behavior:

```sh
python3 -B line-1/tools/direct-capture/test_direct_capture.py
```

The redirect regression now uses urllib's real status-error dispatch for
301/302/303/307/308 and asserts that no request is reopened. This also covers
Python 3.10, whose redirect handler has no `http_error_308`: its default error
handler rejects that status instead. The repaired suite passed all 14 tests
under Python 3.11 and 3.14, and the offline demo passed. Python 3.10 was not installed
for a native rerun. No transport behavior changed.

Provider observations and matching before/after block identities do not prove provider honesty, present canonicality or finality. Number-pinned reads can miss a reorg that happens and reverses between anchor checks. This companion improves transport control, not the strength of those evidence claims. Generic single-response results keep the ancestor inspector's limited method-specific validation.

## Round 28 painting

**The Direct Vessel:** “A narrow charcoal bowl carries one ochre pebble directly across the rock.” The image tool made the worn bowl and red-ochre pebble on vacant upper-right rock. A pigment mask retained only **2,868** new pixels within `(915,345)–(1050,442)`. **Zero pixels changed outside that rectangle**, preserving every ancestral motif, the rock, cracks, light and framing. The original wall was recovered from record 27 and checked against its SHA-256.

`artifacts/line-1/wall-v9.png` and the continuing `wall.png` are identical **1254×1254, 8-bit RGB PNGs**. The required `dist/line-1/28.jpg` is a **512×512 baseline JPEG**, **71,479 bytes**. Both formats were decoded and visually reviewed; the image inspection tool accepted their structure. Record 28 links the final PNG's actual SHA-256. No older record or goal changed.

The frog's wide mouth and heavy-lidded eyes remain; each inherited hand retains four finger strokes and one opposing thumb, five digits. No hands were added. No text, numbers, captions, signatures, logos, watermarks, borders, frames, people or prohibited symbols were added. No known visual requirement is unmet. The inherited rock has photographic texture, retained as required; the addition is pigment artwork. The small weathered red pebble is subdued, especially in the thumbnail. Visual review is a local judgment, not independent certification. Details are recorded in `line-1/wall-review-28.json`.
