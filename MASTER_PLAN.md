# Formcast Master Plan — General Photo → 3D

**Mission:** evolve formcast from "natural-object archetype baker" into a general,
dependable capability: **give it one photograph of a thing — a tree, a dog, a table,
a boulder, a mug — and get back a good 3D model (.glb) of that thing or that kind of
thing.** Photorealistic where achievable, honestly stylized where not, never broken.

**Who executes this:** Claude (Opus) working in this repo with Claude Code, largely
unattended. The user has limited access to frontier models, so this document is the
knowledge transfer: it contains the problem analysis, the prior-art survey, the
measured evidence, the architecture, the step-by-step phases, the self-evaluation
protocol, and the contingency playbook. You (Opus) are expected to do your own
research and experiments as you go — §2 tells you how to do that safely and cheaply.

**Relationship to other documents:**
- `PHOTOREALISM_PLAN.md` (2026-06-09) is the **detailed spec for Phases 0–1** (the
  rendering/eval foundations and the tree-photorealism pass). It remains
  authoritative for those phases; this document supersedes its framing and adds
  everything beyond trees. One correction to it: its Appendix A renderer must apply
  scene-graph transforms (use `scene.dump()`, not `scene.geometry` directly) — a
  bug found by experiment after that document was written (see §5.4).
- `CLAUDE.md` and `README.md` must be updated as scope broadens (Phase 3 changes
  the "natural object" framing to general objects). Keep README in sync with every
  behavior change — standing order.
- `EVALS.md` (you will create this in Phase 0) is the append-only evidence log every
  phase writes to.

**Standing constraints (unchanged):** work on `main`, no commits/pushes until the
user says so; generated scripts use only numpy/trimesh/PIL/stdlib (scipy is already
installed as a trimesh extra and MAY be allowed if you add it to requirements.txt
deliberately — manifold3d likewise ships with `trimesh[easy]` and is verified
working); never overwrite the user's `outputs/*.glb` baselines; bump
`PROMPT_VERSION` on prompt changes; the maple stays the canonical worked example.

---

## 1. Problem analysis: what "photo → 3D" actually requires

### 1.1 The object-class taxonomy that drives everything

Different kinds of objects need fundamentally different generation machinery. This
taxonomy is the backbone of the architecture (§6) — the router classifies into it,
craft packs serve it, and the scope ladder (§1.3) sets expectations by it.

| Class family | Examples | What makes it tractable/hard | Best-fit technique |
|---|---|---|---|
| **Structured organic** (self-similar, statistical) | trees, shrubs, grass, coral | No one "correct" shape — believability is statistical (branching laws, clumping). Hardest part is foliage/texture. | Procedural code (already the formcast core); alpha-cutout cards; photo-derived palettes |
| **Amorphous organic** | rocks, boulders, terrain chunks | Forgiving: any plausible lumpy shape works; texture sells it | Procedural (noise-displaced hulls + triplanar) — *easiest class* |
| **Manufactured, parametric** | tables, chairs, shelves, lamps, mugs, vases | Exact dimensions, symmetry, crisp edges; shape IS describable in words/numbers | Procedural CSG/lathe/extrude code — **validated strong in experiment T3 (§5.3)** |
| **Articulated organic** | dogs, cats, horses, birds | Anatomy: thousands of subtle proportion/blend cues humans are hyper-tuned to read. Blind code-writing plateaus at "toy" | Procedural = stylized tier (validated, §5.2); **faithful tier needs neural reconstruction** (§4.1) |
| **Humans/faces** | people | Uncanny valley at maximum; ethical/identity concerns | **Out of scope v1** — recommend explicitly declining in the router |
| **Complex curved industrial** | cars, sneakers, instruments | Class-A surfaces, decals, transparency | Reconstruction backend or out-of-scope v1; procedural only for boxy/stylized |
| **Thin/soft/deformable** | clothes, flags, plants with large leaves | Cloth dynamics frozen in one photo; thin shells | Stretch goal; card/shell tricks borrow from foliage pack |

### 1.2 The two meanings of "based on that photograph" — the fidelity dial

- **`archetype` fidelity (formcast's heritage):** "make me convincing instances of
  the *kind* of thing in this photo" — seed-varied library, statistics matched
  (proportions, palette, character), not a copy. Right default for trees, rocks,
  scatter props.
- **`faithful` fidelity (new):** "make me a model of *this* object" — silhouette
  and proportions should match the photo within tolerance; one hero model (variants
  still possible via small perturbations). Right default for furniture, products,
  and what most people expect for "my dog".

This becomes a CLI flag (`--fidelity archetype|faithful`) with a per-class default,
and it changes gates (faithful mode adds silhouette-match scoring) and prompts
("match the measured proportions" vs "vary within the family").

> **User decision (2026-06-09): archetype is the quality bar.** Joel: "I care
> less about it looking like the original photo than getting the class of
> objects right." Class credibility — believable structure, mass, materials for
> the KIND — outranks photo resemblance everywhere; `faithful` mode and its
> silhouette-IoU gates drop to a later phase, and judging is re-weighted to
> class credibility first. Furniture's earlier "default faithful" suggestion is
> superseded: everything defaults to archetype.

### 1.3 Scope ladder — the honest quality bars for v1

Declare these openly (README), aim development at them, and gate phases on them:

- **Tier A — photoreal-capable:** trees/shrubs (after Phase 1), rocks, simple-to-
  moderate furniture and props (table/mug/vase/bench grade), at high density with
  textures. Bar: a non-expert says "that's a good 3D model of (that kind of) thing."
- **Tier B — stylized-by-design:** quadrupeds/creatures via procedural pack: clean,
  well-proportioned, game-asset/toy grade, honest about not being photoreal. Bar:
  instantly recognizable species + clean silhouette + no artifacts.
- **Tier C — faithful organics via reconstruction backend (Phase 5):** dogs etc.
  approach photoreal via neural reconstruction + formcast texturing/cleanup. Bar:
  judge prefers it over Tier B 3/3, silhouette IoU vs photo ≥ 0.85.
- **Out of scope v1:** humans, vehicles-as-hero-assets, articulated/rigged output,
  scene reconstruction (multi-object), animation.

### 1.4 Why "LLM writes a generator program" stays the spine

The 2024–2026 research record (§4) now contains strong support for exactly this
design: code is an interpretable, editable, infinitely-variable 3D representation,
and VLM self-critique loops measurably improve it ([LL3M](https://threedle.github.io/ll3m/),
[CADCodeVerify](https://arxiv.org/abs/2410.05340), [EvoCAD](https://arxiv.org/pdf/2510.11631)).
Formcast's differentiators — deterministic seeds, embedded provenance + generator
script inside each .glb, zero heavyweight deps — all come from this choice. Neural
reconstruction doesn't replace it; it slots in as a *backend* for the classes where
code-writing has a low ceiling (§1.1), with formcast still owning texturing,
cleanup, variants, metadata, and evaluation.

---

## 2. Operating manual for Opus (read before every work session)

You will mostly work unattended. These rules keep you fast, cheap, and honest.

### 2.1 Budget & model discipline (the user has limited frontier access)

- **Implementation model:** you (Opus) in Claude Code. **Engine model for bake:**
  the `claude` CLI with `--model opus` (current default; the `opus` alias tracks
  the latest Opus). **Judge model:** `--model sonnet` (cheap, different-enough).
  Never assume Fable-class access for any recurring loop.
- Measured costs to plan around (this machine, 2026-06-09): full authoring bake
  ≈ **$1.3 / 7–8 min** (pass 1 ≈ $0.10/17 s; pass 2 ≈ $0.20–0.39/70–185 s; pass 3
  ≈ $0.5–0.8/175–270 s; one repair ≈ $0.2–0.3/60–75 s); per-variant bake ≈ 0.7 s
  free; isolated single-call experiments ≈ $0.3–0.6; vision measurement ≈ $0.09.
- **The free loop is the default loop:** the saved generator script
  (`outputs/dev/<tag>/<id>.generator.py`) runs standalone —
  `python <gen>.py --image ... --seed 0 --output t.glb` — so texture/geometry/gate/
  renderer iteration costs **zero model calls**. Touch the CLI only when prompts
  change or the refine loop runs.
- Keep a running cost ledger per phase in `EVALS.md`. Soft budgets are listed per
  phase in §7. If a phase projects > 1.5× its budget, stop, log why, and either
  pick the cheaper contingency branch or queue a question for the user.
- Cache what's reusable: pass-1 descriptions keyed by image hash (`--reuse-spec`
  flag, Phase 3) so re-bakes of the same photo skip pass 1.

### 2.2 Research protocol (you do your own research)

Before each phase, run a 30–60 minute WebSearch/WebFetch pass on that phase's
**open questions** (listed per phase in §7). Rules:

- Log findings with links and dates in `EVALS.md` under `## Research — <phase>`.
- Verify any load-bearing claim two ways: a second source, or (better) a local
  empirical test. Licensing claims (model weights, APIs, photos) always get a
  primary-source check (the actual LICENSE file / terms page).
- Time-box: research informs the next experiment; it does not replace it.

### 2.3 Experiment protocol (test before you build)

Pattern proven in this session (§5): *hypothesis → cheapest decisive test →
measure → log → decide.* Concretely:

1. State the hypothesis and the decision it gates in `EVALS.md`.
2. Prefer no-LLM tests (run/modify saved generators, pure-python prototypes).
   If an LLM call is needed, one isolated `claude -p` call with a surgical prompt
   (the T1–T3 harnesses in `outputs/experiments/2026-06-09/` are templates).
3. Render and **look at the result yourself** (Read tool on the PNG).
4. Write the verdict + cost + artifact paths in `EVALS.md` before moving on.

### 2.4 Self-evaluation protocol (your eyes, gates, and a judge)

Four tiers, cheapest first; every quality claim must cite which tier produced it:

- **Tier 1 — gates (free, every iteration):** the objective audit of
  PHOTOREALISM_PLAN §9 generalized per class (§6.6): up-axis, budgets, material
  sanity, alpha discipline, silhouette aspect/IoU, palette ΔE, crown-fill (trees),
  **connected-components** (creatures — would have caught the floating ears in T2),
  dimension spec-match (furniture).
- **Tier 2 — your own eyes (free):** render standard views + a side-by-side
  `[photo | render]` composite; Read them; score a fixed rubric 1–5 in `EVALS.md`:
  silhouette / proportions / surface detail / color-material match / artifacts.
  Always view the **same standard views** so comparisons mean something.
- **Tier 3 — independent VLM judge (~$0.05–0.15/trial):** a *fresh* `claude -p
  --model sonnet` session (never the session that authored the code) gets the
  photo + two unlabeled renders (baseline vs candidate, A/B order randomized per
  trial) and returns forced-choice + rubric JSON. Run 3 trials; candidate wins if
  preferred ≥ 2/3 with no rubric dimension dropping > 1 point. This is your
  promotion test for "did this change actually help."
- **Tier 4 — the user (rare):** per milestone, leave one contact sheet + scorecard
  table ready for them; never block on them.

**Anti-self-deception rules:**
- Freeze baseline renders per benchmark item (`eval/baselines/`); every comparison
  is against the frozen baseline, not your memory.
- Never let the authoring session grade its own output as the promotion test
  (in-session critique is for *iteration*, Tier 3 is for *promotion*).
- Keep a `## Rejected ideas` section in `EVALS.md` so you don't re-try dead ends.
- **Debug the eyes before blaming the model** — in this session, a renderer bug
  (ignored node transforms) made two *correct* models look broken (§5.4). When a
  result looks bizarrely wrong, first verify the harness on a known-good asset.
- Metrics and eyes disagree → eyes win, then fix the metric so it agrees.

### 2.5 When to stop and ask the user (otherwise: decide and log)

Only these: (a) anything requiring a paid account/API key; (b) phase budget
exceeded 1.5× twice; (c) scope/ethics calls (humans in photos, licensed
characters, photos of identifiable private property where it matters); (d) a Tier
A acceptance bar that you've failed three full attempts with all listed
contingencies exhausted. Everything else: pick the default named in this plan, log
the decision in `EVALS.md`, continue.

---

## 3. Where formcast is today (gap analysis)

Verified state (2026-06-09; details in PHOTOREALISM_PLAN §1 and `formcast.log`):

| Capability | State |
|---|---|
| Pipeline plumbing (3 authoring passes + gates + repair loop + resume, metadata embedding, logging) | **Solid** — keep as-is |
| Pass 1 descriptions | Rich and accurate — but prompt says "natural object"; no structured spec; no man-made taxonomy |
| Geometry authoring | Competent code, wrong asks: no envelope/clump craft, no budgets (12.7k vs 73k tri variance run-to-run), Z-up exports (spec violation) |
| Texturing | 256² swatches, detail-destroying tiling, single-tile foliage, no normal maps / vertex colors |
| Viewing/eval | Broken headless (no display; pyglet IndexError); misleading error; **no way to see output where it's made** — fixed by Phase 0 |
| Quality feedback | None — open-loop; quality is a coin flip |
| Classes | Trees work (Tier-B-ish); rocks probably; everything else untested before this session |
| Fidelity | Archetype only |
| Backends | Procedural trimesh only |

The biggest single upgrade remains the same as in PHOTOREALISM_PLAN: **close the
loop** (render → critique → revise) — now generalized to every class and backend.

---

## 4. Prior art survey (web research, 2026-06-09)

### 4.1 Neural single-image → 3D (the reconstruction backends)

The field matured fast; by 2026 open models "genuinely compete with commercial
solutions" ([overview](https://www.pixazo.ai/blog/best-open-source-3d-model-generation-apis),
[tool comparison](https://www.3daistudio.com/3d-generator-ai-comparison-alternatives-guide/best-image-to-3d-tools-2026)).
Two architecture families: multi-view-diffusion + reconstruction (clean topology:
Hunyuan3D, TRELLIS, InstantMesh) and fast feed-forward (TripoSR, Stable Fast 3D —
seconds, lower quality, lighting baked into textures).

| Option | What/license | Relevance to formcast |
|---|---|---|
| **Meta SAM 3D Objects** ([blog](https://ai.meta.com/blog/sam-3d/), [paper](https://arxiv.org/abs/2511.16624)) | Checkpoints + inference code released; single natural image → textured mesh (+ layout); seconds on GPU; SA-3DAO eval set. **SAM 3D Animal** followed ([paper](https://arxiv.org/html/2605.07604)) — directly targets our hardest class | Likely the strongest open faithful-organics path. **Research task P5-R1:** verify license terms + macOS/MPS runnability |
| **Hunyuan3D 2.x** ([2.1 repo](https://github.com/tencent-hunyuan/hunyuan3d-2.1), [2.0 repo](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)) | **Apache-2.0**, weights + training code; PBR texture synthesis | The license-safest backend. **Runs on this Mac** via community forks: [Brainkeys macOS fork](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md) — shape gen works on MPS (2–5 min, ~4–8 GB, **Python 3.11/3.12 venv required**, not 3.13); texturing mostly broken on Mac (nvdiffrast is CUDA-bound) → **formcast supplies textures from the photo — a perfect division of labor.** Also: [MLX port](https://github.com/ZimengXiong/Hunyuan3D-MLX), [MPS port](https://github.com/Maxim-Lanskoy/Hunyuan3D-2-Mac) |
| **TRELLIS / TRELLIS.2** ([repo](https://github.com/microsoft/TRELLIS), [TRELLIS.2](https://github.com/microsoft/TRELLIS.2), [project](https://microsoft.github.io/TRELLIS.2/)) | Open; structured-latent (SLAT/O-Voxel) generation, up to 4B params | Quality reference; likely CUDA-first — check before betting on local use |
| **Hosted APIs:** [Meshy](https://www.meshy.ai/api), [Tripo](https://www.tripo3d.ai/api) ([pricing comparison](https://www.sloyd.ai/blog/3d-ai-price-comparison)) | Credit-based; image→textured mesh ≈ 20–30 credits (~$0.10–0.50/asset); quad remesh, PBR options | Zero-install fallback backend; needs user-approved key + terms check (asset ownership/commercial use) |
| TripoSR / SF3D / SPAR3D, InstantMesh, Unique3D | Open, fast | Lower quality tier; only if the above fail locally |

**Implication:** reconstruction is a *pluggable backend*, default-off, chosen by
the router for `faithful` organics — never a rewrite of formcast.

### 4.2 LLM-writes-3D-code (formcast's own species)

- **[LL3M: Large Language 3D Modelers](https://threedle.github.io/ll3m/)**
  ([paper](https://arxiv.org/abs/2508.08228), [code](https://github.com/threedle/ll3m)) —
  multi-agent LLMs write/debug/refine **Blender** Python; phases = initial creation
  → automatic refinement (code + *visual* self-critique) → user-guided refinement;
  shared code context; retrieval over Blender API docs (BlenderRAG). Validates:
  code-as-representation, visual self-critique, iterative refinement — formcast's
  pass 3.5 is the same idea with a tighter sandbox.
- **3D-GPT / SceneCraft** (cited in LL3M) — LLM agents → Blender scripts for
  scenes; **BlenderMCP** (community, 2025) — Claude driving Blender live.
- **CAD line:** [CADCodeVerify](https://arxiv.org/abs/2410.05340) (VLM visually
  inspects generated CAD and feeds corrective feedback — measurable gains),
  [Text2CAD-Bench](https://arxiv.org/html/2605.18430),
  [EvoCAD](https://arxiv.org/pdf/2510.11631),
  [OpenSCAD LLM benchmark](https://modelrift.com/blog/openscad-llm-benchmark/)
  (LLMs write simple-language CAD more reliably than expressive APIs — keep our
  prompt recipes explicit and simple).
- **[Infinigen](https://infinigen.org/)** ([paper](https://arxiv.org/abs/2306.09310),
  [repo](https://github.com/princeton-vl/infinigen)) — *everything procedural*
  (plants, animals, terrain) at photoreal quality in Blender; plus
  Infinigen Indoors (furniture). **Existence proof for the procedural ceiling** —
  with enough craft, procedural matches photoreal even for creatures. Mine it for
  recipes (their tree/creature generator code is readable Python).
- **Parametric animals:** SMAL (Zuffi et al., CVPR 2017; surveyed in
  [AniMer](https://arxiv.org/abs/2412.00837)) — low-poly quadruped shape space
  (~3.9k verts) spanning cats/dogs/horses/cows; license typically research-only —
  treat as *reference for proportions*, not a dependency.
- **Evaluation:** [3D Arena](https://arxiv.org/abs/2506.18787) (123k human votes;
  automated metrics misalign with human judgment — hence our human-mimicking VLM
  judge + your own eyes), [3DGen-Bench](https://arxiv.org/abs/2503.21745).
- **Retrieval option:** [Objaverse-XL](https://github.com/allenai/objaverse-xl)
  (10M+ assets, ODC-By overall but **per-object licenses vary** — usable subset
  <5M) — backlog idea only (§8 contingencies), license screening required.
- **Blender as a backend:** `bpy` ships as pip wheels per Python version
  ([PyPI](https://pypi.org/project/bpy/), [official builds](https://builder.blender.org/download/bpy/));
  needs its own pinned venv (e.g. py3.11). Phase 6 experiment, not a core dep.

### 4.3 What the survey changes about the old plan

PHOTOREALISM_PLAN was written tree-first and procedural-only. The survey adds:
(1) a **router + backends** architecture instead of one path; (2) a **fidelity
dial**; (3) reconstruction integration as the sanctioned path for faithful
organics; (4) eval methodology grounded in 3D Arena's finding (prefer
preference-judging over pure metrics); (5) Infinigen + LL3M as craft/loop
references. Nothing in the old plan is invalidated; Phases 0–1 below *are* that
plan, with one renderer correction (§5.4).

---

## 5. Evidence: experiments run for this plan (2026-06-09)

All artifacts preserved in `outputs/experiments/2026-06-09/` (gitignored). Costs
are real measured costs on this machine. Use these harnesses as templates.

### 5.1 T1 — Can the engine *measure* a photo by eye? (cost $0.09, 15 s)

One `claude -p --model opus` call with Read on the maple photo, asked for
structured measurements; compared to numpy ground truth:

| Quantity | Vision estimate | Measured truth | Verdict |
|---|---|---|---|
| width/height aspect | 0.78 | 0.84 | good prior |
| crown height fraction | 0.82 | 0.79 | good prior |
| bare-trunk fraction | 0.18 | 0.21 | good prior |
| crown fill | 0.76 | 0.67 | usable, weakest ratio |
| sunlit / shade / trunk RGB | off by ~28–33 per channel | — | **not trustworthy** |
| real height estimate | 9 m | (sanity) | plausible |

**Decisions:** geometric ratios from vision are legitimate fallback priors (±0.1
absolute, so gates use generous tolerances when host measurement is impossible);
**palette must always be pixel-sampled host-side or in-script**, never estimated.

### 5.2 T2 — Procedural quadruped ceiling (cost $0.30, 118 s, first try ran)

One opus call wrote a trimesh dog generator from a prose description + an explicit
recipe (capsule skeleton → `trimesh.boolean.union` → subdivide → Taubin smooth —
possible because `manifold3d` ships with `trimesh[easy]`, verified). Result:
70,656 faces, **watertight unioned body**, correct Y-up stance (paw contacts at
four corners; verified numerically), built in 0.1 s. Render: recognizably a dog,
**toy/balloon grade** — ears attached as floating discs (a connected-components
gate would catch this), balloon-smooth featureless head, lumpy joint bulges.
See `t2_dog_side.png`, `t2_gen.py`.

**Decisions:** (a) procedural creatures are *feasible and cheap* but land in
Tier B (stylized) blind — anatomy craft + refine loop will improve but not reach
photoreal; (b) add `len(mesh.split()) == 1` gate for creature class; (c) Tier C
(faithful animals) goes through the reconstruction backend (Phase 5).

### 5.3 T3 — Procedural furniture (cost $0.58, 270 s, first try ran)

Same harness, round pedestal dining table. Result: **exactly-specified dimensions**
(1.2 m top, 0.75 m height as constants), revolved profiles, four instanced S-curve
feet, both parts watertight, 51k faces. The render is a *genuinely good* table —
near-usable untextured; defects are stylistic (feet too noodly, odd ball at
pedestal base) — precisely what a refine pass fixes. See `t3_table_view.png`,
`t3_gen.py`.

**Decision:** the furniture/man-made pack is **high-confidence**; faithful mode is
realistic for this class procedurally (no neural backend needed).

### 5.4 Meta-lesson — harness bugs masquerade as model failures

Both T2/T3 first renders looked "tipped over"; the models were correct — my
quick renderer read `scene.geometry[...].vertices` (geometry-local) and ignored
node transforms, so the Y-up→Z-up conversion silently didn't apply. Fixed with
`scene.dump()`. **Codified in §2.4: debug the eyes first.** (Also why Phase 0's
renderer must be unit-tested against a known-good transform-bearing GLB.)

### 5.4b Field notes from implementation (running — see EVALS.md and SAMPLES.md)

Learnings from executing Phases 0–1-early on the `experiments` branch
(2026-06-09 evening), folded back into this plan:

- **Description ⇒ geometry, class ⇒ materials/craft.** A v1.1 chair classified
  as `log` still came out chair-shaped (the rich prose description drove the
  geometry pass) but wore charred bark (the class drove texturing). The router
  (§6.3) therefore matters most for *craft/material* selection; the description
  is the main geometry channel. Both channels validated independently.
- **Material-vs-object classification needs an explicit rule.** Pass 1 keyed on
  the marble top and called a console table `white-statuary-marble` → legless
  stone slab. One prompt sentence ("classify by what the WHOLE OBJECT IS, never
  by what it is made of") + the broadened class list fixed it (v1.2: correct
  `furniture`, judge 3/3).
- **The pass-3.5 refine loop worked on first live use** — the model saw its own
  render, opened its critique with "Color is completely wrong", and shipped a
  validated fix. The §6.5 design needs no changes so far.
- **Benchmark acquisition is its own discipline**: automated scoring accepted
  clipart/line-art/B&W museum scans; Openverse `category=photograph` (+ museum
  sources for furniture) plus mandatory eyeball verification is the working
  recipe (EVALS "Rejected ideas").
- **Judge plumbing detail:** subcommands that print JSON must print it as the
  LAST stdout output (log lines otherwise corrupt piped parsing).
- **v1.2 suite outcome (same evening): 4/5 promoted at 3/3 each** (maple,
  table, boulder, tulip); chair rejected 2/3-against for losing turned-wood
  mass — fixed in v1.2.1 (lathe-profile curvature, member thickness, sculpted
  seats, wood grain/wear). The refine loop adopted revisions in 6/6 rounds
  across the suite. Judge-human agreement 2/2 on user-checked items. User
  re-weighted the quality bar to **class credibility over photo fidelity**
  (recorded in §1.2 callout and EVALS Decisions) — faithful mode deprioritized.
- **Ops note:** account session caps kill `claude -p` calls in ~1 s ("exited
  1"); bakes fail fast and cleanly. Serialize bakes (don't parallelize) to
  avoid burning the cap, and expect to re-run items after a reset.

### 5.5 Carried-over evidence (from PHOTOREALISM_PLAN, same day)

Maple baseline numbers (crown fill 47% vs photo 67%; aspect 0.57 vs 0.84; 48%
semi-transparent leaf alpha; bark smear; Z-up bug; broken headless viewer; $1.3 /
7.5 min per bake; 1 repair per run on average; 6× tri-count variance run-to-run).
Verified mechanisms: COLOR_0 + TEXCOORD_0 + normalTexture + MASK export and
round-trip in trimesh 4.12.2.

---

## 6. Target architecture

```
photo ──► Pass 0  preflight (host python): bg mask?, silhouette metrics, palette,
          │        EXIF size hints → PhotoMeasurements (or "unmeasurable")
          ▼
        Pass 1  classify + describe (CLI, vision): taxonomy class, prose
          │     description (rich, as today) + PhotoSpec JSON (parts graph,
          │     proportions w/ confidence, symmetries, materials by region,
          │     suggested fidelity) — cross-checked against Pass 0 numbers
          ▼
        ROUTER  (class, --fidelity, --strategy, available backends)
          │
          ├─► PROCEDURAL (default): Pass 2 geometry ──► Pass 3 texture+export
          │     prompts assembled from: base contract + CLASS CRAFT PACK
          │     (tree | rock | furniture | vessel | creature | generic)
          │     gates: base + class-specific          [Phases 1–4]
          │
          ├─► RECONSTRUCT (faithful organics; flag/backend-gated): local
          │     Hunyuan3D-shape (py311 venv) or SAM 3D or hosted API ──►
          │     formcast post-pass: cleanup/decimate/Y-up/scale ──►
          │     photo-projection + procedural texturing ──► GLB    [Phase 5]
          │
          └─► (either path)
        Pass 3.5  REFINE LOOP: bake probe → soft-render standard views +
          │       texture sheets + [photo|render] composite → metrics →
          │       same-session critique → revised script → re-validate
          ▼
        Pass 4  bake N variants (procedural: seeds; reconstructed: cage-
                deformation + texture-seed variants) + embed metadata
          ▼
        EVAL    `formcast eval`: benchmark manifest → bake/render → gates +
                judge → scorecard.md + contact sheets       [Phase 2]
```

### 6.1 Pass 0 — host-side measurement (new, pure python in formcast.py)

The §B.1 code from PHOTOREALISM_PLAN generalized: background-mask attempt (border-
median tolerance), content bbox/aspect, per-row width profile, fill ratios, k-means
palette (k≈6) over the foreground, dominant-region colors. Output dataclass
`PhotoMeasurements` with a `measurable: bool`. Never fails the bake — degrades to
`unmeasurable` for in-situ photos (then PhotoSpec carries vision priors with wide
tolerances, per T1).

### 6.2 Pass 1 v2 — taxonomy + PhotoSpec

Broaden the prompt ("natural object" → "the primary object"; explicitly allow
man-made things; add `class` values: tree, shrub, plant, grass, cactus, rock,
boulder, cliff, log, stump, **furniture, vessel, tool, lamp, structure, vehicle,
animal, bird, fish, other**). Keep the prose description exactly as rich as today
(it works). Add a second JSON block, PhotoSpec:

```json
{ "class": "furniture", "subtype": "pedestal dining table",
  "fidelity_suggestion": "faithful",
  "symmetry": ["rotational-4", "axial-vertical"],
  "parts": [{"name":"top","shape":"disc","rel_size":{"diameter":1.0,"thickness":0.033}},
            {"name":"pedestal","shape":"turned-column", ...}],
  "proportions": {"height_over_width": 0.62, "confidence": 0.8},
  "materials": [{"region":"all","family":"wood","finish":"satin"}],
  "real_size_estimate_m": {"height": 0.75, "confidence": 0.7},
  "humans_present": false }
```

Pass 0 numbers override PhotoSpec numbers when both exist (T1: vision ±0.1).
`humans_present` → router declines (scope ladder).

### 6.3 Router (small, explicit, logged)

Pure function: `(photospec, args, backends_available) → plan`. Defaults:
tree/shrub/plant/rock/log → procedural+archetype; furniture/vessel/tool/lamp →
procedural+faithful; animal/bird → procedural+archetype (Tier B) unless
`--fidelity faithful` AND a reconstruction backend is configured → reconstruct;
vehicle/structure → procedural+faithful with a logged "low-confidence class"
warning; humans → refuse politely with a clear message. Always log the routing
decision and why at INFO.

### 6.4 Class craft packs (prompt modules + gates, the heart of Phases 1–4)

Each pack = (a) a PASS2 geometry guidance block, (b) a PASS3 material guidance
block, (c) class gates, (d) standard render views for the refine loop. Packs are
text constants in formcast.py (keep single-file), selected by the router, inserted
into the existing instruction templates. **No species/object constants in
formcast** — packs teach *methods* (envelope+clumps; lathe+instancing; capsule-
union+smooth), the photo/description supplies the specifics. Pack specs live in
§7 phase sections.

### 6.5 Refine loop (pass 3.5) — unchanged design, now class-aware

As specified in PHOTOREALISM_PLAN §8, with: per-class standard views (trees:
front/side/closeup; furniture: front/three-quarter/top; creatures: side profile
**first** — silhouette is where anatomy lives — then front/three-quarter); the
metrics table injected per class; `--refine N` default 2. Reconstructed-mesh path
runs the same loop but critique targets the *post-pass* (cleanup/texturing
parameters), not the mesh source.

### 6.6 Gates (audit) — base + per-class

Base: Y-up, base-at-origin, finite, budgets (≤80k/25k/8k tris by density),
embedded PNG textures ≥ the class minimum, metallic=0 unless class says metal,
deterministic-seed warning check. Trees: PHOTOREALISM_PLAN §9 table. Furniture:
spec-match (each PhotoSpec dimension within ±10% in faithful mode), symmetry check
(reflect/rotate vertices, chamfer distance small), connected components ==
declared part count, crisp-edge check (dihedral histogram has a sharp-angle mode).
Creatures: single connected component, stance contact (≥3 ground-contact clusters
for standing quadrupeds), symmetry-across-sagittal-plane tolerance. Rocks: just
base + texture gates.

### 6.7 Reconstruction backend interface (Phase 5)

`formcast.py` gains a thin adapter: `reconstruct(image_path, out_mesh_path) -> None`
implemented by (priority order) `hunyuan3d-local` (subprocess into a dedicated
py3.11 venv; shape-only; document install in README), `sam3d-local` (if P5-R1
research says feasible), `hosted-tripo`/`hosted-meshy` (env-keyed, user-approved).
Post-pass (formcast, pure python): trimesh load → largest component → hole fill →
decimate to budget → align Y-up via PCA + ground plane → scale from
PhotoSpec/Pass 0 → UV via xatlas? **no new dep:** smart-projection UVs (front
photo-projection blended with triplanar procedural continuation for unseen sides)
→ refine loop → metadata embeds `backend` + model/version in provenance.
Variants: seeded smooth cage deformation (numpy trilinear FFD over a 4×4×4
lattice, small amplitudes) + texture seed jitter.

### 6.8 Eval harness (`formcast eval`, Phase 2)

`benchmarks/manifest.json`: `[{id, class, fidelity, photo_url, license,
local_path, notes}]`. Photos cached into gitignored `benchmarks/cache/` by
`formcast eval --fetch`; the manifest (tracked) records source + license for every
item. `formcast eval [--ids ...] [--rebake]` → per item: bake (or reuse last) →
standard renders → gates → Tier-3 judge vs frozen baseline → write
`eval/scorecard.md` + `eval/contact-<id>.png` + append summary row to `EVALS.md`.
This is the regression suite; run it before declaring any phase done.

---

## 7. Phase-by-phase plan

Each phase lists: goal, steps, deliverables, acceptance (with eval tier), budget,
open research questions, and **contingencies**. Work strictly in order; phases 2+
may interleave with ongoing fixes but never skip acceptance.

### Phase 0 — Eyes, spec-compliance, evidence log (budget ≈ $5, 1–2 sessions)

*Goal: you can see, measure, and log everything headlessly.*

1. Implement the soft renderer in formcast.py per PHOTOREALISM_PLAN §4 + Appendix A
   **with the §5.4 fix** (`scene.dump()`), COLOR_0 multiply, up-axis param.
   Unit-test on: maple GLB (Z-up, no transforms), `t2_dog.glb` and `t3_table.glb`
   (Y-up *with* a root transform) — all three must render upright.
2. `view --renderer {auto,gl,soft}` + honest no-display error, per old plan.
3. Y-up authoring requirement + base audit (old plan §5).
4. Create `EVALS.md` (template: §9 of this doc) and freeze baselines: render the
   user's 10 maple GLBs + selftest + T2/T3 into `eval/baselines/`.
5. Implement the Tier-3 judge helper (`_judge(photo, render_a, render_b) -> dict`,
   fresh sonnet session, randomized order) + a tiny self-test (judge an obviously
   better vs worse pair — e.g. maple render vs dog render against the maple photo —
   expect 3/3).

Acceptance: all of the above demonstrated in `EVALS.md` with artifact paths.
Contingencies: renderer too slow on 70k tris → chunked vectorization, 512px
iterate / 1024px final; judge returns malformed JSON → strict-JSON reprompt wrapper
(reuse `_extract_json`); judge can't discriminate the self-test pair → revise
judge prompt (rubric anchors) before any real use.

### Phase 1 — Trees to the photoreal bar (budget ≈ $25, the quality template)

Execute PHOTOREALISM_PLAN §6–§10 exactly (geometry envelope/clump pack, leaf
atlas + bark + COLOR_0 + normal maps, refine loop, gates, variant differentiation),
with acceptance = its §13 **plus** Tier-3 judge ≥ 2/3 vs the frozen baseline on
the maple. This phase produces the *patterns* every other pack copies: craft-pack
prompt structure, gate wiring, refine-loop plumbing, EVALS discipline.

Contingencies (in addition to that doc's): refine loop converges to "APPROVED"
without visible improvement → tighten critique prompt with the metrics table and
explicit "name 3 gaps"; refine oscillates → keep best-of-N by gate score, cap at
`--refine` and move on; cost overrun → drop refine to seed-0-only renders.

### Phase 2 — Eval harness + benchmark suite (budget ≈ $8)

1. Build `formcast eval` + manifest per §6.8.
2. Acquire benchmark photos (research task P2-R1): CC0/PD images, cutout-style
   preferred v1 — sources: Wikimedia Commons (PD/CC0 filters), Openverse,
   museum/gov collections. Target set (~10): maple (have), oak or shrub, boulder,
   round table, wooden chair, ceramic mug, standing dog side-view, bird,
   vase/pot, + one in-situ tree (stretch, exercises the unmeasurable path).
   Record license + URL per item in the manifest; do not commit the images
   themselves (cache dir), keep `inputs/` rule intact.
3. Freeze current-state baselines for every item (even the classes that don't
   work yet — bake them anyway; failures are baselines too).

Acceptance: `formcast eval` runs end-to-end on ≥8 items producing scorecard +
contact sheets; manifest licenses verified. Contingency: can't find a good CC0
photo for a class → generate a stand-in description-only benchmark entry (the
pipeline minus pass-1-vision) and flag it; ask the user to drop in a photo later.

### Phase 3 — PhotoSpec, router, and the two easy packs (budget ≈ $15)

1. Pass 0 preflight + PhotoSpec + router + `--fidelity/--strategy` flags +
   `--reuse-spec` caching (§6.1–6.3). Broaden Pass 1 taxonomy (update CLAUDE.md +
   README scope text in the same change).
2. **Rock pack** (quick win): noise-displaced hull + strata + triplanar bark...
   rock textures; gates: base only + texture floor. Benchmark: boulder item.
3. **Furniture pack** (T3-validated): lathe/revolve + extrude + instancing
   recipes; exact-dims constants from PhotoSpec; symmetry instancing; crisp-edge
   rule (no smoothing filters; ≥64 segments); wood/metal/fabric procedural
   materials sampled from photo palette; faithful-mode silhouette gate
   (front-view IoU ≥ 0.8 against Pass-0 mask after scale-normalize); spec-match
   gate ±10%. Refine views: front/three-quarter/top.
4. Re-run `formcast eval` full sweep.

Acceptance: table + mug + boulder benchmark items pass gates; judge ≥ 2/3 vs their
Phase-2 baselines; routing decisions logged correctly for every benchmark item;
trees unregressed (eval suite). Research questions: P3-R1 best lathe/profile
representation in trimesh (`creation.revolve` API details); P3-R2 IoU alignment
method (simple bbox-normalize vs ICP-lite).
Contingencies: silhouette IoU gate too brittle on perspective photos → relax to
aspect + part-proportion checks, log; revolve API limitations → polygon-soup lathe
(manual ring stitching, same as `_tube`); class misrouting → add a `--class`
override flag for the user and a router confusion-matrix entry in EVALS.

### Phase 4 — Creature pack, stylized tier (budget ≈ $15–20)

The T2 recipe, upgraded with craft (this is a *quality* push, accepting Tier B):

1. PASS2 creature pack: skeleton-graph definition (named joints with
  parent/child + radii), capsule+ellipsoid skinning, **mandatory part-overlap rule**
  (every part must interpenetrate its parent by ≥ 0.5× its radius — kills floating
  ears), boolean union → single component, subdivide+Taubin, sagittal symmetry
  with small asymmetry jitter, side-profile-first proportioning ("design the
  side silhouette before coordinates"), paw/hoof/head secondary masses, tail
  curves. Anatomy guidance: proportion *method* (measure head:body:leg ratios from
  the photo / PhotoSpec) not species constants.
2. PASS3 creature materials: short-fur albedo synthesis (directional noise flow
  along body axis), palette from photo regions, optional fur-fringe alpha cards
  along the silhouette (reuse foliage-card machinery!) at high density only.
3. Gates: single component, stance contacts, symmetry, budget; refine loop with
  side-profile view first; judge rubric emphasizes silhouette + proportions.
4. Benchmark: dog + bird items; 3 refine iterations × up to 2 prompt-pack
  revisions.

Acceptance (Tier B bar): judge scores ≥ 4/5 on "recognizable as the photographed
species" and "clean, artifact-free", ≥ 2/3 preference vs Phase-2 baseline; gates
green. **Explicitly NOT photoreal.**
**Decision point P4-D1:** if after the full budget the dog judge scores < 4/5 →
stop polishing; procedural creatures remain "variant/stylized mode" and faithful
animals go exclusively through Phase 5. Log the decision; don't sink more cost.
Contingencies: boolean union failures on complex part sets (manifold3d edge cases)
→ union incrementally largest-first, fall back to voxel remesh
(`trimesh.voxel.creation.voxelize` + marching via manifold? **research P4-R1**;
if no clean no-new-dep path, keep parts separate but enforce overlap + per-part
watertight and relax the single-component gate to "visually seamless"); smoothing
erases limb definition → smooth body only, union crisp parts after.

### Phase 5 — Reconstruction backend for faithful organics (budget: setup time + ≈$5)

1. **Research first (P5-R1):** SAM 3D Objects license + macOS/MPS feasibility;
  Hunyuan3D mac-fork current state; hosted API terms (asset ownership, commercial
  use). Primary sources; log in EVALS.
2. Local path: dedicated `~/.formcast/venvs/hunyuan3d` (python3.11) per the
  [macOS fork instructions](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md);
  wrapper script `formcast-reconstruct-hunyuan3d` (subprocess; shape-only;
  PYTORCH_ENABLE_MPS_FALLBACK=1; ~2–5 min/shape). The backend adapter + post-pass
  per §6.7 (cleanup, Y-up/scale, photo-projection + procedural texturing, FFD
  variants). **Texture division of labor:** their shape, our textures.
3. Router activation for `--fidelity faithful` + class animal (and as `--strategy
  reconstruct` for any class, e.g. weird furniture).
4. Refine loop on the post-pass; gates: base + single-component + silhouette IoU
  ≥ 0.85 (this is the faithful tier).
5. Hosted fallback only with user-supplied key (ask once, per §2.5).

Acceptance (Tier C bar): dog benchmark faithful-mode run end-to-end headless on
this Mac; judge prefers it over the Phase-4 stylized dog 3/3; IoU gate green;
metadata provenance carries backend identity. Contingencies: local install
unworkable (torch/MPS churn) → document failure in EVALS, pivot to hosted-API
adapter and ask the user for a key; both unavailable → ship v1 with
procedural-only and an honest class-support matrix in README (the capability is
architected; the backend plugs in later); reconstruction mesh quality too poor →
try SAM 3D / TRELLIS variants before giving up (one each, time-boxed).

### Phase 6 — Blender backend experiment (time-boxed: 2 sessions, ≈$5)

Hypothesis: bpy unlocks fur/particles, bevels, proper UV unwrap + AO baking and
raises every pack's ceiling (per LL3M/Infinigen). Experiment only:
py3.11 venv + `pip install bpy` (per [PyPI](https://pypi.org/project/bpy/) /
[official wheels](https://builder.blender.org/download/bpy/)); author one tree and
one table via CLI-written bpy scripts headlessly; render with Cycles CPU; compare
against the trimesh pipeline on cost/quality/robustness; write a go/no-go
recommendation in EVALS for the user. **Do not integrate into formcast.py without
the user's nod** (it's a heavyweight dependency and a second execution sandbox).
Contingency: bpy wheel/python mismatch on this machine → try the official builder
wheels; still no → record as not-viable-now, revisit when python/wheel versions
align.

### Phase 7 — Hardening & product polish (budget ≈ $10)

Full benchmark sweep ×2 (reproducibility: both sweeps pass; seeds byte-stable or
warn-listed); README overhaul (scope, class-support matrix with honest tiers,
flags, costs, examples incl. one furniture example using a benchmark photo);
CLAUDE.md scope refresh; header docstring rewrite; `inspect` shows PhotoSpec +
routing + backend provenance; final demo kit for the user (`eval/scorecard.md` +
contact sheets); prompt-version bump and a CHANGELOG section in README.

Acceptance: the user can run three commands (tree, table, dog) from README verbatim
and get Tier-A/A/B-or-C results; eval suite green twice in a row.

---

## 8. Consolidated contingency playbook (pivot tree)

Use when a phase stalls; always log the branch taken in `EVALS.md`.

```
Quality stalls on a class after 3 iterations + 1 prompt-pack revision
├─ Is the failure visible in renders but not in gates? → add the missing gate
│   (make the failure objective), then iterate once more
├─ Is it a craft-knowledge gap (you don't know what good looks like)?
│   → research detour: find 2–3 reference techniques (Infinigen code, SpeedTree
│     docs, furniture proportion guides), encode into the pack, retry once
├─ Is it a representation ceiling (T2-style: code can't express it)?
│   → demote the class one tier (faithful→archetype, photoreal→stylized), record
│     in class-support matrix; route faithful requests to reconstruction backend
└─ Is it the engine model? → try one run with --model sonnet (sometimes terser =
    more disciplined geometry) and one with the latest opus; keep the better;
    do NOT chase model-of-the-day beyond this

Refine loop not converging
├─ critiques vague → inject metrics table + "name exactly 3 gaps, ranked"
├─ model can't see the defect → add zoomed crop views + [photo|render] composite
├─ fixes one thing, breaks another → keep best-of-N by gate score, not last
└─ still flat after 3 → freeze geometry, refine textures only (cheaper, often
    where the photorealism actually lives)

Infrastructure fights you (booleans, exports, renderer)
├─ FIRST: validate the harness on a known-good asset (§5.4 lesson)
├─ boolean union flaky → incremental union / voxel remesh / relax to overlap rule
├─ trimesh API surprise → write the 20-line manual version (rings/stitching) —
│   never add a dependency to dodge a small function
└─ renderer perf → chunked rasterization, lower iterate-res, cache textures

Cost pressure
├─ switch refine + judge to sonnet; keep authoring on opus
├─ reuse cached pass-1 specs (--reuse-spec); batch experiments per session
└─ stop multi-variant bakes during development (--count 1 until promotion)

Everything in a phase is red and contingencies are exhausted
└─ write a POSTMORTEM block in EVALS.md (what was tried, evidence, your best
    hypothesis), mark the phase BLOCKED, move to the next phase that doesn't
    depend on it, and queue the decision for the user. Never silently lower a bar.
```

---

## 9. EVALS.md template (create in Phase 0)

```markdown
# formcast evidence log (append-only; newest at bottom)

## <date> <phase>.<step> — <short title>
- Hypothesis/goal:
- What ran: (commands, model, flags)            Cost: $X.XX  Wall: Xm
- Artifacts: (paths)
- Gates: (pass/fail table or "n/a")
- Tier-2 (my eyes, rubric 1–5): silhouette X, proportions X, surface X, color X,
  artifacts X — notes
- Tier-3 judge: prefer K/3 vs <baseline-id>, rubric deltas
- Verdict: KEEP/REJECT/PIVOT(branch) — one sentence why
- Next:
```

Plus standing sections: `## Cost ledger` (running totals per phase),
`## Research — <phase>` (links + dates + one-line takeaways), `## Rejected ideas`,
`## Decisions` (router defaults chosen, scope calls, P4-D1 etc.),
`## POSTMORTEMs`.

---

## 10. Risk register (know these going in)

| Risk | Mitigation |
|---|---|
| Judge shares model family with author → correlated blind spots | Randomized A/B, frozen baselines, periodic user spot-check, gates as independent signal |
| Soft renderer ≠ real engines (no PBR response, no AA) | It's a *comparator*, not a beauty render; periodically verify one asset in an external viewer when the user is around; keep materials conservative |
| Prompt-pack changes regress other classes | `formcast eval` full sweep before any promotion; PROMPT_VERSION bump per change |
| manifold3d/boolean robustness on adversarial part sets | §8 infrastructure branch; gates catch silently-broken output |
| Reconstruction licensing/ToS surprises | P5-R1 primary-source check before any integration; provenance records backend |
| Benchmark photo licenses | Manifest records license+URL; CC0/PD only; photos never committed |
| Cost creep from refine/judge loops | Ledger + per-phase soft budgets + §8 cost branch |
| numpy/PIL/trimesh API drift breaks generated code | API-gotchas paragraph in prompts (saves ~1 repair/run); env pins in requirements.txt |
| Scope creep toward "everything" | Scope ladder §1.3 + class-support matrix; out-of-scope list is a feature |

---

## 11. Definition of done (v1 of the general capability)

1. `python formcast.py bake <photo>` on the 10-item benchmark: every item produces
   a valid, Y-up, textured GLB with correct routing, gates green, no crashes —
   including graceful refusal/explanation paths (humans, unmeasurable photos).
2. Tier bars hit: maple ≥ old-plan §13 bar; table/mug/boulder Tier A (judge ≥4/5,
   faithful gates); dog Tier B minimum (≥4/5 stylized rubric), Tier C if Phase 5
   landed (judge prefers over Tier B 3/3, IoU ≥ 0.85).
3. `formcast eval` reproduces the scorecard twice in a row; EVALS.md tells the
   whole story (a stranger could reconstruct every decision).
4. README/CLAUDE.md/docstring reflect reality (scope, matrix, flags, costs);
   PROMPT_VERSION bumped; user demo kit ready; nothing committed without the
   user's go-ahead.

---

## Appendix A — Key sources (accessed 2026-06-09)

Reconstruction: [SAM 3D blog](https://ai.meta.com/blog/sam-3d/) ·
[SAM 3D paper](https://arxiv.org/abs/2511.16624) ·
[SAM 3D Animal](https://arxiv.org/html/2605.07604) ·
[Hunyuan3D-2.1](https://github.com/tencent-hunyuan/hunyuan3d-2.1) ·
[Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) ·
[Hunyuan3D macOS fork](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md) ·
[Hunyuan3D-MLX](https://github.com/ZimengXiong/Hunyuan3D-MLX) ·
[TRELLIS](https://github.com/microsoft/TRELLIS) ·
[TRELLIS.2](https://github.com/microsoft/TRELLIS.2) ·
[2026 open-source comparison](https://www.pixazo.ai/blog/best-open-source-3d-model-generation-apis) ·
[image-to-3D tool guide](https://www.3daistudio.com/3d-generator-ai-comparison-alternatives-guide/best-image-to-3d-tools-2026)

LLM-3D-code: [LL3M project](https://threedle.github.io/ll3m/) ·
[LL3M paper](https://arxiv.org/abs/2508.08228) ·
[LL3M code](https://github.com/threedle/ll3m) ·
[CADCodeVerify](https://arxiv.org/abs/2410.05340) ·
[Text2CAD-Bench](https://arxiv.org/html/2605.18430) ·
[EvoCAD](https://arxiv.org/pdf/2510.11631) ·
[OpenSCAD LLM benchmark](https://modelrift.com/blog/openscad-llm-benchmark/) ·
[Infinigen](https://infinigen.org/) · [Infinigen paper](https://arxiv.org/abs/2306.09310) ·
[Infinigen repo](https://github.com/princeton-vl/infinigen)

Animals/eval/data: [AniMer (SMAL survey)](https://arxiv.org/abs/2412.00837) ·
[3D Arena](https://arxiv.org/abs/2506.18787) ·
[3DGen-Bench](https://arxiv.org/abs/2503.21745) ·
[Objaverse-XL](https://github.com/allenai/objaverse-xl)

APIs/tooling: [Meshy API](https://www.meshy.ai/api) · [Tripo API](https://www.tripo3d.ai/api) ·
[3D AI pricing comparison](https://www.sloyd.ai/blog/3d-ai-price-comparison) ·
[bpy on PyPI](https://pypi.org/project/bpy/) ·
[official bpy wheels](https://builder.blender.org/download/bpy/)

## Appendix B — Experiment artifacts (this session)

`outputs/experiments/2026-06-09/` — `t2_gen.py` + `t2_dog.glb` + `t2_dog_side.png`
(procedural dog, $0.30); `t3_gen.py` + `t3_table.glb` + `t3_table_view.png`
(procedural table, $0.58); `fc_render.py` (transform-aware soft renderer — the
reference implementation for Phase 0, supersedes PHOTOREALISM_PLAN Appendix A's
gather()); maple baseline renders + extracted textures. T1 harness + comparison
table: see §5.1 (script was `/tmp/fc_exp/t1_measure.py`; recreate from §5.1 if
needed — ground truth numbers are in PHOTOREALISM_PLAN §1/Appendix B).
