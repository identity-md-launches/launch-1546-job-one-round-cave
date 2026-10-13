# Nonce context for unsigned Ethereum proposals

`nonce_context.py` adds an offline account-sequence explanation to the inherited
unsigned EIP-1559 decoder. Give it the chain ID and the latest and pending next
nonce counts you have independently obtained for the intended sender. It explains
whether the proposal is below the latest count, inside the pending window, at its
frontier, or above it, and reports exact signed distances and the gap size.
All arithmetic is integer arithmetic; JSON integers are decimal strings.

From the repository root, this one command shows it working:

```sh
python3 -B line-3/tools/nonce-context/nonce_context.py --demo --chain-id 1 --latest-nonce 0 --pending-nonce 0
```

When tried, it reported `at-pending-frontier`, zero gap, the real Ethereum ZTO
contract `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`, and selector
`0x18160ddd` (`totalSupply()`). The inherited demo is a **synthetic unsigned
inspection sample**, not a fetched transaction or live account observation.
The counts in that command are explicit example assertions. Nothing was sent.

For a real proposal, replace the three context arguments with your asserted
values and replace `--demo` with `--transaction HEX`, where HEX is the complete
unsigned type-2 RLP envelope. Alternatively use `--stdin` to read the hex from
standard input. No input file is opened. The CLI emits one JSON report and exits
0 for every valid diagnostic, including a stale nonce or gap. Invalid inputs
exit 2 with an error on stderr and no partial report. A diagnostic is not an
approval decision.

For example, asserted latest 5 and pending 8 put proposal nonces 5, 6 and 7
inside the pending window; 8 is the frontier; 12 leaves four nonce positions
between that frontier and the proposal. This is an interpretation of the counts,
not evidence of four actual transactions. The context must satisfy pending >=
latest and must match the decoded chain ID. Counts and proposal nonce must fit
uint256; this is an arithmetic bound, not a claim of protocol-valid nonce range.
Decimal context text must be canonical, unsigned and unpadded.

An unsigned envelope cannot identify its sender. The caller must associate the
counts with the intended account and chain. Counts may be stale, inaccurate or
provider-local; competing proposals, nonce availability and replacement policy
are not discovered. The report proves no contract behavior, execution, gas
sufficiency, inclusion, finality or safety to sign. The fingerprint is SHA-256 of
unsigned bytes, not an Ethereum transaction hash. There is no RPC, wallet, key,
environment-variable access, signing, transaction submission, payment or post.

Python standard library only, no installation or network needed. Keep this
folder and `../zto-eip1559-decoder/` together. Imports resolve relative to this
script, so commands also work when launched from another current directory.

Checks run locally:

```sh
python3 -B line-3/tools/nonce-context/test_nonce_context.py
python3 -B line-3/tools/zto-eip1559-decoder/test_decoder.py
```

All **14 new tests and 12 inherited decoder tests passed**. Coverage includes
all window boundaries, empty windows, exact large distances, mismatched chains,
inconsistent and malformed context, malformed and signed envelopes, hex
spelling, clean CLI failures, and bounded stdin before whitespace stripping.

The accompanying mark, **Pepe's Next Step**, means: “Pepe follows a pebble trail
and notices the gap before the next step.” A new ochre trail on vacant floor
stone represents nonce sequencing. The finished wall remains 1254×1254 PNG;
the 512×512 JPEG and visual limitations are documented in
`line-3/IMAGE-PROMPT-39.md` and `line-3/round-39-review.json`.
