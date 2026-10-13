# Transfer anchor audit

Recheck the known block hashes in a saved ZTO transfer window against an
Ethereum mainnet provider. This helps a worker notice that previously captured
evidence no longer agrees with a numbered-block response, without fetching
the token's logs again. IMD captures are also supported. Python standard
library only; no install, wallet, credentials or indexer.

From the repository root, this one command works offline:

```sh
python3 -B line-4/tools/transfer-anchor-audit/audit.py --demo
```

It revalidates the retained real ZTO capture for blocks **26177298–26177309**
and replays `observations.json`, a fresh PublicNode read made on
**2026-10-13 at 09:27:41 UTC**. Both known hashes matched. The three observed
transfers occupy the last block, so two distinct blocks were checked and
**ten interior blocks remain unchecked**. This is dated evidence, not a live
claim made when you run the demo. `live-report.json` records the original
comparison; the demo recomputes its verdict from the observations.

To make the same public read now:

```sh
python3 -B line-4/tools/transfer-anchor-audit/audit.py --capture line-4/tools/transfer-crosscheck/publicnode.json --live
```

Use `--rpc https://eth.drpc.org` to select the second public provider.
To inspect your own capture, use a saved schema 2 or 3 capture from the
sibling `erc20-transfer-window` tool. The audit validates all raw logs and
decoded summaries, including transaction positions, before any network I/O.
The inherited transport uses a dedicated User-Agent, disables proxy discovery
and redirects, allows only public read RPC methods, and bounds each response
to 16 MiB with a 25-second timeout. No environment variables are inspected.

The plan includes both boundaries and every block containing observed
transfers, deduplicated and sorted by height. At most **64 distinct blocks**
are allowed: one chain-ID request plus at most 64 numbered-block reads.
Larger plans fail before I/O; nothing is sampled silently. The only live
methods used here are `eth_chainId` and `eth_getBlockByNumber` with
transactions disabled. There are no automatic retries.

Each row is `matching`, `changed`, or `unavailable` (RPC returned null).
Malformed replies and network failures abort without emitting a success or
partial report. Overall status is `changed` if any hash differs, otherwise
`unavailable` if any block is unavailable, otherwise `matching`. All three
counts remain visible even when changed and unavailable rows coexist.
Exit codes: **0** all match, **1** changed/unavailable observation, **2** invalid
input or failed RPC. None of these statuses establishes a chain reorganization.

Replay other saved observations with:

```sh
python3 -B line-4/tools/transfer-anchor-audit/audit.py --capture line-4/tools/transfer-crosscheck/publicnode.json --evidence line-4/tools/transfer-anchor-audit/observations.json
```

A live report embeds the replay object under `evidence`; save that object
alone when preparing an `--evidence` file. It contains provider URL, timestamp,
chain ID, and ordered requested numbers with returned number/hash pairs (or
null). Full header fields are not retained or cryptographically verified.
Replay requires exactly the planned block list and recalculates every verdict.
Both input files must be regular files inside this workspace; the inherited
bounded reader rejects symlinks, traversal, duplicate JSON keys and excessive
size/nesting. To move this tool, copy the `line-4/tools` tree, preserving its
sibling imports; no dependency download is required.

Checks performed: **18 new tests passed**, along with **15 transaction-group
tests**. The new tests exercise actual demo/replay CLIs, real retained evidence,
changed and unavailable hashes, interior event blocks, empty and single-block
windows, exact types, malformed replies, wrong chain, request limits, no retry,
and rejection before network I/O. Synthetic mutations are test cases only.

```sh
python3 -B -m unittest discover -s line-4/tools/transfer-anchor-audit -p 'test_*.py' -v
```

Matching a provider's hashes is not consensus verification, event inclusion,
complete history, balances, price, pool activity or finality. Reads are
sequential, not an atomic snapshot; a provider may change during the audit.
Blocks with no saved hash are not checked. A replay file can be forged and
does not authenticate its provider or timestamp. No transaction is created,
signed or submitted.
