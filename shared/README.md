# Shared pieces

[`horizon-context/`](horizon-context/README.md) (Gathering 15) joins Line 3's
fee-horizon model to Line 1's complete pinned ZTO snapshot. Observed parent
fees and hypothetical child fees remain separate, with exact evidence digests.
Eight unchanged dependencies make the folder standalone standard-library Python.

```sh
python3 -B shared/horizon-context/horizon_context.py demo
```

Ten integration tests passed using a fresh real ZTO parent observation and an
explicitly synthetic unsigned proposal. Gathering 16 refreshes the native model repair: original parents are uint256,
while hypothetical intermediates can grow beyond it. The twice-target gas
assumption remains documented.

[`evidence-handoff/`](evidence-handoff/README.md) (gathering 01) shares Line 2's deterministic
handoff utility and joins the public JSON outputs from Lines 1, 3 and 4 into one
offline-verifiable archive. It has no network or third-party dependencies.

```sh
python3 -B shared/evidence-handoff/bundle.py demo
```

[`tx-preflight/`](tx-preflight/README.md) (gathering 02) joins Line 3's offline decoder with Line 1's
read-only RPC validators. It checks an unsigned EIP-1559 transaction against
live state pinned to one block: chain, fees, nonce, ETH for gas, and ERC-20
amount, balance and recipient. Every read is kept as a Line 1 snapshot, so the
same evidence replays offline.

```sh
python3 -B shared/tx-preflight/preflight.py demo
```

[`evidence-review/`](evidence-review/README.md) (gathering 03) copies the newer
line validators into a portable kit. It packages pinned ZTO supply, validated
transfer windows, recomputed provider comparisons and original unsigned RLP
with ERC-20 intent. Inspection verifies archive integrity and rebuilds evidence
summaries. Live capture supports the supplied relay and links observations with
matching closing block hashes.

```sh
python3 -B shared/evidence-review/review.py demo
```

Use Evidence review when raw logs, block anchors or original RLP must be
revalidated; the first Evidence handoff checks simpler producer shapes.

The original line folders are unchanged. These are reusable worker tools, not
record viewers.

[`handoff-revision/`](handoff-revision/README.md) (gathering 04) joins Line 2's
verified archive and source comparisons with Line 3's complete unsigned-envelope
comparison. A worker sees file changes and exact transaction changes together,
and can check that the revised bundle still matches its public source directory.
The folder is portable and uses only the Python standard library.

```sh
python3 -B shared/handoff-revision/revision.py demo
```

[`anchor-bridge/`](anchor-bridge/README.md) (gathering 05) is a small offline
join for Line 1's block-pinned snapshot and Line 4's validated transfer window.
It emits a receipt only when both supplied observations have the exact same
closing block hash and height.

```sh
python3 -B shared/anchor-bridge/anchor_bridge.py demo
```

[`window-handoff/`](window-handoff/README.md) (gathering 06) joins Line 4's
validated transfer receipts with Line 2's deterministic packaging, streaming
inspection and filename screening. It accepts current schema-3 captures,
recomputes optional address summaries and saved receipts, and preserves
original evidence bytes. The folder is standalone standard-library Python.

```sh
python3 -B shared/window-handoff/window_handoff.py demo
```

[`call-witness/`](call-witness/README.md) (gathering 07, named output v8) joins
Line 1's offline snapshot replay with Line 3's unsigned gas-budget diagnostic.
It matches exact destination/calldata at the recorded hash and carries the
original response bytes with provenance, while explicitly keeping transaction
execution unverified. The folder is standalone standard-library Python.

```sh
python3 -B shared/call-witness/witness.py demo
```

Gathering 07 also refreshed Evidence review's Line 4 copies to accept current
schema-3 captures and revalidate optional address summaries. Its historical
schema-2 examples still pass; no line sources or old examples were changed.

## Pinned fee context (Gathering 08)

`pinned-fee-context/` joins Line 1's retained number-pinned ZTO observation to
Line 3's unsigned fee arithmetic. It validates the full snapshot and identical
before/after block base fees, then keeps the block identity beside the diagnostic.
Run `python3 -B shared/pinned-fee-context/pinned_fee.py demo` offline.
Six unchanged dependencies are vendored with provenance; no line folders needed.

## Batch handoff (Gathering 10)

`batch-handoff/` joins Line 1's ZTO-first, hash-pinned JSON-RPC batch with Line
2's deterministic HANDOFF v1 archive. It keeps the original response envelopes
and recomputes the inspection after archive verification. Five unchanged source
modules and a real dated ZTO/IMD example are included, so it runs without the
line folders or a network.

```sh
python3 -B shared/batch-handoff/batch_handoff.py demo
```

## Flow handoff (Gathering 11)

[`flow-handoff/`](flow-handoff/README.md) combines Line 4's directed counterparty
aggregation and raw-log checks with Line 2's deterministic writer and bounded
archive inspector. Recipients verify exact source bytes and recompute flows and
an explicit optional public-address filter. Six unchanged vendored modules make
it standalone; retained real ZTO evidence demonstrates the complete path.

```sh
python3 -B shared/flow-handoff/flow_handoff.py demo
```

Gathering 12 refreshed its vendored Line 4 validator with the native exact
event-type repair. A fresh real ZTO window and reproducible archive are now
included. Verify the dated archive without network access:

```sh
python3 -B shared/flow-handoff/flow_handoff.py check shared/flow-handoff/examples/round-12-zto-flows.zip
```

## Ledger handoff (Gathering 13)

[`ledger-handoff/`](ledger-handoff/README.md) carries Line 4's exact per-address
in/out/net event accounting through Line 2's reproducible archive format. The
receiver recomputes the ledger from raw logs, then checks a chosen workspace
landing directory for conflicts without extracting or overwriting. Eight
vendored dependencies and real ZTO evidence make it usable offline by a worker
who has never seen this repository.

```sh
python3 -B shared/ledger-handoff/ledger_handoff.py demo
```

The included fresh two-block ZTO archive also passed the native handoff review
and landing commands. Its receipt establishes internal consistency of dated
provider evidence, not balances, complete history, sender identity or finality.

## Stitch handoff (Gathering 14)

[`stitch-handoff/`](stitch-handoff/README.md) carries both raw transfer-window
sources through Line 2's deterministic archive format. It revalidates and
recomputes Line 4's overlap/adjacency join at the receiver, preserving the
original observations separately. Seven unchanged vendored modules make it
standalone and usable offline.

```sh
python3 -B shared/stitch-handoff/stitch_handoff.py demo
```

## Corroborated horizon (Gathering 16)

[`corroborated-horizon/`](corroborated-horizon/README.md) combines Line 1's
new fee/gas field crosscheck with Line 3's repaired fee horizon. It binds exact
source bytes, compares all four retained block replies, and produces no model
when providers disagree. Twelve unchanged modules make the folder standalone.

```sh
python3 -B shared/corroborated-horizon/corroborated.py demo
```

Twelve integration tests passed. Fresh real ZTO evidence also passed; Line 2's
subset tool carried its report into a reproducible, offline-verified archive.

## Timeline handoff (Gathering 17)

[timeline-handoff](timeline-handoff/README.md) joins Line 1's bounded ZTO supply
timeline to Line 2's explicit dependency closure. Exact source observations,
declarations and report travel together in a reproducible archive; the receiver
recomputes the timeline and rejects a rehashed false report. Eight vendored
ordinary modules make the complete folder portable, without line sources or
installation. Two import bases are adapted with exact source/copy provenance.

```sh
python3 -B shared/timeline-handoff/timeline_handoff.py demo
```

Twelve integration tests passed. The demo uses dated real ZTO evidence, preserves
unsampled gaps and carries conflicts as diagnostics. Integrity does not establish
provider honesty, complete history, finality, balances or a sender's identity.

## Account proof handoff (Gathering 19)

[proof-handoff](proof-handoff/README.md) joins Line 1's real ZTO account proof
with Line 2's deterministic archive. The receiver checks original snapshot
bytes, three header hashes, the account inclusion path and every account claim,
and rejects a rehashed false report. The complete folder runs offline.

```sh
python3 -B shared/proof-handoff/proof_handoff.py demo
```

Thirteen integration tests and native handoff review passed. The included
88,860-byte archive contains fresh dated real Ethereum evidence. Verification
is relative to a supplied state root; it does not authenticate mainnet consensus
or prove token balances, totalSupply, finality or sender identity.
