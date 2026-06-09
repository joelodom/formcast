# formcast

**Turn a single photo into a small library of 3D models.**

Hand formcast one reference photo — say, a snapshot of a maple tree — and it gives
you back a handful of ready-to-use `.glb` 3D models in that same style. Not ten
copies of the *exact* tree in your photo, but ten believable variations on the
same *kind* of thing: different branches, different proportions, the same
character. Drop them into Blender, three.js, Godot, Unity, or any glTF viewer.

formcast is a single command-line tool. Behind the scenes it asks Claude Code
(running locally on your own machine) to look at your photo and *write the
procedural modeling code*, then runs that code for you to bake out the finished
models. You bring a picture; you get back models.

---

## What you can do with it

formcast has three commands:

| Command   | What it does |
| --------- | ------------ |
| `bake`    | A photo goes in; a set of seed-varied `.glb` models comes out. This is the main event. |
| `inspect` | Print (or pull back out) the metadata tucked inside each `.glb` — including the original photo and the exact script that built it. |
| `view`    | Open a 3D preview of one model, or a whole row of variations side by side. |

---

## Getting started

### 1. Install the Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Claude Code and sign in once

formcast uses the local `claude` command to do the creative heavy lifting, so it
needs to be installed and signed in once:

```bash
npm install -g @anthropic-ai/claude-code   # needs Node.js
claude                                       # run once to authenticate
```

A Claude subscription login works fine, or set `ANTHROPIC_API_KEY` if you prefer.
formcast itself never asks you for an API key.

### 3. Create the outputs folder

This repo already ships with a sample photo at `inputs/maple-tree.png`. Baked
models go in `outputs/`, which isn't tracked in git — so create it before your
first bake:

```bash
mkdir -p outputs
```

(If you forget, formcast will create the output directory for you on the first
bake — but making it yourself keeps things tidy.)

### 4. Bake your first models

Bake the bundled sample (or drop your own photo in `inputs/` and point at that):

```bash
python formcast.py bake inputs/maple-tree.png --out-dir outputs/ --count 10
```

formcast looks at the photo, works out what it's seeing, writes a procedural
generator for it, and bakes ten variations into `outputs/`. When it's done,
preview them all at once:

```bash
python formcast.py view outputs/maple-tree-*.glb
```

That's the whole loop: **photo in → a row of models out.**

---

## A few more examples

```bash
# Also bake a high/medium/low level-of-detail (LOD) chain for each variant
python formcast.py bake inputs/maple-tree.png --out-dir outputs/ --count 10 --lods

# Pin an exact model instead of the default
python formcast.py bake inputs/maple-tree.png --model claude-opus-4-8

# Look inside a finished model
python formcast.py inspect outputs/maple-tree-03.glb

# Pull the embedded photo, generator script, and description back out to files
python formcast.py inspect outputs/maple-tree-03.glb --extract ./extracted/

# Render a single model straight to a PNG (works without a display)
python formcast.py view outputs/maple-tree-03.glb --save preview.png
```

formcast works best on natural objects with clear structure and surfaces — trees,
shrubs, plants, boulders, rock formations, logs — the kinds of things that read as
"a trunk, some branches, a canopy" or "a rock with this kind of surface."

---

## A quick note on trust

`bake` does two things worth understanding before you run it:

1. It runs the local `claude` CLI, restricted to its **Read** tool only — during a
   bake it can look at your image and nothing else (it can't write files or run
   commands).
2. It then **executes the Python that Claude wrote**, in a subprocess, to actually
   build the meshes. That's the whole idea of the tool — but it does mean running
   model-generated code, so run formcast on a machine you trust.

`inspect` and `view` never execute embedded code; they only read data.

---

## Logs

formcast tells you what it's doing as it runs. By default you get clean, readable
progress on screen (INFO level), and a complete, timestamped DEBUG trace — per-pass
and per-variant timings, plus each Claude call's duration and token/cost usage — is
always written to **`formcast.log`** (gitignored). Add `-v`/`--verbose` to see that
DEBUG detail on screen too:

```bash
python formcast.py bake inputs/maple-tree.png --verbose
```

If a run is slow or something looks off, `formcast.log` is the first place to look
(and the handy thing to share).

---

## How it works

Curious what happens between "photo in" and "models out"? Under the hood, `bake`
runs four passes. The first three ask Claude Code (locally, in headless mode) to
author increasingly complete code; the last one is just plain plumbing.

1. **Classify & describe.** Claude looks at your photo and writes a short
   identifier (used for filenames) plus one rich paragraph describing the object's
   form, structure, surface materials, and overall character. The description is
   qualitative on purpose — it plays to the model's strengths and to the goal of
   capturing a *style*, not reconstructing one exact object.

2. **Author the geometry.** Claude writes a deterministic
   `build_mesh(seed, density)` function using `numpy` and `trimesh`, with geometry
   grouped by semantic surface name (`trunk`, `branches`, `canopy`, `rock`, …).
   formcast actually runs this code and checks the mesh is real and non-empty; if
   it fails, the error is handed back to Claude for a fix (a couple of retries).

3. **Author texturing & export.** Claude folds that geometry into one complete,
   standalone script that also pulls tileable material swatches out of your photo,
   applies UVs per surface type, assigns materials, and exports a `.glb`. Again
   formcast runs it end-to-end and confirms the result opens with real geometry.

4. **Bake.** With the generator now frozen and proven, formcast runs it N times
   with seeds `0..N-1` (optionally across detail levels) to produce
   `maple-tree-00.glb`, `maple-tree-01.glb`, and so on.

Finally, formcast tucks a small metadata bundle inside every `.glb` — the
description, the original photo, the *exact* generator script, and provenance
(which tool, model, and prompt version made it). That makes each file
self-describing and re-bakeable later with no outside context; `inspect` is how
you read it back. The metadata rides along quietly in the glTF JSON and is ignored
by your renderer, so it costs nothing at load time.

A nice consequence of all this: formcast isn't photogrammetry. It never tries to
reconstruct the precise object in your photo — it captures the *archetype*, enough
about the form and surfaces to generate an endless supply of fresh, believable
instances "of that kind." That's what makes it useful when you want variety: a
whole grove of distinct maples from a single photo of one.
