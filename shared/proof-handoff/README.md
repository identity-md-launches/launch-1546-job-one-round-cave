# ZTO account proof handoff

Give another worker one reproducible archive containing a pinned Ethereum ZTO
snapshot, its EIP-1186 account inclusion proof, and a report that the recipient
recomputes. This joins Line 1's account verifier to Line 2's HANDOFF v1 writer
and bounded ZIP inspector. Python 3.8+ and its standard library suffice; all
runtime dependencies are ordinary files in this folder.

From the repository root, run:

```sh
python3 -B shared/proof-handoff/proof_handoff.py demo
```

The demo checks dated **real ZTO evidence**, builds the archive twice in memory,
checks reproducibility, and verifies the proof again without a network, writes,
extraction, or execution of payloads. To move it, copy this whole folder and run
`python3 -B proof_handoff.py demo` from the recipient workspace.

## What happened when tried

At **2026-10-13T09:41:20Z**, read-only capture through the assigned Ethereum relay
observed numbered block **26182632**, hash
`0xb3720ccec3dcf333f18e16d3535bf245c355d7c0399e455842e5d91855730d80`.
The public source alias is <https://ethereum-rpc.publicnode.com>; this alias is
assigned by the task and does not authenticate the actual upstream provider.
The block had first been selected using the finalized tag; the delivered capture
re-read that explicit number. This is not independent finality verification.

The ten-node account proof verifies ZTO contract nonce **1**, native ETH balance
**0 wei**, storage root and code hash relative to state root
`0x8ff5dea341d745acc370f85dead12d71d1b7f5848fdfdeeb6fbd3efc0030f6d2`.
All three saved Prague headers recompute to the same block hash. Zero is an
observed and proved native balance, not a placeholder address or transaction.
The reported supply is 1000000000000000000000000000 base units, but account
inclusion **does not prove totalSupply or any token balance**.

The included `examples/zto-proof.zip` is **88,860 bytes** and passed the native
Line 2 review's integrity, filename portability and byte reproduction checks.
Its original snapshot is 52,008 bytes and proof 34,506 bytes. Their original
bytes travel unchanged, including whitespace. The receiver refuses a validly
rehashed ZIP with a false proof report. Thirteen integration tests passed:

```sh
python3 -B -m unittest discover -s shared/proof-handoff -p 'test_*.py' -v
```

Tests cover the real proof offline, exact bytes, deterministic packing, trusted
digests, changed account claims/nodes, source-byte binding, false reports,
missing/extra payloads, strict JSON, limits, corruption, noncanonical ZIPs,
symlinks, exclusive creation, portability of the complete folder and dependency
provenance. An initial test-fixture path bug on Python 3.12 was repaired; the
runtime needed no change. A test deliberately changes an unproved supply
observation and confirms it remains explicitly unproved.

## Use your own complete evidence

```sh
python3 -B shared/proof-handoff/proof_handoff.py pack snapshot.json proof.json proof.zip
python3 -B shared/proof-handoff/proof_handoff.py check proof.zip
```

`pack` requires three explicit workspace-relative paths. It creates only the
named new archive and refuses an existing output. Inputs and output parents
are traversed using POSIX directory descriptors and no-follow opens. Symlinks,
`..`, absolute paths, nonregular inputs and oversized files are refused.
`check --sha256 HASH` can require an independently retained archive digest.
A digest copied from the same candidate is not sender authentication.

The fixed payload contract is `evidence/snapshot.json`,
`evidence/account-proof.json`, and `review/account.json`, plus HANDOFF.json.
The inspector first bounds and verifies the ZIP, then the proof verifier
rechecks original snapshot bytes, header hashes, account-trie path and claims.
The report must equal the recomputed canonical report, and rebuilding those
three files with the inherited writer must reproduce the entire archive.
Nothing from the archive is extracted, imported or executed.

Each input, output JSON and complete archive is limited to **99,000 bytes**.
This deliberately small exchange format can refuse valid large captures;
select a complete smaller-block capture. Never drop fields, truncate evidence
or silently reserialize a snapshot that its proof digest binds. The original
line verifier supports larger inputs, but this submission's file-size contract
does not. Invalid input exits 1 without a JSON receipt; valid checks exit 0.
Argument syntax errors use argparse's exit 2. POSIX no-follow support is needed
for file commands; the in-memory demo uses trusted local example files.

## Limits and reuse

The verifier proves inclusion **relative to the supplied state root**. It does
not establish that the root is authentic mainnet consensus, finality, current
state, storage-slot contents, the bytecode preimage, or an eth_call result.
The native account balance is ETH, not ZTO. It supports the real ZTO account,
not arbitrary senders; this is not transaction nonce context for Line 3.
No keys, wallets, environment discovery, signatures, submission, payment or
posting are involved. ZTO is the default token; no new coin is needed.

`PROVENANCE.json` records all eight line modules and their source/copy hashes.
Six are unchanged. The account verifier additionally accepts immutable snapshot
bytes, using the same native checks, so the receiver need not extract files.
The snapshot reader's workspace root uses the invocation cwd for standalone
portability; the glue uses the bytes path. `workspace_io.py` reuses Gathering
18's reviewed no-follow file helpers, with its own provenance entry. No package
installation, submodule or network fetch is needed to run the delivered kit.
