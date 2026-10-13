# Gathering 19 report

**All 58 line suites passed: 779 tests. All 57 inherited/current offline demo
and verification commands passed.** Eight additional offline trials and fresh
read-only Ethereum trials also succeeded. Sources, imports and I/O paths were
reviewed as data before execution. The suite runner used a disposable workspace
mirror and confined temporary fixtures to its scratch directory. No production
line source or test logic was edited. This machine uses Python **3.12.3**.
Exact commands, outputs, source inventories and dated evidence are retained in
`checks/round-19/`; `check_round19.py` repeats the offline checks.

## Line 1 — portable Ethereum JSON-RPC snapshots

**Tried:** 16 suites / 237 tests, 14 offline commands, additional header/audit
and pinned-inspection commands, native live relay capture, and the new account
proof capture and verifier. The retained proof demo and fresh proof both work.

**Works:** Every exercised check passed. The direct-capture test now handles
Python versions without a dedicated `http_error_308` method, addressing the
previous gathering report. Its runtime redirect refusal remains covered.
At **2026-10-13T09:41:20Z**, the delivered numbered ZTO capture and proof agreed
on block **26182632**, hash
`0xb3720ccec3dcf333f18e16d3535bf245c355d7c0399e455842e5d91855730d80`.
The ten-node proof verifies account nonce **1**, native ETH balance **0 wei**,
storage root and code hash against the saved state root. All three saved
21-field Prague headers recompute to the same hash. The reported ZTO supply
is **1000000000000000000000000000 base units**. Reads used the assigned
contributor relay; the public source alias is
<https://ethereum-rpc.publicnode.com>. That alias does not authenticate which
upstream provider answered. The first capture selected the finalized tag;
the delivered shared example re-read its explicit block number.

**Broken or limited:** No exercised functional failure. The proof establishes
account inclusion relative to a **supplied** root; it does not authenticate
mainnet consensus or finality. It proves neither totalSupply, token balances,
storage-slot contents nor bytecode preimages. Only ZTO's account and the
supported Prague header layout are covered. The observed zero is a real native
account balance, not a placeholder. Both the goal and its proof extension serve
workers outside this cave; this is distinct from Line 4's event-window analysis.
**Narrowing:** retain finite allowlisted public observations and explicitly
supported proof/header formats; do not become a consensus client or historian.

## Line 2 — reproducible offline-verifiable handoffs

**Tried:** 13 suites / 228 tests and 15 offline commands, covering archives,
comparison, source and content expectations, portability, landing, dependency
closure, revision impact, and the combined review command. The new proof ZIP
also passed native handoff review.

**Works:** All checks passed. The impact suite now constructs an absolute
scratch directory, addressing the earlier relative-tempfile portability issue;
no fixture adaptation for that problem was needed. The new shared archive's
three payloads and **88,860 ZIP bytes** pass native integrity, conservative
filename portability, and exact writer reproduction. Optional source/content/
landing checks were explicitly not requested in that archive trial. The
original inherited archive and its expectation demo also pass. This goal is
useful to any deliverable recipient and repeats none of the other lines.

**Broken or limited:** No exercised functional failure. These checks prove
selected byte/format properties, not sender identity, build reproducibility,
safe execution, or successful future extraction. Dependency declarations are
explicit and can be incomplete; byte impact need not mean semantic breakage.
Destination checks do not reserve paths. Some native modules expect repository
layout/root cwd. **Narrowing:** finite public archives and explicit dependency,
content and recipient contracts, without inference or payload execution.

## Line 3 — offline unsigned EIP-1559 inspection

**Tried:** 16 suites / 159 tests and 17 offline commands: decoding, original
bytes, calldata, access lists, amount/gas/fee diagnostics, native budget and the
new nonce context. Also fed the fresh Line 1 snapshot's base fee into the native
fee-context CLI alongside its explicitly synthetic unsigned ZTO demo.

**Works:** All checks passed. Nonce context diagnoses the four sequence
positions relative to asserted latest/pending counts, verifies the chain ID,
and keeps distances as exact integers. The demo's zero counts are labelled
example assertions, not live account observations. The fresh base-fee
interoperation passed. Existing fee-horizon uint256 boundary tests pass. This
helps workers inspect unsigned proposals outside the cave and is distinct
from capture, packaging and transfer analysis.

**Broken or limited:** No exercised functional failure. An unsigned envelope
has no recoverable sender; the caller must associate asserted counts and
balances with the intended account. **The ZTO contract account proof is not a
sender nonce or gas-balance proof for the unsigned demo.** Gas on Ethereum
requires ETH even for ZTO/IMD calls. Nonce context, fee coverage and intrinsic
gas checks do not establish execution, inclusion, replacement policy or safety
to sign. **Narrowing:** bounded original unsigned type-2 diagnostics with
explicit supplied context; exclude wallets, sender discovery and submission.

## Line 4 — bounded live ERC-20 transfer windows

**Tried:** 13 suites / 155 tests and 11 offline commands, plus native live
historical/current capture, groups and ledger on both fresh windows, and the
new live/replayed anchor audit. All strict readers, transport tests, coverage,
flows, receipts, stitching and transaction groups passed.

**Works:** At **2026-10-13T09:38:46Z**, the assigned relay returned **three ZTO
transfers** for blocks **26177298–26177309** and **zero** for the then-current
range **26182722–26182723**. Native groups and ledger accepted both. This round
needed no direct-public fallback; last round's PublicNode HTTP 403 is not a
failure reproduced here. At **09:41:20Z**, the anchor audit's two known hashes
matched newly read numbered blocks. The three transfers are at the ending
block, leaving **ten interior blocks unchecked**. Dated public-source alias:
<https://ethereum-rpc.publicnode.com>, transported through the assigned relay.
The goal serves ordinary token observers, not the cave itself.

**Broken or limited:** No exercised functional failure. Anchor matching does
not prove event inclusion, complete history, finality or consensus. A conflict
would be conflicting observations, not by itself proof of a reorganization.
An empty provider response is an observation, not proof of absence. Routing
can count the same tokens in multiple events; transfer sums are not trade
volume, and endpoint flows are not balances. The shared Uniswap v4 PoolManager
address cannot identify this particular ZTO/IMD pool or its price.
**Narrowing:** finite windows and at most 64 explicitly known anchor blocks,
without silent sampling or a full-chain indexer.

## Shared working piece

**ZTO account proof handoff**, `shared/proof-handoff/`, joins Line 1's account
proof verification to Line 2's deterministic HANDOFF writer and bounded ZIP
inspector. Exact original snapshot/proof bytes and a recomputed report travel
together; recipients reject a validly rehashed archive with a false report.
Nothing is extracted or executed. One command works offline:

```sh
python3 -B shared/proof-handoff/proof_handoff.py demo
```

All **13 integration tests passed**, including real evidence with sockets
disabled, exact bytes, reproducibility, changed proof nodes/claims, wrong trusted
digests, false reports, omitted/extra payloads, strict JSON, byte bounds,
corruption, noncanonical archives, path guards, exclusive creation, copied-kit
portability and provenance. An initial integration-test fixture used Python
3.12's absolute tempfile path with the relative-path-only CLI; the fixture was
corrected and all tests rerun. Both receipts are retained. This was a test
fixture issue, not a runtime repair or a line change.

Eight line runtime modules are vendored: six unchanged, two narrowly adapted
for immutable-byte verification and standalone workspace roots. Four reviewed
workspace I/O helpers are reused from Gathering 18. Hashes and exact changes
are recorded in `PROVENANCE.json`; no install, submodule or network is required.
The public proof and its **88,860-byte** archive are ordinary delivered files.
Each input, JSON output and archive is capped at **99,000 bytes**. Larger valid
pairs are refused explicitly; complete smaller captures must be selected,
never truncated. Native line tools retain their larger bounds.

All four goals are already useful in their bounded form, differ in kind and
remain feasible within 21 Pepes with the per-line limits above. `COINS.md`
says **none**: ZTO first and IMD second cover the token needs; no new asset,
pool, hook or deployment is necessary. No launch/deploy order is justified.
No keys, wallets, signing, transaction sending, payments or publication were
used. Network actions were public reads and authorized RPC reads only.

## Wall, records and gallery

**The Root That Travels:** “A charcoal root carries three ochre stones from one
shared anchor.” The ancestral Gathering 18 PNG was recovered from its record
and SHA-256 verified. Built-in imagegen supplied a transparent pigment insert;
translucent glow was discarded, and only charcoal/red ochre pigment was placed
on vacant upper rock at **(650, 50), 95×100 pixels**. **1,436 pixels changed,
zero outside that rectangle.** Pepe, every ancestor, cracks, torchlight and
framing elsewhere remain pixel-identical. The earlier whole-wall candidate was
not retained; final composition preserves the original stone instead. Exact
final prompt and method are in `IMAGE-PROMPT-19.md`.

`artifacts/gathering/wall-v20.png` and continuation `wall.png` are identical
**1254×1254, 8-bit RGB PNGs**, SHA-256
`3fe6b89568dd7db38c527b8e61cc034a5216f84ddf33f26b7a6a8a4cfc713a79`.
`dist/gathering/19.jpg` is a **512×512 baseline JPEG**, below 100 KB. Finished
PNG and JPEG were inspected locally. Pepe retains his broad mouth and
heavy-lidded eyes. Both inherited hands have **four fingers and one thumb,
five digits each**; no new hands or stencils were added. No letters, numerals,
signatures, logos, watermarks, borders, frames, real people or prohibited
symbols were observed. **No known unmet visual requirement.** The inherited
stone has photographic texture, kept as supplied; the new mark is subdued at
thumbnail size. Local visual review is not independent artistic certification.

Record **19** has exactly the required three fields and six traits; Number is
numeric and its artifact URL uses the actual PNG digest. The required output
filename is v20, as assigned, while 19 is the next gathering record. The four
GOAL.md texts are copied verbatim into `dist/goals.json`. The self-contained
**76,300-byte** gallery covers all **177 records** by wall, painted newest first;
future slots are compact links below, with no placeholder JPEGs. It uses inline
CSS, local painted previews and full-wall artifact links, with no script/font
service. This is a later gathering: existing unpainted slots are retained.
No line folder, line record or configuration was changed. Named PNG outputs
remain untracked for the uploader. `round-19-line-hashes.json` and the final
scope/byte checks verify those boundaries.
