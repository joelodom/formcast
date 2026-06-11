# formcast — Technical Guide

This document explains how formcast works, and along the way introduces the 3D
modeling concepts it's built on. It assumes you're comfortable with code and
data structures but new to 3D graphics. Wherever possible the examples are
real incidents from this project's own development log (`EVALS.md`).

The other docs: [`README.md`](README.md) is the user guide,
[`SAMPLES.md`](SAMPLES.md) the visual results journal,
[`ROADMAP.md`](ROADMAP.md) the future work.

---

## Part 1 — A 3D modeling crash course for programmers

### 1.1 A model is a mesh: vertices and triangles

A 3D model is mostly just two arrays:

- **vertices** — an `(N, 3)` array of points in space: `[x, y, z]` each.
- **faces** — an `(M, 3)` array of integer indices into the vertex array.
  Each row names three vertices that form a **triangle**.

That's it. A teapot is ~37,000 little triangles whose corners happen to lie on
a teapot-shaped surface. Triangles are the universal currency because they're
the simplest shape that's always flat (any 3 points lie on a plane), which
makes them fast to draw. "How many triangles?" is the standard size/cost
measure — formcast budgets ≤ 80k triangles for a high-detail model, ≤ 8k for a
cheap distant one.

A mesh with more triangles isn't automatically better. The whole craft is
spending your triangle budget where the *silhouette* needs it. This project's
strongest design rule came from a furniture experiment: a simple chair that
nailed the essential masses beat a heavily detailed one (see SAMPLES, the
Windsor chair).

### 1.2 Normals: why surfaces look smooth or faceted

A **normal** is the direction a surface faces at a point. Lighting is computed
from normals: a triangle facing the light is bright, one facing away is dark.

The trick: you can store one normal *per face* (every triangle is uniformly
lit → the surface looks **faceted**, like a disco ball) or one *per vertex*,
averaged across the triangles that share it (lighting interpolates smoothly →
the surface looks **curved** even though it's still flat triangles). When our
tulip's petals looked like cut gemstones instead of soft petals, the cause was
exactly this: vertices weren't shared ("welded") between neighboring
triangles, so normals couldn't average and every facet showed.

### 1.3 Coordinates, up-axis, and units

Nothing in the math says which way is "up." Two conventions coexist in the
wild: **Y-up** (most game/graphics tools, and the glTF standard) and **Z-up**
(Blender, CAD). Get it wrong and your tree lies on its side — which is
literally what happened three separate times in this project before we
standardized: formcast models are **+Y up, base resting at y = 0, measured in
meters**. Old bakes (prompt version 1.0/1.1) were Z-up; the viewer reads each
file's embedded metadata and compensates.

### 1.4 Scenes and transforms

Models are organized as a **scene graph**: a tree of nodes, each with a
*transform* (a 4×4 matrix encoding position/rotation/scale) and optionally a
mesh. The same mesh can appear under several nodes — build one chair leg,
place it four times. Crucially, a mesh's vertices are stored in *local*
coordinates; you must apply the node transforms to get world positions. Our
renderer originally forgot this and two perfectly good models rendered tipped
over — the bug was in our *eyes*, not the models. (Lesson now baked into the
workflow: when a result looks bizarrely wrong, verify the harness on a
known-good asset before blaming the model.)

### 1.5 Textures and UV coordinates

Geometry gives shape; **textures** give color detail. A texture is just an
image, and **UV coordinates** are the mapping that says which point of the
image each vertex corresponds to: every vertex gets a `(u, v)` pair in
`[0,1]²`, and the renderer paints each triangle by stretching the
corresponding patch of image across it. Think of it as flattening the surface
onto wrapping paper.

Mappings have classic failure modes, and we've hit them:

- **Pole pinch.** Wrap an image around a sphere like latitude/longitude and
  all the texture columns converge at the poles — our v1.2.2 boulder shows
  dark streaks pinching at its apex for exactly this reason. Fixes: cellular/
  patch-based texturing, or *triplanar* projection (project the image from
  three axes and blend).
- **Visible seams** where the wrapping paper edges meet — handled by making
  textures *tileable* (the image's left edge continues its right edge).
- **Background contamination.** formcast builds textures by sampling colors
  from your photo. Early versions sampled blind rectangles that sometimes
  landed on background — giving a purple-striped tulip stem (bokeh) and a
  boulder wearing ocean colors. The fix: sample only well inside the object's
  silhouette, take medians of several small patches, and discard outliers.

### 1.6 Materials: how surfaces respond to light

Modern 3D uses **PBR** (physically based rendering) materials. The properties
that matter here:

- **Base color / albedo** — the texture image (or flat color).
- **Roughness** (0–1) — mirror-like vs chalky. Foliage ≈ 0.8, stone ≈ 0.95,
  finished wood ≈ 0.5–0.7.
- **Metallic** (0–1) — metals reflect differently; almost everything organic
  is 0.
- **Vertex colors (COLOR_0)** — a per-vertex RGB tint multiplied over the
  texture. Cheap way to add large-scale variation: sunlit crown brighter at
  the top, ambient-occlusion-style darkening near the ground.

A hard-won materials lesson: **very dark objects still need brightness
variation in their albedo.** Lighting reveals 3D form through value changes
across a surface; if the texture is uniformly near-black, there is nothing to
vary and the object collapses into a flat silhouette. Our black-painted chair
did exactly that — twice. Sampling the photo's sheen highlights fixed a
*glossy* black teapot, but a *matte* black chair has no sheen to sample; the
roadmap fix is to synthesize a value range for matte-dark surfaces.

### 1.7 Alpha and the leaf-card trick

Textures can carry transparency (**alpha**). glTF has three modes: OPAQUE,
**MASK** (each pixel fully visible or fully invisible, by threshold — crisp,
cheap, no sorting headaches), and BLEND (true translucency — pretty, but
order-dependent and artifact-prone).

This enables the single most important trick in real-time vegetation:
**leaf cards**. Nobody models thousands of individual leaves as geometry.
Instead you scatter a few thousand small flat rectangles ("cards") through the
crown, each textured with a *picture* of a leaf cluster whose alpha mask cuts
out the leaf silhouette. At any normal viewing distance the eye reads
overlapping leaf shapes, not flat cards. formcast's trees and shrubs are
leaf-card crowns: clumps of 40–120 cards around 10–25 clump centers on a
"foliage envelope" (a lobed ellipsoid that defines the crown's overall shape).

The generalization is one of this project's core findings: **fine repeating
detail belongs in the texture, not the geometry.** The Tiffany lamp's mosaic
shade timed out when the model tried to build hundreds of glass-tile solids —
and succeeded, faster and better-looking, as a smooth dome with a mosaic
*painted on*.

### 1.8 glTF / GLB: the file format

**glTF** is the standard interchange format for 3D ("the JPEG of 3D");
**GLB** is its single-file binary flavor. One `.glb` contains the scene graph,
meshes, materials, and embedded texture images. It also allows arbitrary
metadata ("extras") — formcast embeds the source photo, the complete generator
script, the prose description, and provenance (tool/model/prompt version) in
every model it bakes, so any output can be inspected (`formcast inspect`) and
reproduced later.

### 1.9 Procedural generation: the model is a program

formcast does not sculpt meshes directly. It writes a **generator**: a Python
program that *computes* the mesh with numpy + [trimesh](https://trimesh.org).
The standard construction tools:

- **Primitives** — boxes, cylinders, spheres.
- **Lathe / revolve** — spin a 2D profile curve around an axis: vases, teapot
  bodies, turned chair legs (the profile's bulbs and coves come from the
  photo).
- **Extrusion** — push a 2D outline through space: planks, table tops.
- **Displacement noise** — start from a sphere, push each vertex in/out by
  smooth random noise: rocks and boulders.
- **Instancing** — build one leg/leaf/spindle, place many with transforms.
- **Sweeps** — run a circle along a curve: spouts, handles, branches.

The generator takes a **seed** for its random number generator and is
**deterministic given the seed** — same seed, same model; different seed, a
sibling variation (slightly different branching, lean, proportions). That's
how one photo becomes a *library* of distinct-but-related models, and it makes
everything reproducible and debuggable. It also enables the cheapest workflow
in the project, the **free loop**: every bake saves its generator script, so
you can edit the code by hand and re-run it for zero AI cost, only paying for
a new AI authoring pass once a hand-tested idea is worth encoding in the
prompts.

### 1.10 Rendering without a screen

To *look at* a model you rasterize it: project each triangle to the screen,
fill its pixels, keep the nearest surface per pixel (depth buffering), shade
by normals and material. This Mac has no display and no working OpenGL, so
formcast includes a small pure-numpy **software rasterizer** (perspective
projection, depth buffer, texture sampling with MASK alpha, vertex-color
multiply, simple two-light shading). It is a *comparator*, not a beauty
renderer — good enough to judge silhouettes, proportions, and materials, which
is its whole job in the evaluation loop below.

---

## Part 2 — How formcast works

### 2.1 The pipeline

```
photo ──► PASS 1: classify & describe ──► PASS 2: author geometry code
                (vision)                        (craft-pack guidance)
                                                       │ validated
            PASS 3.5: refine loop  ◄── PASS 3: author texturing + GLB export
            render → critique → revise                 │ validated + audited
                       │
                       ▼
            PASS 4: bake N seed variants ──► outputs/*.glb (+ metadata)
```

All AI passes run the local `claude` CLI headlessly (read-only tools, your
machine, your photo never uploaded anywhere except to the model API).

- **Pass 1 — classify & describe.** A vision call looks at the photo and
  returns an archetype id (`comb-back-windsor-armchair`), a coarse **class**
  (`tree`, `furniture`, `vessel`, …), and a long prose description of the
  object's structure, proportions, and materials. Two separate channels
  matter: the *description* drives the geometry; the *class* selects the
  craft and materials. (We learned this when a chair misclassified as `log`
  still came out chair-shaped from its rich description — but textured like
  bark.) Classification is by what the whole object *is*, never its material.
- **Pass 2 — geometry authoring.** Claude writes the generator module
  (`build_mesh(seed, density)`), guided by a per-class **craft pack** — a
  block of distilled know-how injected into the prompt: foliage envelopes and
  leaf-card clumps for plants; lathe profiles, instancing, and measured member
  thicknesses for furniture; noise-displaced hulls for rocks; capsule-skeleton
  construction for creatures. The contract: Y-up, meters, base at y=0,
  triangle budgets, semantic surface names (`"trunk"`, `"seat"`, `"shade"`)
  so texturing can target each part. Code is executed and **validated**
  (does it run? sane bounds? budgets?) with automatic repair rounds on error.
- **Pass 3 — texturing & export.** Claude extends the generator into a full
  script that derives materials from the photo (silhouette-only sampling,
  de-lighting, tileable swatches, leaf/petal atlases with crisp MASK alpha,
  COLOR_0 tints), assigns UVs per surface type, and exports the GLB. The
  result must pass **audit gates** — objective checks (up-axis and ground
  placement, triangle budgets, texture resolution floors, alpha discipline,
  no floating fragments) whose failures feed the repair loop as plain text.
- **Pass 3.5 — the refine loop.** formcast bakes a preview, renders it from
  standard angles with the software rasterizer, and shows those renders back
  to the authoring session next to the photo: *name the three biggest gaps,
  then revise the script.* Revisions are validated and adopted only if they
  pass. This closed loop is the single most effective thing in the pipeline —
  it has caught a globally wrong color, a too-squat teapot, and an azalea that
  read as a tree, all before the user ever saw them.
- **Pass 4 — baking.** The final script runs once per seed — fast, free, no
  AI — producing N sibling `.glb` files, each with embedded provenance.

### 2.2 Evaluation: how we know a change helped

Quality claims are graded in tiers, cheapest first:

1. **Gates** (free, objective): the audit checks above.
2. **My own eyes** (free): render the standard views, score a fixed rubric
   1–5 (silhouette / proportions / surface / color-material / artifacts).
3. **An independent judge:** a *fresh* Claude session (never the one that
   authored the code) gets the photo plus two unlabeled render sheets —
   current champion vs candidate — and returns a forced choice with reasons;
   3 trials with A/B order alternated to cancel position bias. Promotion
   needs ≥ 2/3. This machinery exists because self-grading fails: the judge
   has twice overruled the author's scoring, and matched the user's
   independent verdicts when checked.
4. **Joel** (the user): outranks everything. Two standing quality directions
   came from his reviews — **class credibility over photo fidelity** (a
   convincing instance of the *kind* beats a copy of the photo) and
   **simplicity/geometric essence over detail-chasing**.

Per benchmark item, the best model so far is its **champion** (registry in
`ROADMAP.md`); every experiment is logged in `EVALS.md` with what worked and
what didn't, and every result is visible side-by-side with its photo in
`SAMPLES.md`.

### 2.3 The judge, mechanically

`formcast judge photo.jpg championA-contact.png candidateB-contact.png
--trials 3` spawns fresh sonnet sessions, alternates which sheet is "A",
and emits machine-readable JSON (last line of stdout) with per-trial picks,
rubric scores, and reasons. The judge prompt weighs class credibility first,
per the standing direction.

### 2.4 Repo map

| Path | What it is |
|---|---|
| `formcast.py` | The whole tool — single file, four subcommands (`bake`, `inspect`, `view`, `judge`) |
| `inputs/` | Source photos (gitignored except the tracked samples `maple-tree.png`, `pencil.png`) |
| `outputs/` | Baked models (never tracked); `outputs/dev/<run>/` holds experiment bakes + their generator scripts |
| `benchmarks/manifest.json` | The 9-item benchmark with license provenance; `benchmarks/cache/` (gitignored) holds the photos |
| `eval/` | Rendered contact sheets + reference thumbnails used by SAMPLES/README |
| `formcast.log` | Full DEBUG log of every run (gitignored) — timings, token usage, repair rounds |
| `README.md` / `SAMPLES.md` / `ROADMAP.md` / `TECHNICAL.md` / `EVALS.md` | Overview / visual journal / future work / this file / experiment log |

### 2.5 Design principles (earned, not assumed)

Each of these is backed by a logged experiment in `EVALS.md`:

- **Close the loop.** Models that *see renders of their own output* fix real
  flaws unprompted. (Refine loop adopted useful revisions in nearly every
  round across the benchmark.)
- **Class credibility over photo fidelity.** The product is a believable
  *kind*, not a replica.
- **Simplicity and geometric essence beat detail-chasing.** The simplest
  geometry that reads unmistakably as the kind wins; detail that muddies the
  silhouette is negative detail.
- **Repeating fine detail goes in textures, not geometry.**
- **Dark materials need a value range** — sampled from sheen when it exists,
  synthesized when matte.
- **Never trust a single blind sample** — texture colors come from medians of
  multiple in-silhouette patches.
- **Verify the harness before blaming the model** — two "broken" models were
  a renderer bug; three up-axis incidents taught us to check conventions
  per-file.
- **A per-example win can be a lucky outlier; optimize the general case.**
  The v1.1 chair still beats the modern pipeline on that one item — accepted,
  understood, not chased.
