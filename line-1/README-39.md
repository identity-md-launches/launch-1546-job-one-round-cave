# The Rooted Seed — Line 1, mark 39

This round adds `tools/account-proof-check`, a Python standard-library tool that
checks a saved ZTO contract account proof against the state root in a saved
Ethereum block header. The header hashes, trie path and account fields are
checked offline; exact snapshot bytes are bound into the proof bundle. The
retained evidence came from PublicNode at block **26182473** on 2026-10-13.

From the repository root, this one command verifies the real ten-node proof
without a network connection or installation:

```sh
python3 -B line-1/tools/account-proof-check/account_proof_check.py demo
```

It reports `verified: true`. This means inclusion relative to the supplied,
self-consistent header. It does not establish a trusted chain anchor or prove
finality, ZTO supply, storage values or bytecode. Full scope, input bounds,
capture instructions, observed values and test results are in the tool README.

Gathering 18's reported failure was repaired first: direct-capture's redirect
test uses urllib's real error dispatch instead of directly calling a method
absent in Python 3.10. Runtime behavior is unchanged. Its 14 tests pass under
Python 3.11 and 3.14; Python 3.10 was unavailable for a native rerun. The broader
scoped dependency run passed 62 unit tests and the two transport demos, whose
25 and 68 checks overlap some unit coverage. `regression-39.json` records the
commands and the inherited fixture-cleanup ResourceWarnings.

The mark is a red ochre seed on a branching charcoal root. The installed built-in
image tool generated the pigment; only a vacant 88×151 patch of inherited rock
received it. **1,655 pixels changed; zero outside the patch.** The prior wall's
SHA-256 was verified before editing. The goal and older records are unchanged.

- `artifacts/line-1/wall-v20.png`: required **1254×1254 8-bit RGB PNG**.
- `artifacts/line-1/wall.png`: byte-identical continuing wall.
- `dist/line-1/39.jpg`: **512×512 baseline JPEG**, 72,481 bytes.
- `dist/line-1/39.json`: one new record with the finished PNG's SHA-256 URL.

Both images were visually inspected. Pepe's heavy-lidded eyes, wide mouth,
and two five-digit hands remain. No hands, text, numerals, logo, watermark,
border, real person or prohibited symbol was added. The inherited rock looks
photographic, a documented unmet visual requirement retained to preserve the
cave; the small new root loses detail in the thumbnail. Exact prompt and review
are in `IMAGE-PROMPT-39.md` and `wall-review-39.json`.

The output contract can be checked locally with:

```sh
python3 -B line-1/check-deliverable-39.py
```

The named PNGs remain untracked for the uploader. No dependency was installed,
and no secret, wallet, signing, transaction submission, payment, deployment or
external publication was used. Local checks do not independently certify
behavior or artistic quality.
