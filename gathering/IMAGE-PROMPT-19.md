# The Root That Travels

Built-in `image_gen.imagegen`, transparent background enabled. Final prompt:

> Use case: illustration-story. One isolated small primitive prehistoric cave-paint pigment mark on a genuinely transparent background: a crooked branching root drawn with charcoal, with exactly three small irregular red-ochre pebbles attached to the tips. The stem at the top branches down toward the three pebbles at bottom left, bottom center, bottom right. Very simple handmade burnt-stick lines and thumb-dab ochre, rough uneven dry pigment with worn gaps. Charcoal black and red earth ochre only. Flat pigment artwork, no paper or rock background, no lighting, no shadow, no glow. This is an insert for an existing torchlit cave wall. No letters, numerals, captions, symbols, logos, watermark, border, frame, hands, people or characters. Generous transparent margin around the complete small motif.

The tool returned a 1536×1024 transparent PNG. Its opaque motif extent was
(417,113)–(1118,911). `finish_wall19.cjs` rejects alpha at or below 180 to discard
a faint tool-generated glow, area-averages the remaining pigment to 95×100,
and maps it to charcoal/red ochre over the original stone at (650,50). Original
stone shows through at up to 80% pigment opacity. The source wall is SHA-256
checked against record 18 before composition. Both generated inserts and
intermediate candidates were overwritten by the complete final wall; no extra
workspace image remains. No photograph or procedural drawing replaces the
installed image tool's generated pigment.

An initial whole-wall additive edit was visually plausible but softened some
inherited texture. Its candidate was discarded in favor of the isolated
pigment workflow. The final output preserves every pixel outside the vacant
rectangle, including both five-digit hands and every ancestor.

Final files: `artifacts/gathering/wall-v20.png`, continuation `wall.png`, and
`dist/gathering/19.jpg`. Dimensions, formats, final hashes, exact changed-pixel
count and manual visual review are in `checks/round-19/image-preservation.json`.
No known unmet visual requirement. The source rock's photographic appearance
is inherited; the new art consists only of earth pigment. Small mark visibility
at 512px and the limits of local visual review are recorded explicitly.
