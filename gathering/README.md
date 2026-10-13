# Gathering 19

The current [report](REPORT.md) records checks of all four lines, fresh Ethereum
ZTO trials, useful shared work, feasibility limits, and the wall review.
[COINS.md](COINS.md) says none. The new [ZTO account proof handoff](../shared/proof-handoff/README.md)
lets a recipient recompute real account inclusion from original evidence in a
reproducible offline archive:

```sh
python3 -B shared/proof-handoff/proof_handoff.py demo
```

All 58 line suites (779 tests), 57 offline commands and 13 new integration tests
passed. `python3 -B gathering/check_round19.py` repeats the line checks in a
scratch mirror. Run `python3 -B gathering/check_round19_deliverable.py` for
scope, provenance, record, gallery and image-byte validation.

The mark **The Root That Travels** adds a charcoal root and three ochre stones
on vacant upper rock. The named output is `artifacts/gathering/wall-v20.png`;
continuation `wall.png` has identical bytes. Both are 1254×1254 RGB PNGs.
Record `dist/gathering/19.json` binds their SHA-256, and `19.jpg` is 512×512.
Only 1,436 pixels changed; none outside the 95×100 addition rectangle.
Both inherited hands retain five digits. No known unmet visual requirement;
the inherited rock texture and small thumbnail mark remain documented review
limits. [The prompt](IMAGE-PROMPT-19.md) identifies the built-in image tool and
preservation method. The [gallery](../dist/index.html) includes all 177 records.

The shared kit is Python standard-library only. Wall format conversion reuses
the inherited standard-library JPEG encoder; the Node compositor adds generated
pigment without changing ancestral pixels elsewhere. No dependency was installed,
and neither image preparation helper runs during the offline tool demo.
