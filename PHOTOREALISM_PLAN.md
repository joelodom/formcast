# Formcast Photorealism Plan

> **Read `MASTER_PLAN.md` first.** This document is now the detailed specification
> for **Phases 0–1** of that master plan (headless rendering/eval foundations and
> the tree-photorealism pass). It remains authoritative for those phases. One
> correction found by later experiment: the Appendix A renderer must apply
> scene-graph node transforms — iterate `scene.dump()` instead of
> `scene.geometry.items()` (see the note in Appendix A and MASTER_PLAN §5.4).
>
> **Standing constraints** (commit discipline, session pacing, model choice, doc
> upkeep) live in **`CLAUDE.md`** — the single source of truth. This plan does not
> restate them; refer there. No fixed dollar/time budget applies.
> A transform-aware reference copy lives at
> `outputs/experiments/2026-06-09/fc_render.py`.

**Goal:** make `bake` output dramatically more photorealistic, starting with (but not
hardcoded to) the maple example, and raise the quality *floor* so every run lands a
good model. (This is about reliability, not bit-exact repeatability — some run-to-run
variation from seeds/temperature is fine, even useful: formcast bakes a seed-varied
library to choose from, and Joel may want to pick the best of a few samples. Two
same-parameter runs should land in *about* the same place, but that's a soft aim, not
a hard rule.) This document is an implementation plan for Claude (Opus) working in this
repo. It is grounded in measurements taken on 2026-06-09 against two real bakes of
`inputs/maple-tree.png`; every claim below was verified empirically in this repo,
including the trimesh export mechanisms (Appendix C) and the software renderer
(Appendix A), which is known-working code you can paste.

**How to use this plan:** work the phases in order (P0 → P3). P0 builds the eyes
(headless rendering + audit metrics) — do not skip it, because nothing else can be
verified without it. Each later phase has acceptance criteria measured by the P0
tooling. After each phase, run the verification protocol in §11 and *look at the
renders yourself* (the Read tool views PNGs).

**Standing constraints (from CLAUDE.md — do not violate):**

- Keep formcast **generic 2D → 3D**. No maple/tree-specific constants in
  `formcast.py`. Species/class-specific craft lives in *prompt guidance conditioned
  on Pass 1's `class`* (trees/shrubs get foliage-card guidance, rocks get rock
  guidance) and in the *generated* scripts. The maple photo is the benchmark, not
  the domain.
- Update `README.md` in the same change as any flag/behavior change.
- Do not commit or push until the user says so. Work on `main`.
- Generated scripts may only use `numpy`, `trimesh`, `PIL`, stdlib. Do not add
  runtime deps to formcast itself (the renderer below is pure numpy+PIL on purpose;
  scipy exists in this env but must NOT become a requirement).
- Bump `PROMPT_VERSION` (currently `formcast/1.1-cli`) when you change the pass
  prompts. Keep the header docstring of `formcast.py` in sync with the new pipeline.
- The user's existing bakes in `outputs/*.glb` are the baseline — **do not
  overwrite them**. Bake experiments into `outputs/dev/<short-tag>/`.

---

## 1. Baseline evidence (measured, reproducible)

Two end-to-end bakes of the same image, default settings (`--model opus`):

| Metric | Run A (user, 11:24) | Run B (selftest, 14:00) | Reference photo |
|---|---|---|---|
| Wall time | 458 s | 402 s | — |
| Repairs needed | 1 (pass 3, SyntaxError) | 1 (pass 2, `ndarray.ptp` removed in numpy 2) | — |
| Total triangles (high) | 12,676 | ~73,000 | — |
| Canopy cards | 620 (2 tris each) | 520 (8 tris each) | — |
| Texture resolution | 256² everywhere | 256² everywhere | — |
| Width/height aspect | 0.57 (too narrow) | similar | **0.84** |
| Crown-bbox fill (front render) | **47%** | worse (confetti) | **67%** |
| Leaf alpha: fully transparent / semi (16–240) / opaque | 21% / **48%** / 58% | similar approach | crisp edges |
| Foliage two-tone | weak | weak | sunlit ≈ (152,171,93), shade ≈ (35,50,5) — ~4:1 luminance |
| glTF up-axis | **Z-up (violates spec)** | Z-up | glTF requires +Y-up |
| Foliage material | MASK 0.5, doubleSided ✓ (correct!) | MASK 0.4 ✓ | — |
| Subjective render | sparse, scraggly, floating clumps | scattered confetti, see-through | dense billowing dome |

Key takeaways:

1. **The "leaves not transparent" complaint is NOT an alpha-export bug.** Both runs
   correctly wrote `alphaMode: MASK`, `alphaCutoff`, `doubleSided: true`, and a real
   RGBA PNG (verified in the binary GLB JSON chunk — Appendix B.3). Two real causes:
   (a) the leaf texture's alpha is 48% *semi*-transparent mush, so under MASK the
   cutout has noisy dissolve edges and cards still read as blobby squares; and
   (b) formcast's own `view` cannot render at all on this machine (below), so the
   models were inspected in tools that may ignore MASK.
2. **`view` is broken headless and the error is misdiagnosed.** `scene.save_image()`
   / `scene.show()` need a *display* (pyglet `get_default_screen → IndexError: list
   index out of range`); the error handler blames OpenGL and suggests `--save`,
   which also fails. pyrender is not installed. Until P0, neither the user, you,
   nor a future refine loop can see anything on this box.
3. **The exported tree lies on its side in spec-compliant viewers.** Generated
   geometry is authored Z-up and exported with no rotation node (verified: `nodes`
   have no `rotation`). three.js / `<model-viewer>` / Blender import assume +Y-up.
4. **Run-to-run variance is huge** (12.7k vs 73k tris; different surface naming —
   Run B merged branches into "trunk"; both runs needed one repair). The prompts
   under-constrain the result, so the quality floor is unreliable run to run (~7 min per attempt).
5. **The texture pipeline destroys its own detail.** Both runs derive a 256² swatch
   from the photo, then "make it tileable" by rolling and blurring a cross through
   the middle — measured local contrast in the blurred cross is 9.5 vs 16.9 outside
   it. The bark texture is half photo detail, half featureless brown smear; the
   leaf texture's center is an out-of-focus green smudge.
6. **What's already good:** Pass 1 descriptions are excellent (rich, accurate,
   "two-tone yellow-green / shadow teal", "cauliflower clumping"). The
   sample-the-photo idea is sound. The pipeline plumbing (gates, repair loop,
   session resume, metadata embedding) works. The geometry *code* the model writes
   is competent — it just isn't being asked for the right things.

Reproduce any of this with the commands and snippets in Appendix B.

---

## 2. Root causes, ranked by visual impact

| # | Root cause | Visible symptom |
|---|---|---|
| 1 | Open-loop pipeline: the model never sees what it built | All of the below survive to ship |
| 2 | Leaf texture = blurred photo swatch + noise-blob alpha, 256², single tile | Blobby dissolve-edged cards, no leaf silhouettes, repetition |
| 3 | Cards scattered i.i.d. around branch anchors, no crown envelope, no clumping | Wispy gappy crown (47% vs 67% fill), floating outliers, wrong aspect (0.57 vs 0.84) |
| 4 | No lighting variation baked in: one flat texture for the whole canopy | Flat "plastic hedge" look; photo has 4:1 sun/shade range |
| 5 | Roll+blur "tileable" step | Bark smear column; mushy leaf centers |
| 6 | Z-up export | Sideways trees in real engines |
| 7 | No normal/occlusion maps, 8-sided trunk, tube caps poke through canopy | CG-smooth bark, faceted silhouette |
| 8 | Crop boxes for photo swatches are hardcoded guesses, not measured | White-background bleed (specks), wrong material sampling on other photos |
| 9 | No budget/quality constraints in prompts | 6× tri variance, 256² textures chosen "by vibe" |
| 10 | Headless viewer broken + misleading error | Nobody can evaluate output where it's produced |

---

## 3. Architecture of the fix (overview)

```
P0  WS0  Headless software renderer + `view` fixes      ← the eyes
    WS1  glTF correctness: Y-up, real-world scale, audit  ← spec compliance
P1  WS2  PASS2 geometry prompt overhaul (envelope + clumps + budgets)
    WS3  PASS3 texturing prompt overhaul (leaf atlas + bark + COLOR_0 + normals)
    WS4  Pass 3.5: closed-loop visual refinement (render → critique → revise)
P2  WS5  Objective quality gates wired into the repair loop
    WS6  Variant differentiation + LOD sanity
P3  WS7  Experiments menu (photo-sourced leaf sprites, space colonization, …)
```

WS4 is the single highest-leverage change: formcast already drives a *vision-capable*
agent (the `claude` CLI reads `reference.png` via its Read tool today). Rendering the
baked model to PNGs in the same workdir and asking the same session "compare, then
revise the script" converts every other workstream's residual errors into things the
loop can fix on its own. WS2/WS3 raise the floor so the loop starts close.

---

## 4. WS0 — Headless software renderer + `view` fixes (P0)

**Why first:** no GL context exists here (pyglet: zero screens). You cannot do WS4,
WS5, or even sanity-check WS2/WS3 without a GL-free render path. Appendix A contains
a proven pure numpy+PIL rasterizer (used to produce every render measurement in §1);
adapt it rather than rewriting from scratch.

Implementation:

1. Add a private module-level section in `formcast.py` (keep single-file):
   `_soft_render(scene, width, height, az_deg, el_deg, zoom, up='+y'|'+z') -> PIL.Image`
   plus `_render_views(glb_path, out_dir, stem) -> list[Path]` that renders a
   standard set: front (el≈8°), 3/4 close-up of the upper half (zoom≈2.2), and a
   side view. Honor: `baseColorTexture`, `COLOR_0` (multiply), `alphaMode MASK` +
   `alphaCutoff`, `doubleSided`, `baseColorFactor`. Two fixed directional lights +
   ambient is enough (see Appendix A). Auto-detect up-axis from bounds or accept a
   parameter; after WS1 everything is +Y-up.
2. `view` subcommand: add `--renderer {auto,gl,soft}` (default `auto`). `auto`
   tries the GL path; on failure (including pyglet's no-screen `IndexError`) falls
   back to the soft renderer with an INFO note instead of erroring. `--save` works
   headless via soft path. Fix the error text for the interactive path: detect the
   no-display case and say "no display detected — use --save (software renderer)".
3. Performance: the Appendix A implementation renders a 13k-tri tree at 900×1000 in
   a few seconds — fine. If Run-B-sized models (70k tris) are slow, sort geometry
   by mesh and vectorize per-triangle bbox loops only if needed; do not add deps.
4. README: document `view --renderer`, headless behavior, and that `--save` no
   longer needs a display.

Acceptance: `python formcast.py view outputs/broadleaf-maple-00.glb --save x.png`
succeeds on this machine; leaf cutouts visibly honor MASK; a 3-model row renders.

---

## 5. WS1 — glTF correctness: +Y-up, scale, base placement (P0)

1. **Author Y-up natively.** In `PASS2_INSTRUCTION`, change the contract: "+Y is up
   (glTF convention). The ground plane is XZ; the object's base sits at y=0 and the
   object is centered near the origin in X/Z." Do NOT bolt on a rotation transform
   at export time — authoring Y-up keeps every downstream step (UVs "along the limb
   axis", renders, audits) consistent.
2. **Real-world scale.** Require "1 unit = 1 meter; choose a plausible real-world
   size for the described object and put the chosen height in a module-level
   constant". (The maple description says "mature shade tree" → the model should
   pick ~10–15 m. Do not hardcode numbers in formcast; the *requirement* is generic.)
3. **Audit** (part of WS5 but minimally here): after `_validate_full_script` bakes
   the probe GLB, load it and assert: finite bounds; `min.y ≥ -0.02 × height` and
   `≤ 0.05 × height` (base at ground); height between 0.05 m and 150 m. Feed
   failures into the existing repair loop verbatim.
4. Check `_compose_row` and the renderer assume nothing about Z-up (they currently
   lay out along X — fine either way).

Note: existing baked GLBs in `outputs/` stay Z-up; the soft renderer should accept
both (`up` parameter) so old baselines remain comparable.

---

## 6. WS2 — Geometry prompt overhaul (PASS2_INSTRUCTION) (P1)

Rewrite the foliage/structure guidance from "scatter a few hundred quads" to an
explicit crafting spec. Keep it conditional: "for trees/shrubs (canopy-bearing
archetypes) …; for rocks/boulders …". The bullets below are the content to encode
(adapt wording, keep the output contract identical):

**Crown envelope first.**
- Derive an explicit crown envelope (lobed ellipsoid / superellipsoid: base shape
  plus 3–6 low-frequency radial bulges) whose proportions match the reference:
  crown height fraction, crown width : total height, where the widest point sits.
  State in the prompt that the model should *measure these by looking at the image*
  and write them as named constants with comments (e.g. `CROWN_WIDTH_FRAC = 0.78`).
  The maple photo's truth, for your own verification only: crown = 79% of height,
  max width ≈ 0.78 × total height, widest slightly above mid-crown, overall w/h 0.84.
- Branches must grow *to fill the envelope*: bias growth direction toward unfilled
  envelope regions, terminate near the shell, never protrude past it by more than
  ~3% (this kills both the "wing" outliers and the tube-through-canopy artifact).

**Clumped foliage, not i.i.d. scatter.**
- Choose 10–25 clump centers on/just inside the envelope shell (plus 2–5 interior),
  preferably at high-order branch tips so structure and foliage agree.
- Per clump, spawn 40–120 cards inside a small ellipsoid (clump radius ≈ 8–15% of
  crown width). Card half-size ≈ 3–6% of crown width, log-normal jitter.
- Orient cards mostly tangent to the local clump surface, normal pointing outward
  with ±25° jitter; a minority (~20%) random for interior fill. Add a sparse ring of
  slightly drooping cards along the crown's lower margin (the photo's "skirts").
- Totals at `high`: 1,500–3,500 cards. `med` ≈ 40%, `low` ≈ 12% of that.
- Target outcome (will be gate-checked in WS5): front-view crown-bbox fill within
  ~10 points of the reference photo (maple: 67%), no isolated card farther than
  ~6% of crown width from its nearest neighbor.

**Wood.**
- Trunk: 12–16 sides at high; radius profile with basal flare (×1.3–1.6 over the
  bottom 5–8%); gentle lean/curve. Branches: ≥6 sides until radius < ~1.5 cm.
- Children start *inside* the parent (overlap ≥ parent radius) so junctions never
  show seams; child radii follow approximately r_parent² ≈ Σ r_child² (da Vinci).
- Hide everything above the lowest foliage clump from silhouette concern, but keep
  interior limbs — the photo shows "dark struts glimpsed through gaps".

**Budgets & misc.**
- Total triangle budget: ≤ 80k at high, ≤ 25k med, ≤ 8k low; put per-density
  numbers in one `_params(density)`-style table.
- Surface naming contract unchanged ("trunk", "branches", "canopy"); explicitly
  require "canopy" exists for canopy-bearing classes (Run B silently merged names).
- Y-up + meters + base-at-origin per WS1.
- Determinism per existing rules.

**API gotchas paragraph (saves a repair round ≈ 60–75 s each):** add to
both PASS2 and PASS3 prompts: "Environment: numpy 2.x (`ndarray.ptp()` removed —
use `np.ptp(arr)`; no `np.float`/`np.int`), Pillow 12 (`Image.ANTIALIAS` removed —
use `Image.LANCZOS`), trimesh 4.x. Do not import scipy. Before returning, mentally
re-check the code compiles (both observed failures were one-liners: a `.ptp()` call
and a keyword-then-positional argument)."

---

## 7. WS3 — Texturing prompt overhaul (PASS3_INSTRUCTION) (P1)

This is where "good" becomes "photoreal". Four sub-specs to encode:

**7.1 Leaf-cluster atlas (replaces the single blurry swatch).**
- One RGBA atlas, **1024×1024, 4×4 = 16 tiles** (each 256²). Each tile = one leaf
  *cluster*: 8–25 overlapping individual leaf silhouettes at varied rotation/scale,
  drawn procedurally with PIL `ImageDraw.polygon` (anti-aliased via 4× supersample
  then LANCZOS downscale).
- Leaf silhouette comes from the description (generic mechanism, species-specific
  result): the model should write a parametric outline function matching the
  described leaf ("broad palmate-to-lobed, serrated" → 5-lobed pointed polygon with
  serrated edge jitter). For other archetypes the prompt text stays the same —
  "draw the leaf shape the description calls for".
- Color: sample the photo's foliage palette (see 7.3) — per-leaf hue/value jitter,
  subtle per-leaf linear gradient (tip brighter), darker leaves underneath earlier
  ones in the stack (paint back-to-front with multiply-darkened lower layers).
- Tile variation axis: tiles 0–7 "sunlit" (warm bright greens, high contrast),
  tiles 8–15 "shaded" (cool dark greens, low contrast). Cards pick tiles by their
  position (see 7.3).
- **Alpha discipline:** silhouette alpha is binary with only anti-alias edges —
  target ≤ 5–8% of texels in 16 < a < 240, opaque coverage 35–70% per tile. No
  global blurs of the alpha channel. (Baseline was 48% semi — this is the actual
  fix for "leaves should be transparent".)
- UVs: each card maps the full quad to one tile (`u ∈ [i/4,(i+1)/4]` etc.) with a
  random 0/90/180/270 rotation and occasional mirror for variety.

**7.2 Bark.**
- 512² (or 1024×512 for tall wraps). Sample the *measured* trunk region (7.3), not
  a hardcoded box.
- **Replace roll+blur tiling.** Two acceptable techniques, in order of preference:
  (a) mirror-fold: reflect-pad to 2× then average the seam-crossing strips only
  within ~8 px (preserves interior detail exactly); (b) patch quilting: stack 3–5
  vertically-offset copies of the strip blended with ragged vertical masks. The
  forbidden thing is any full-width/height Gaussian seam cross. Gate (WS5): no
  64-px column/row whose mean local gradient < 40% of the texture's median.
- De-light as today (divide by heavily blurred luminance) but clamp the gain to
  [0.6, 1.6] so it can't wash regions out.
- **Normal map from albedo:** height = inverted luminance, Sobel → tangent-space
  normal, strength tuned for shallow fissures; attach as `normalTexture`
  (verified exported — Appendix C). Roughness 0.85–0.95, metallic 0.
- Edge hygiene: when the sampled strip includes background (white) pixels, erode
  the content mask 2–3 px before filling, so no white specks survive (baseline has
  them).

**7.3 Palette + region measurement (deterministic, in the generated script).**
- The script must *measure* rather than guess: build a foreground mask (for
  near-uniform backgrounds: `~all(|px - border_median| < tol)`; if the mask is
  degenerate, fall back to model-chosen normalized crop boxes — keep both paths).
- Foliage pixels = foreground ∧ green-dominant; trunk strip = the narrow column of
  foreground in the lower region. From these derive: sunlit foliage color (mean of
  top-20%-luminance foliage), shade color (bottom 20%), mean bark color. (Maple
  ground truth for your verification: ≈(152,171,93) / ≈(35,50,5) / ≈(80,76,61).)
- These constants drive atlas tinting and the vertex-color field below.

**7.4 Baked lighting variation via COLOR_0 (the SpeedTree trick).**
- Per-card vertex tint = f(position): cards high + near the envelope shell →
  1.0–1.15 × sunlit tint; deep/interior/low cards → 0.45–0.7 × toward shade tint;
  smooth blend by normalized depth-into-crown and height. Slight per-clump random
  tint (±6%) so clumps read as distinct masses.
- Mechanism (verified working, Appendix C): set
  `mesh.visual.vertex_attributes["color"] = uint8 (N,4)` on the textured canopy
  mesh → exports as `COLOR_0`, multiplies `baseColorTexture` in glTF.
- Also tint wood: slight darkening up high (thin branches read darker) and in
  crotches.
- The soft renderer (WS0) must multiply COLOR_0 so you can SEE this without an
  external engine.
- Fallback if any target engine ignores COLOR_0 (note in README): split canopy
  into 2–3 meshes by lighting zone with different `baseColorFactor` tints —
  implement only if a real consumer needs it.

**7.5 Material parameters.** Foliage: roughness ~0.8, metallic 0, MASK cutoff
0.4–0.5, doubleSided true. Wood: roughness 0.9, metallic 0. No emissive.

---

## 8. WS4 — Pass 3.5: closed-loop visual refinement (P1, highest leverage)

After Pass 3 validates, formcast currently freezes the script. Insert a refinement
loop that lets the same Claude session *see* its work:

```
for i in range(args.refine):                      # new flag: --refine N, default 2
    bake probe GLBs (seed 0 and seed 1, density high) into the CLI workdir
    render with WS0: per seed → front, side, canopy close-up   (e.g. 900×1100)
    also write texture sheets: the atlas + bark PNGs extracted from the GLB,
        and a side-by-side composite [reference | front render] for direct compare
    compute audit metrics (WS5): crown fill, aspect, alpha histogram, palette ΔE,
        two-tone ratio, tri count
    ask (same session, attach_image=False — reference is already in context):
        "The script you wrote was baked and rendered. Read these files:
         render-s0-front.png, render-s0-side.png, render-s0-closeup.png,
         render-s1-front.png, compare-front.png, atlas.png, bark.png.
         Measured gaps vs the reference: <metrics table>.
         List the 3 biggest realism gaps you can SEE, then return the COMPLETE
         revised script fixing them (same contract). If nothing meaningful would
         improve, reply exactly APPROVED."
    if reply is APPROVED: break
    extract code → _validate_full_script (+ audits) → existing repair loop on failure
    keep the new script only if it passes validation; otherwise keep the previous one
```

Implementation notes:

- The CLI's only tool is `Read`; renders land in `llm.workdir` next to
  `reference.png`, so `Read render-s0-front.png` just works (same mechanism the
  image attach uses today — see `ClaudeCLI.ask` / `image_in_workdir`).
- Keep prompts generic ("realism gaps vs the reference") — no species words.
- Plumbing: `--refine N` (0 disables), wire into `cmd_bake` between pass 3 and the
  artifact save; log per-iteration timings/cost at DEBUG like other passes; save
  each iteration's script as `workdir/script_refine_<i>.py` for the logfile trail.
- Time: each iteration ≈ one pass-3-sized call (~1–3 min) + ~5 s of bake/render;
  default `--refine 2` keeps a full bake under ~15 min. Note the timings in README.
- Optional model lever (document, don't default): `--refine-model sonnet` runs
  critique iterations on a cheaper model while authoring stays on opus —
  right-model-for-the-task (see CLAUDE.md).
- The final refined script is what gets saved/embedded — provenance already records
  `prompt_version`; also record `refine_iterations` in the metadata `provenance`.

This is also the mechanism that generalizes: rocks, shrubs, anything — the loop
sees what's wrong in *that* bake without formcast knowing anything about the domain.

---

## 9. WS5 — Objective quality gates (P2)

Add `_audit_glb(glb_path, image_path, spec) -> list[str]` (empty = pass) used by
`_validate_full_script` and the refine loop. Parse materials/textures from the GLB's
JSON chunk + embedded PNGs (snippet: Appendix B.3); render via WS0 for the
silhouette metrics. Suggested gates (hard unless noted):

| Gate | Threshold (class: tree/shrub) |
|---|---|
| Up-axis / base | min.y in [−2%, +5%] of height; height 0.05–150 m (all classes) |
| Canopy material | exists; MASK; cutoff 0.3–0.6; doubleSided; metallic 0 |
| Textures | atlas ≥ 1024² (or ≥16 tiles ≥ 256² each); bark ≥ 512²; PNG embedded |
| Alpha discipline | semi-alpha (16<a<240) ≤ 10% of atlas texels; opaque 30–75% |
| Bark smear | no 64-px column/row with mean gradient < 40% of texture median (warn) |
| Silhouette aspect | model front-view w/h within ±0.15 of photo's content bbox w/h * |
| Crown fill | within ±12 points of photo crown-bbox fill * (warn at ±8) |
| Foliage palette | rendered foliage mean RGB within ΔE*ab ≈ 12 (or RGB dist < 40) of photo foliage mean * |
| Two-tone | rendered foliage luminance p90/p10 ≥ 2.2 (photo ≈ 4) |
| Budgets | tris ≤ 80k/25k/8k for high/med/low; canopy cards 1.2k–4k at high |
| Seed consistency | same seed bakes a closely-matching model twice (warn only — seed/temperature/PNG-encoder variation is expected) |

\* photo-relative gates only run when the reference has a measurable near-uniform
background (the mask heuristic from §7.3, computed by formcast in Python — same
code, host-side). Otherwise skip with a DEBUG note. This keeps gates generic for
in-situ photos.

Gate failures are appended to the repair-loop error text (they're strings), so the
existing `_author_with_repair` machinery handles re-prompting unchanged. Class
"rock"/"boulder" runs only the class-agnostic rows.

---

## 10. WS6 — Variant differentiation (P2)

Today seeds only jiggle the random walk. Require (PASS2) that seed also varies, at
stated small amplitudes: crown width ±8%, height ±7%, lean ±3°, clump count ±20%,
palette value jitter ±4%. All variants must still pass the WS5 gates (so they read
as siblings, not different species). Verify with a 6-up contact sheet render
(`view outputs/dev/<tag>/ --save contact.png`).

---

## 11. Verification protocol (run after each workstream)

1. Cheap loop (no model calls, free): edit/run the *saved generator* directly —
   `python outputs/dev/<tag>/broadleaf-maple.generator.py --image inputs/maple-tree.png
   --seed 0 --density high --output /tmp/t.glb` — then render + audit. Use this
   while developing WS0/WS1/WS5 and when hand-checking texture techniques.
2. Full loop (model in the loop, ~7–15 min):
   `python formcast.py bake inputs/maple-tree.png --out-dir outputs/dev/<tag> --count 3 -v`
   then render the row, view the PNGs with Read, record metrics + timings (from
   `formcast.log`: per-pass durations) in a short table in your summary.
3. Compare against: the photo, the §1 baseline numbers, and the user's original
   `outputs/*.glb` (render them with `up='+z'`).
4. A change ships only if: all hard gates pass AND the front render visibly beats
   the baseline when you look at them side by side. Trust your eyes over metrics
   when they disagree — then improve the metric.
5. Re-bake consistency check before declaring victory: run the full bake twice;
   both runs should land a *good* model (pass gates). The bar is a reliable
   quality floor, not identical output — seed/temperature variation is expected
   and fine.

Engineering heuristic: if a prompt change needs more than ~3 full-bake iterations
to stabilize, the constraint probably belongs in a gate (checked in code) rather
than in prose. (No fixed bake/dollar budget — see CLAUDE.md for pacing.)

---

## 12. Experiments menu (P3 — different things to try, ranked)

1. **Photo-sourced leaf sprites (high win, medium risk).** When the background mask
   exists, harvest 20–60 real leaf-cluster sprites from the *photo's canopy edge*
   (connected components of foliage touching background → crisp natural alpha),
   normalize lighting, and quilt them into the atlas instead of / mixed with drawn
   silhouettes. Photoreal texture for free; risk: messy alpha → must still pass the
   alpha-discipline gate.
2. **Two-layer canopy:** large soft "mass" cards (shaded tiles) forming the volume
   + smaller crisp "edge" cards on the shell for silhouette fluff. Mimics how the
   photo reads (solid interior, detailed rim).
3. **Space-colonization branching** (attraction points filling the envelope) instead
   of recursive random walk — more believable limb spread, naturally fills the
   crown; ~80 lines of numpy.
4. **Sky-occlusion bake:** per-card AO = fraction of upward rays leaving the
   envelope; fold into COLOR_0 (cheap, big depth cue).
5. **Backlit rim tiles:** 2 atlas tiles tinted toward yellow-translucent for cards
   whose normal faces away from the key light — fakes leaf translucency without
   KHR extensions.
6. **KHR_materials extensions** (sheen/specular) via a pygltflib post-pass — only
   if the user's target engine honors them; core-only is safer. (Ask user first.)
7. **Multi-reference input:** accept 2–3 photos (`bake img1 img2 ...`), copy all
   into the workdir, let Pass 1 synthesize; helps where one angle under-specifies.
8. **Perceptual metric in the refine loop:** if the user later allows a dev-only
   dep, LPIPS/CLIP similarity photo↔render as an extra refine signal. Not now.
9. **`--refine-model` cost tuning** (see WS4) and trying `--model claude-fable-5`
   (most capable current model; `opus` alias = Opus 4.8) for Pass 2/3 authoring —
   measure quality-per-dollar on this exact task before switching defaults.
10. **"ultra" density tier** above high (8k cards, 2048² atlas) for hero assets —
    only after gates hold at high.

---

## 13. Acceptance criteria for the maple benchmark (definition of done)

- [ ] All WS5 hard gates pass on `--count 3`, twice in a row (fresh sessions).
- [ ] Front render: crown fill within 12 points of 67%; aspect within 0.15 of 0.84;
      no floating clumps (nearest-neighbor rule); trunk shows no smear column.
- [ ] Leaf cutouts: real leaf-cluster silhouettes with crisp edges at MASK 0.5;
      atlas semi-alpha ≤ 8%.
- [ ] Visible sun/shade gradient across the canopy (p90/p10 ≥ 2.2) and per-clump
      tonal grouping.
- [ ] +Y-up, base at y≈0, ~10–15 m tall; loads upright in an external viewer
      (verify JSON: a `rotation`-free node tree with Y-up bounds is sufficient).
- [ ] `view --save` works headless; README documents all new flags
      (`--refine`, `--renderer`, …) and the updated pipeline (incl. pass 3.5).
- [ ] `PROMPT_VERSION` bumped; header docstring updated; `formcast.log` shows
      per-pass + per-refine timings/cost.
- [ ] Side-by-side `[photo | best render]` composite that a human would call
      "clearly the same kind of tree, clearly much better than baseline".

---

## Appendix A — Proven software rasterizer (adapt into formcast.py)

Used for every render in this analysis; handles texture sampling, MASK cutoff,
doubleSided lighting, perspective-correct UVs. Add COLOR_0 multiply where noted.
Z-up camera as written (parameterize for Y-up per WS0).

```python
import numpy as np
import trimesh
from PIL import Image


def gather(scene):
    """(name, verts, faces, uv, tex_rgba, alpha_mask, cutoff, doublesided) per mesh.
    WS0 TODO: also pull visual.vertex_attributes['color'] for COLOR_0 multiply.
    CORRECTION (verified by experiment, see MASTER_PLAN §5.4): iterate
    scene.dump() — which applies scene-graph node transforms — NOT
    scene.geometry.items(), whose vertices are geometry-local. Formcast's current
    GLBs have identity transforms so both work, but any GLB with a root rotation
    (e.g. external assets) renders wrongly with the raw-geometry version."""
    out = []
    for name, geom in scene.geometry.items():  # see CORRECTION above before reuse
        v = np.asarray(geom.vertices, dtype=np.float64)
        f = np.asarray(geom.faces, dtype=np.int64)
        uv, tex, amask, cutoff, ds = None, None, False, 0.5, False
        vis = geom.visual
        if hasattr(vis, "uv") and vis.uv is not None:
            uv = np.asarray(vis.uv, dtype=np.float64)
        mat = getattr(vis, "material", None)
        img = None
        if mat is not None:
            img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
            amask = (getattr(mat, "alphaMode", None) == "MASK")
            c = getattr(mat, "alphaCutoff", None)
            if c is not None:
                cutoff = float(c)
            ds = bool(getattr(mat, "doubleSided", False))
        if img is not None:
            tex = np.asarray(img.convert("RGBA"), dtype=np.uint8)
        out.append((name, v, f, uv, tex, amask, cutoff, ds))
    return out


def render(meshes, width, height, az_deg, el_deg, zoom=1.0, bg=(255, 255, 255)):
    allv = np.vstack([m[1] for m in meshes])
    lo, hi = allv.min(0), allv.max(0)
    center = (lo + hi) / 2.0
    radius = float(np.linalg.norm(hi - lo)) / 2.0

    az, el = np.radians(az_deg), np.radians(el_deg)
    cam_dir = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    cam_pos = center + cam_dir * radius * 2.6 / zoom
    fwd = center - cam_pos; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 0.0, 1.0]); right /= np.linalg.norm(right)  # world up: Z here; parameterize
    up = np.cross(right, fwd)
    fpx = (height / 2.0) / np.tan(np.radians(38.0) / 2.0)

    zbuf = np.full((height, width), np.inf)
    img = np.empty((height, width, 3)); img[:] = np.asarray(bg, float)
    l1 = np.array([0.5, -0.6, 0.62]); l1 /= np.linalg.norm(l1)
    l2 = np.array([-0.6, 0.4, 0.3]); l2 /= np.linalg.norm(l2)

    for name, v, f, uv, tex, amask, cutoff, ds in meshes:
        rel = v - cam_pos
        cx, cy, cz = rel @ right, rel @ up, rel @ fwd
        ok = cz > radius * 0.05
        sx = width / 2.0 + fpx * cx / cz
        sy = height / 2.0 - fpx * cy / cz
        e1 = v[f[:, 1]] - v[f[:, 0]]; e2 = v[f[:, 2]] - v[f[:, 0]]
        fn = np.cross(e1, e2)
        n = np.linalg.norm(fn, axis=1, keepdims=True); n[n == 0] = 1; fn /= n

        for ti in range(len(f)):
            i0, i1, i2 = f[ti]
            if not (ok[i0] and ok[i1] and ok[i2]):
                continue
            xs = np.array([sx[i0], sx[i1], sx[i2]]); ys = np.array([sy[i0], sy[i1], sy[i2]])
            zs = np.array([cz[i0], cz[i1], cz[i2]])
            minx = max(int(np.floor(xs.min())), 0); maxx = min(int(np.ceil(xs.max())), width - 1)
            miny = max(int(np.floor(ys.min())), 0); maxy = min(int(np.ceil(ys.max())), height - 1)
            if minx > maxx or miny > maxy:
                continue
            gx, gy = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
            d = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
            if abs(d) < 1e-12:
                continue
            w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / d
            w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / d
            w2 = 1.0 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any():
                continue
            iz = w0 / zs[0] + w1 / zs[1] + w2 / zs[2]
            zpix = 1.0 / np.maximum(iz, 1e-12)
            sub_z = zbuf[miny:maxy + 1, minx:maxx + 1]
            closer = inside & (zpix < sub_z)
            if not closer.any():
                continue
            if tex is not None and uv is not None:
                u = (w0 * uv[i0, 0] / zs[0] + w1 * uv[i1, 0] / zs[1] + w2 * uv[i2, 0] / zs[2]) * zpix
                vv = (w0 * uv[i0, 1] / zs[0] + w1 * uv[i1, 1] / zs[1] + w2 * uv[i2, 1] / zs[2]) * zpix
                th, tw = tex.shape[:2]
                tx = np.clip((u % 1.0) * (tw - 1), 0, tw - 1).astype(np.int32)
                ty = np.clip((1.0 - (vv % 1.0)) * (th - 1), 0, th - 1).astype(np.int32)
                texel = tex[ty, tx].astype(np.float64)
                rgb = texel[..., :3]
                if amask:
                    closer = closer & (texel[..., 3] >= cutoff * 255.0)
                    if not closer.any():
                        continue
                # WS0 TODO: rgb *= interpolated COLOR_0 / 255
            else:
                rgb = np.full(gx.shape + (3,), 180.0)
            nrm = fn[ti]
            lam = max(0.0, nrm @ l1) + (max(0.0, (-nrm) @ l1) if ds else 0.0)
            lam2 = max(0.0, nrm @ l2) + (max(0.0, (-nrm) @ l2) if ds else 0.0)
            shade = min(0.45 + 0.45 * min(lam, 1.0) + 0.25 * min(lam2, 1.0), 1.25)
            colored = np.clip(rgb * shade, 0, 255)
            sub_img = img[miny:maxy + 1, minx:maxx + 1]
            sub_img[closer] = colored[closer]
            sub_z[closer] = zpix[closer]
    return Image.fromarray(img.astype(np.uint8), "RGB")
```

## Appendix B — Reproduce the baseline measurements

**B.1 Crown fill / aspect / palette of the photo** (host-side; same code becomes the
§7.3/§9 measurement helper):

```python
import numpy as np
from PIL import Image
im = np.asarray(Image.open('inputs/maple-tree.png').convert('RGB'), np.float32)
nonwhite = ~(im > 235).all(axis=2)
ys, xs = np.where(nonwhite)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
aspect = (x1 - x0) / (y1 - y0)                      # 0.84
crown = nonwhite[y0:y0 + int((y1 - y0) * 0.79), x0:x1]
fill = crown.mean()                                  # 0.67
green = nonwhite & (im[:, :, 1] > im[:, :, 0]) & (im[:, :, 1] > im[:, :, 2])
g = im[green]; lum = g.mean(1)
sun = g[lum > np.percentile(lum, 80)].mean(0)        # ~(152,171,93)
shade = g[lum < np.percentile(lum, 20)].mean(0)      # ~(35,50,5)
```

**B.2 Render any baked GLB headless:** adapt Appendix A; the user's existing
`outputs/*.glb` are Z-up, new ones (post-WS1) are Y-up.

**B.3 Inspect materials/images inside a GLB** (basis for the WS5 audit):

```python
import json, struct, io
from PIL import Image
data = open(path, 'rb').read()
clen, _ = struct.unpack_from('<II', data, 12)
js = json.loads(data[20:20 + clen].decode())
# js['materials'][i]['alphaMode' / 'alphaCutoff' / 'doubleSided' / 'normalTexture']
bs = 20 + clen
blen, _ = struct.unpack_from('<II', data, bs)
binc = data[bs + 8:bs + 8 + blen]
for img in js.get('images', []):
    bv = js['bufferViews'][img['bufferView']]
    off = bv.get('byteOffset', 0)
    pil = Image.open(io.BytesIO(binc[off:off + bv['byteLength']]))  # .mode/.size, alpha histogram
```

**B.4 Baseline logs:** `formcast.log` lines 1–56 (Run A: timings, per-pass cost,
the pass-3 SyntaxError repair) and 57+ (the user's failed `view`, plus Run B with
the numpy-2 `.ptp()` repair).

## Appendix C — Verified trimesh 4.12.2 export capabilities (don't re-litigate)

Test performed in this environment; all assertions held, including round-trip:

```python
mat = trimesh.visual.material.PBRMaterial(
    baseColorTexture=rgba_pil, normalTexture=rgb_pil,
    metallicFactor=0.0, roughnessFactor=0.8,
    alphaMode="MASK", alphaCutoff=0.5, doubleSided=True)
mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
mesh.visual.vertex_attributes["color"] = np.uint8_rgba_per_vertex   # (N,4)
# exported GLB primitive attributes: ['COLOR_0', 'POSITION', 'TEXCOORD_0']
# exported material keys include: alphaMode/alphaCutoff/doubleSided/normalTexture
# trimesh.load() round-trips the color attribute
```

Also verified: the foliage MASK/cutoff/doubleSided in the existing baked GLBs is
already correct in the file — the rendering/evaluation side was the gap. Environment:
trimesh 4.12.2, numpy 2.4.6 (no `ndarray.ptp()`), Pillow 12.0.0, pyglet 1.5.31
(needs a display), pyrender absent, `claude` CLI 2.1.170 on PATH, authenticated.
