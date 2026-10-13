# The Revisited Stones

Built-in imagegen tool; supporting pigment insert for an inherited wall.

Exact prompt:

> Use case: illustration-story. Supporting pigment insert for an inherited prehistoric cave painting. Draw exactly two small irregular ochre stones side by side joined by a single loose charcoal loop, like two observations of the same stone checked again. Red ochre on the left, yellow ochre on the right, burnt charcoal black thin looping cord. Hand-made uneven thumb-dabs and burnt-stick strokes, worn pigment gaps, simple flat Lascaux marks. Isolated central motif on pure white with ample white margin. No hands, frogs, people, text, letters, numerals, logos, signatures, watermark, frame or border. No realism, shadows or 3D. Final composition will preserve an existing cave wall and its Pepe painting by adding this small pigment insert only to empty rock. If saving, use only artifacts/line-4/wall-v20.png inside the workspace; it will be overwritten by the finished full wall.

The returned data-URL bytes were written directly to the declared output
path; no generated file outside the workspace was read. `finalize-39.js`
is adapted from the read ancestor compositor and verifies record 38's
SHA-256 before applying the new pigment. It uses the generated crop
(300,280,950,470) and vacant-rock rectangle (64,493,132,68). White is removed
in memory and pigment is blended with the existing rock. Every pixel outside
the rectangle is compared before saving and remains identical.

The generated insert was overwritten by the full final wall. Only the two
required full-wall PNG aliases and the specified JPEG are new image files.
The reviewed `gathering/make_thumbnail.py` helper performs format conversion.
The compositor is a process record, not the delivered worker tool; replaying
it requires the original ancestor and the original generated insert.
