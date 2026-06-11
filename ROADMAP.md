# formcast Roadmap

Everything future-facing lives here: the 1.0 release checklist, quick wins, the
remaining research/experiment program, and working directions for Opus. The
visual record of results is [`SAMPLES.md`](SAMPLES.md); the technical
explanation of the system is [`TECHNICAL.md`](TECHNICAL.md); the append-only
experiment log is [`EVALS.md`](EVALS.md); standing orders are in `CLAUDE.md`.

> This file replaces the earlier planning documents (`MASTER_PLAN.md`,
> `OPUS_PLAYBOOK.md`, `PHOTOREALISM_PLAN.md`). Their still-open items were
> folded in below; their full texts remain in git history.

## 1. Release 1.0 checklist

Do these in order; each is small. Items marked **(code)** change `formcast.py`
and need a quick smoke test (`bake` one cheap item, or run the free loop) before
commit.

1. ✅ **DONE — (code) Add a project version.** `__version__ = "1.0.0"` near the
   top of `formcast.py`, a `--version` flag on the top-level parser, and print
   it in the `bake` startup log line. Note: `PROMPT_VERSION` (`formcast/1.2.2-cli`)
   is a *different* number — it versions the prompt engine and is embedded in
   each GLB's provenance. Leave it as is; bump it only when prompts change.
   (Any future prefix is safe for up-axis detection, which only treats
   `formcast/1.0*`/`1.1*` as Z-up.)
   *Landed:* `formcast --version` → `formcast 1.0.0`; every bake logs
   `formcast 1.0.0 (prompts formcast/1.2.2-cli) starting bake of …` at INFO.
   `PROMPT_VERSION` left untouched.
2. ✅ **DONE — (code) Detect the session cap and fail clearly.** When the
   `claude` CLI dies, its JSON stdout carries `"api_error_status": 429` and a
   human message like `"You've hit your session limit · resets 4:20pm"`. Before
   this it surfaced as a generic `Claude CLI exited 1 after ~1s`. Now
   `_session_cap_hint()` sniffs both stdout and stderr (before the returncode
   branch, so it wins however the cap manifests) and `ClaudeCLI.ask()` raises
   `FormcastError("Claude session limit reached (resets 4:20pm); re-run this
   bake after the reset…")`. *Landed:* triggers on the limit phrase **or** the
   `api_error_status` 429 field; extracts the `resets …` clause when present;
   unit-tested (incl. no false positive on a script containing a literal `429`)
   plus a hermetic fake-CLI end-to-end (clean message, exit 1, no traceback).
3. ✅ **DONE — (code) Raise the per-call timeout default.** `CLI_TIMEOUT_S` was
   1200, too low for the Tiffany lamp (needed `--cli-timeout 2700` to author its
   geometry). Raised the default to **2700**; the `--cli-timeout` flag still
   overrides. *Landed:* `bake --help` now shows `(default: 2700)`; the lamp no
   longer needs the explicit flag.
4. ✅ **DONE — (code) Pin dependency floors in `requirements.txt`.** The
   authoring prompts hard-assume numpy 2.x (`np.ptp`), Pillow ≥ 10
   (`Image.LANCZOS`), trimesh 4.x. Pinned `numpy>=2`, `Pillow>=10`,
   `trimesh[easy]>=4` (with a comment recording why) so a stale environment
   can't silently mismatch the prompts. *Landed:* file parses and all floors
   are satisfied by the current env (numpy 2.4.6, Pillow 12.0.0, trimesh
   4.12.2). `pygltflib`/`pyglet<2` left as-is.
5. **Confirm the eye-call promotions with the judge** (optional but cheap,
   ~$0 marginal on subscription): 3-trial `formcast judge` for table and tulip
   v1.2.2 vs their old v1.2 champions. Boulder needs no judge — Joel decided it
   directly. Log results in EVALS either way.
6. **Final doc pass** (the CLAUDE.md pre-commit rule): README gallery current,
   SAMPLES sections match champions, this checklist updated.
7. **Tag** `v1.0.0` after Joel reviews and pushes.

## 2. Low-hanging fruit (post-1.0 quick wins, roughly in order of value/effort)

- **Three banked prompt lines** (one sentence each in `formcast.py`; bump
  `PROMPT_VERSION` to `formcast/1.2.3-cli`; verify on the next routine bake —
  do NOT re-bake the chair just to test):
  1. *Matte-dark value lift:* matte/low-sheen near-black surfaces must
     **synthesize** an albedo value range (lift midtones toward the photo's
     ambient bounce), not merely sample sheen — sampling fixed the glossy
     teapot but left the matte chair silhouette-black.
  2. *Repeating detail is texture:* mosaic/leaded glass, scales, brickwork =
     a faceted surface + a painted TEXTURE, never per-tile geometry (the lamp
     timed out authoring tile solids, then succeeded as a textured dome).
  3. *No pole-pinch:* spherical/cylindrical UVs must avoid streaks converging
     at poles — prefer cellular/triplanar-style variation on rocks and other
     noise-textured organics (the v1.2.2 boulder carries a visible pole-pinch).
- **`formcast eval` runner** (no model calls by default): read
  `benchmarks/manifest.json`, re-render every champion, recompute free metrics
  (tri count, extents, base-y, gates), write `eval/scorecard.md`. This is the
  regression net that makes prompt changes safe to land; `--judge` opt-in flag
  for A/B confirmation. Acceptance: one command, all 9 items, < 60 s.
- **Lower `DEFAULT_COUNT`?** The default bakes 10 variants per archetype;
  every real run this month used `--count 2`. Consider 4 (cheap to change;
  needs Joel's nod since it's user-facing behavior).
- **Champion staging flag** (tiny QoL): `formcast bake ... --stage DIR` or a
  small script to copy the `-00.glb` + reference into
  `~/Public/formcast-champions/` instead of the manual `cp` ritual.

## 3. The experiment program (the real quality levers, in priority order)

1. **Foliage/flower silhouette atlas + sun-shade depth — the #1 lever.**
   The evidence: in the v1.2.2 re-bake sweep, *every* class moved except
   foliage (maple was a wash; the azalea's bloom is a blotchy blanket; "leaves"
   are photo-swatch blobs). The fix is class-specific, not a prompt tweak:
   - **Atlas:** a 4×4 atlas of *drawn* leaf-cluster / flower tiles (PIL
     polygons, 4× supersample, crisp binary alpha) instead of photo-swatch
     blobs — distinct silhouettes are what make foliage read at a glance.
   - **Sun/shade depth:** per-card COLOR_0 vertex tints — brighter toward the
     crown top/outside, darker toward the interior/bottom (the maple photo has
     a 4:1 sun/shade luminance range; renders are nearly flat). Target:
     rendered foliage luminance p90/p10 ≥ 2.2.
   - **Crown gaps:** 2–4 deliberate void pockets with glimpses of dark interior
     branches (the photo shows them; the model crowns are too solid).
   Protocol: prototype each idea FREE on a saved champion generator
   (`outputs/dev/v12-maple/*.generator.py`, `v122-azalea/*.generator.py`),
   then encode in the foliage craft pack, one change per bake, judge vs the
   champion.
2. **Rock character:** geometric crack ridges (the Moeraki septarian network
   was present in v1.1 geometry and lost since) + cellular texture variation.
   Free-loop the v1.2.2 boulder generator first.
3. **Creature class — the untested major class.** Acquire a CC0 standing-dog
   side-view photo (Openverse, `license=cc0,pdm`, `category=photograph`;
   verify visually — automated scoring accepts clipart). First bake with the
   creature pack; expectations are Tier-B/stylized; judge by class credibility.
4. **Variant differentiation:** run a champion generator at seeds 0–3, render
   the row (`formcast view ... --save row.png`); if variants are near-clones,
   add explicit seed-variation amplitudes to PASS2 (crown width ±8%, lean ±3°,
   clump count ±20%, palette value ±4%).
5. **Faceted curved surfaces:** tulip petals still show low-poly facets;
   smooth-shading guidance exists but under-delivers — check vertex welding in
   generated code via the free loop.

### Research pointers (read before the matching experiment; log findings in EVALS)

- **Foliage atlas / crown structure:**
  [Infinigen](https://github.com/princeton-vl/infinigen) (procedural photoreal
  nature — read `infinigen/assets/objects/trees/` for concrete branching/clump
  parameters) · SpeedTree-style leaf-card heuristics (search "leaf card cluster
  texture atlas best practices").
- **Refine-loop critique quality:**
  [LL3M](https://github.com/threedle/ll3m) (LLMs writing Blender code with
  visual self-critique — compare their critique prompts with our
  `REFINE_INSTRUCTION`) ·
  [CADCodeVerify](https://arxiv.org/abs/2410.05340) (corrective-feedback
  question lists for geometry).
- **Reconstruction backends (bigger bet below):**
  [Hunyuan3D-2.1 macOS fork](https://github.com/Brainkeys/Hunyuan3D-2.1-mac/blob/main/README_macOS.md) ·
  [TRELLIS](https://github.com/microsoft/TRELLIS) ·
  [SAM 3D](https://ai.meta.com/blog/sam-3d/). Verify licenses against primary
  sources before any integration.

## 4. Bigger bets (propose to Joel before starting)

- **Reconstruction backend for faithful organics.** If procedural hits a
  ceiling on animals/faithful mode: a local image→mesh model (Hunyuan3D-2.1
  mac fork; SAM 3D / TRELLIS as alternates) as a `--strategy reconstruct`
  backend — their shape, our textures. Heavier lift: separate venv, MPS
  quirks, license checks. Research first, primary sources.
- **Blender (`bpy`) backend experiment.** Time-boxed two sessions: author one
  tree + one table via headless bpy (unlocks particles, bevels, proper UV
  unwrap, AO baking), compare cost/quality/robustness vs trimesh, write a
  go/no-go in EVALS. Do not integrate without Joel's nod.
- **Pass-1 description caching** (`--reuse-spec` keyed by image hash) so
  re-bakes of the same photo skip the vision pass.
- **PhotoSpec + router + `--fidelity archetype|faithful` flags:** a structured
  measurement pass (proportions, palette, part dims read off the photo) feeding
  class-specific gates, and an explicit strategy router (procedural vs future
  reconstruction backend) — the formalization of what the prose description
  does informally today. Worth it when faithful mode becomes a real goal;
  archetype mode (Joel's stated priority) doesn't need it.

## 5. Directions for Opus (how to work this roadmap)

Read `CLAUDE.md` first — it is the single source of truth for standing orders
(read all docs + `formcast.py` at session start; refresh docs before every
commit; commit incrementally; never push; invite Joel to review SAMPLES often).
Then:

- **The free loop comes first.** Every bake saves a standalone generator at
  `outputs/dev/<run>/<id>.generator.py`; edit and re-run it for zero model
  calls (`python3 <gen>.py --image <photo> --seed 0 --density high --output
  /tmp/t.glb`), render with `formcast view t.glb --save t.png`, look at it.
  Pay for a bake only when a hand edit visibly helps and you've encoded it as
  a prompt change.
- **One change per bake. Promotion needs evidence:** render the standard views
  (`python3 -c "import formcast; formcast._render_glb_views(...)"`), score
  Tier-2 by eye in EVALS, then `formcast judge <photo> <champion-contact>
  <candidate-contact> --trials 3` — promote on ≥2/3. A direct verdict from
  Joel outranks the judge; your own eyes alone are not enough (they've been
  overruled twice).
- **Document every experiment** (EVALS entry + SAMPLES image row with honest
  what-worked / what-didn't), commit per item so session caps can't lose work.
- **Ops gotchas:** a `claude` call dying in ~1 s with exit 1 is the session
  cap — stop, note it, re-run after the reset (until checklist item 2 makes
  this a clear error). Heavy geometry (mosaic-like) may need `--cli-timeout
  2700`. Never run two bakes at once.
- **Don't chase the chair.** v1.1 stays its champion (Joel's call; the v1.2.2
  checkpoint failed for an understood reason — matte paint). The matte-dark
  prompt line is the only follow-up, and it's validated on *other* objects.

### Champion registry (update after every promotion)

| Item | Champion | Contact sheet |
|---|---|---|
| maple | v1.2 (`outputs/dev/v12-maple/`) | `eval/v12-maple-contact.png` |
| table | v1.2.2 (`outputs/dev/v122-table/`) | `eval/v122-table-contact.png` |
| boulder | v1.2.2 (`outputs/dev/v122-boulder/`) — Joel's call | `eval/v122-boulder-contact.png` |
| tulip | v1.2.2 (`outputs/dev/v122-tulip/`) | `eval/v122-tulip-contact.png` |
| chair | **v1.1** (`outputs/dev/base-chair/`) — accepted outlier, do not chase | `eval/baselines/v11-chair-contact.png` |
| teapot | v1.2.2 (`outputs/dev/v122-teapot/`) | `eval/v122-teapot-contact.png` |
| tiffany-lamp | v1.2.2 (`outputs/dev/v122-lamp/`) — heavy geometry (now within the default 2700 s timeout) | `eval/v122-lamp-contact.png` |
| azalea | v1.2.2 (`outputs/dev/v122-azalea/`) | `eval/v122-azalea-contact.png` |
| pencil | v1.2.2 (`outputs/dev/v122-pencil/`) | `eval/v122-pencil-contact.png` |
