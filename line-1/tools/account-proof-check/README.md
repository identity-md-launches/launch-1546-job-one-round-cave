# Account proof check

Verify that the real ZTO contract account is included in the Ethereum state
root recorded by a saved `pinned-zto-snapshot/1` observation. The verifier
recomputes both saved execution headers, traverses an EIP-1186 account proof
using Ethereum Keccak-256, and compares the proved nonce, native ETH balance,
storage root and code hash with all four RPC claims. This gives a worker a
portable account proof that can be checked without access to an RPC service.
Python standard library only; no installation is needed.

From the repository root, one command demonstrates the retained real proof:

```sh
python3 -B line-1/tools/account-proof-check/account_proof_check.py demo
```

The demo uses only `live-zto.json` and `live-proof.json`. It creates no socket
and writes its report to stdout. The report identifies the exact snapshot
SHA-256, block, state root, proved account fields, reported capture provenance
and assurance limits. Exit 0 means the proof verifies relative to that root;
exit 1 means invalid evidence or a capture failure, with no partial JSON output.

## What happened when tried

A fresh finalized-tag snapshot was obtained from
`https://ethereum-rpc.publicnode.com` at **2026-10-13T09:02:41Z** using the
existing pinned-snapshot tool. This tool then requested the ZTO account proof
at its explicit block number and fetched that same numbered block again at
**2026-10-13T09:05:31Z**. The retained evidence is:

| Item | Verified value |
| --- | --- |
| Block number | 26182473 |
| Block hash | `0x9df535d2c4325171af456d416f0f7ca969209b5c10076b4a412fd2c7e2051f5a` |
| State root | `0xc48ced6b7ec310acd70ea93fd7081f1f3dbd6aa06d09a2c52d81de8ef9d51492` |
| ZTO contract nonce | 1 |
| Contract's native ETH balance | 0 wei |
| Account proof | 10 nodes |
| Storage root | `0x5ae77dcf88467fd92c60208c7db4ec3dbecf7dc0250e67efd1718bbaa26d28df` |
| Code hash | `0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d` |

The source snapshot is 61,606 bytes, the proof bundle is 39,305 bytes, and both
are ordinary retained JSON files. Both original headers and the post-proof
header recomputed to the same hash. The snapshot's reported ZTO totalSupply is
1000000000000000000000000000 base units; **this account proof does not prove
that value**. The observed zero native balance is an actual RPC value checked
against the account leaf, not an address, key or deployment placeholder.

Thirty-six tests passed, including the real demo with socket creation disabled,
mutation of each real proof node, missing/reordered/unused nodes, every account
claim, source digest and header binding, canonical RLP, compact paths,
the exact 31/32-byte embedded/hash boundary, byte/depth/item limits, workspace
file/symlink/FIFO guards, duplicate JSON keys, fixed RPC requests, redirect
refusal, an explicit empty proxy handler and bounded response handling:

```sh
python3 -B -m unittest discover -s line-1/tools/account-proof-check -p 'test_*.py' -v
```

## Check or collect evidence

To check another saved pair offline:

```sh
python3 -B line-1/tools/account-proof-check/account_proof_check.py check line-1/tools/account-proof-check/live-zto.json line-1/tools/account-proof-check/live-proof.json
```

For a fresh proof, first obtain a recent valid pinned snapshot with the existing
`pinned-snapshot` tool. Then run this command with that snapshot's workspace path:

```sh
python3 -B line-1/tools/account-proof-check/account_proof_check.py capture line-1/tools/account-proof-check/live-zto.json --rpc https://ethereum-rpc.publicnode.com
```

That last command makes public reads and prints a new proof bundle; it does not
replace the retained example. An older example can require archive-state proof
support that a public provider may no longer offer. The offline demo still
works. Capture accepts only three fixed requests: `eth_chainId`,
`eth_getProof` for ZTO with an empty storage-slot array at an explicit numeric
block, and `eth_getBlockByNumber` for that number with transaction details off.
The captured header must recompute and match the saved number/hash/state root.
No arbitrary RPC method, block tag, token or storage slot is accepted by this
transport. It uses its own User-Agent, a 20-second timeout, explicit empty proxy
configuration, no redirects, identity content encoding and a 4 MiB response cap.
Requests never sign, send transactions, access wallets or read secrets.

Inputs must be regular files within this workspace, at most 4 MiB, with no
symlink components. Inherited strict JSON parsing refuses duplicate keys and
nonfinite numbers. A proof has 1–65 nodes, at most 4,096 bytes per node and
32,768 decoded proof bytes in total. RLP decoding also bounds nesting and item
count and rejects nonminimal lengths, truncation and trailing bytes. Traversal
checks compact-path flags/padding, exact secure-key consumption, selected-child
hashes and the embedded-versus-hashed size boundary. It rejects unused nodes,
absence proofs, and any nonempty `storageProof`. It checks canonical RLP and
the inclusion path; it does not reconstruct the whole trie or certify the
normalization of unrelated trie branches.

## What verification means

The proved account belongs to
`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e` **relative to the supplied state
root**. Header reconstruction supports the inherited **21-field Prague layout**.
Older headers or later header layouts need separate support. A provider can
fabricate a self-consistent root, proof, block header and hash together. Neither
chain ID nor a requested `finalized` tag establishes a trusted mainnet anchor,
consensus validity or finality. Capture endpoints and timestamps are reported
metadata, not authenticated provenance. A reorg away and back between reads
is not excluded.

The four account fields do not establish ZTO's storage-slot layout, supply,
holder balances, pool liquidity, code bytes or the result of `eth_call`.
In particular the native ETH balance of the contract is not a ZTO token balance.
The tool deliberately requests no storage slots instead of guessing a slot for
totalSupply. A test changes only the reported supply and shows that account
verification still passes, with the changed supply explicitly labelled as
unproved provider evidence.

The implementation follows the account field order and RPC proof format in
[EIP-1186](https://eips.ethereum.org/EIPS/eip-1186) and the node/path/reference
rules described in Ethereum's
[Merkle Patricia Trie documentation](https://ethereum.org/en/developers/docs/data-structures-and-encoding/patricia-merkle-trie/).
It reuses `header-hash-check` (including its vendored Keccak source),
`snapshot-seal` workspace-safe reads, and `pinned-snapshot`/`rpc-snapshot`
validation. Keep those sibling folders when copying it; no downloaded package
or uncommitted dependency is needed.
