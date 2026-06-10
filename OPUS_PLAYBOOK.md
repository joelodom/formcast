# Opus Playbook — continuing the photo→3D experiments

You are Opus, continuing an experiment program on the `experiments` branch.
**The goal is actual, judged improvement of the 2D→3D bake quality**, one small
change at a time. This playbook is written so every step is a concrete action
with exact commands, expected outputs, and a decision rule. Work the steps in
order; each is sized to one focused work session or less.

Read first (10 min): `SAMPLES.md` (the visual journal Joel watches — you must
keep it updated), `EVALS.md` (append-only evidence log + Decisions),
`MASTER_PLAN.md` §1–2 + §5.4b (architecture, operating manual, field notes).
`PHOTOREALISM_PLAN.md` is the deep spec for tree quality (step 5 uses it).

## 0. Standing rules (apply to every step)

- **Budget discipline.** A bake ≈ $1.5–2.5 / 8–17 min (opus authoring +
  `--refine 1`). A judge ≈ $0.21 (3 sonnet trials). NEVER run two bakes at
  once. Joel's account hits session caps: when a bake's log shows
  `Claude CLI exited 1 after ~1s`, STOP — the cap is hit; note it in EVALS,
  wait for reset, re-run only the failed items.
- **The free loop comes first.** Every bake saves its generator at
  `outputs/dev/<run>/<id>.generator.py`. You can edit that script directly and
  re-run it for ZERO model cost:
  `python3 <gen>.py --image <photo> --seed 0 --density high --output /tmp/t.glb`
  Prototype texture/geometry ideas there; only when a hand edit visibly helps
  do you encode it as a prompt change and pay for a bake.
- **One change per bake.** Otherwise you can't attribute the result.
- **Promotion protocol.** Render with
  `python3 -c "import formcast; formcast._render_glb_views(...)"` (see step 1
  for the exact snippet), then judge against the CURRENT CHAMPION (table
  below): `python3 formcast.py judge <photo> <champion-contact> <candidate-contact> --trials 3`.
  Promote only on ≥2/3. Tie/loss → log honestly, fix or pivot. **Never judge
  your own work by eye alone — your eyes scored the v1.2 chair ahead and the
  judge (and Joel) disagreed.**
- **Document every step**: EVALS.md entry (template at the top of that file),
  SAMPLES.md image row + verdict (Joel watches this file — commit the PNGs you
  reference!), then `git commit` (you have standing permission on this branch;
  follow the existing commit-message style; never push).
- **Class credibility over photo fidelity** (Joel's standing direction): the
  bar is "a convincing instance of this KIND of object", not resemblance to
  the exact photo.

### Champion registry (update after every promotion)

| Item | Champion | Contact sheet |
|---|---|---|
| maple | v1.2 (`outputs/dev/v12-maple/`) | `eval/v12-maple-contact.png` |
| table | v1.2 (`outputs/dev/v12-table/`) | `eval/v12-table-contact.png` |
| boulder | v1.2 (`outputs/dev/v12-boulder/`) | `eval/v12-boulder-contact.png` |
| tulip | v1.2 (`outputs/dev/v12-tulip/`) | `eval/v12-tulip-contact.png` |
| chair | **v1.1** (`outputs/dev/base-chair/`) | `eval/baselines/v11-chair-contact.png` |
| teapot | — (never baked) | — |
| tiffany-lamp | — (never baked) | — |

## 1. Chair verdict (one judge call, ~$0.21)

The v1.2.1 chair is baked and rendered (`eval/v121-chair-contact.png`) but the
session cap killed the judge. Run:

```bash
python3 formcast.py judge benchmarks/cache/picked/chair.jpg \
  eval/baselines/v11-chair-contact.png eval/v121-chair-contact.png \
  --trials 3 --log-file /tmp/fcj.log 2>/dev/null
```

(The JSON is the last stdout output; `candidate_wins` counts B = v1.2.1.)

- **≥2/3:** promote v1.2.1 as chair champion; update the registry above,
  SAMPLES.md chair section, EVALS entry; commit.
- **≤1/3:** go to step 3 (study-the-champion) before any re-bake. Likely
  failure mode (visible in the render): the chair is silhouette-black — mass
  improved but material variation didn't materialize.

## 2. First bakes: teapot and tiffany-lamp (~$2–3 + ~$0 judge — no champion yet)

```bash
python3 formcast.py bake benchmarks/cache/picked/teapot.jpg \
  --out-dir outputs/dev/v121-teapot --count 2 --refine 1
python3 formcast.py bake benchmarks/cache/picked/tiffany-lamp.jpg \
  --out-dir outputs/dev/v121-lamp --count 2 --refine 1
```

Then render each (this is the standard render snippet for ALL steps):

```bash
python3 - <<'EOF'
import sys, glob
sys.path.insert(0, ".")
import formcast
from pathlib import Path
for run, stem in [("v121-teapot", "v121-teapot"), ("v121-lamp", "v121-lamp")]:
    glbs = sorted(glob.glob(f"outputs/dev/{run}/*-00.glb"))
    if glbs:
        print(formcast._render_glb_views(Path(glbs[0]), Path("eval"), stem)[-1])
EOF
```

View the contact PNGs yourself (Read tool); write Tier-2 rubric scores
(silhouette/proportions/surface/color/artifacts, 1–5) in EVALS. No judge
needed (no champion) — these become the first champions. Add SAMPLES.md rows
(photo thumbnails already exist: `eval/photos/teapot.jpg`,
`eval/photos/tiffany-lamp.jpg`). Commit renders + journal.

Expected: teapot should do well (revolve body + handle = the manmade pack's
home turf). The lamp is a deliberate stretch (mosaic glass) — a mediocre lamp
is fine; document what specifically fails (likely the stained-glass texture).

## 3. Chair material fix (only if step 1 verdict was ≤1/3)

The information you need is already on disk — **read the champion's code**:

1. Read `outputs/dev/base-chair/windsor-armchair.generator.py` (v1.1 champion)
   — find how it textures wood (it accidentally used bark-style swatch
   sampling, giving value-rich dark wood).
2. Read `outputs/dev/v121-chair/comb-back-windsor-armchair.generator.py` —
   find why it's flat near-black (likely: sampled the photo's dark paint as a
   single color; no grain/wear modulation despite the prompt line).
3. **Free-loop prototype:** edit the v1.2.1 generator directly — add value
   variation to the wood albedo (e.g. multiply by 0.85–1.25 low-frequency
   noise + lighten edges/highlights toward the photo's sheen color), re-run
   the script (zero cost), re-render, eyeball. Iterate until the front render
   shows visible turning detail instead of silhouette.
4. Encode what worked as 1–2 sentences in `CRAFT_PASS2["manmade"]` or the
   PASS3 wood-material bullet in `formcast.py` (keep it generic: "very dark
   painted objects still need visible value variation — sample the photo's
   highlight/sheen zones, not just the average; modulate albedo with
   grain-scale noise"). Bump `PROMPT_VERSION` to `formcast/1.2.2-cli`
   (up-axis detection only cares about 1.0/1.1 prefixes — safe).
5. One re-bake (`--out-dir outputs/dev/v122-chair`), render, judge vs v1.1.
   If it STILL loses: write a POSTMORTEM in EVALS (include both generators'
   relevant snippets), leave v1.1 as champion, move on. Do not iterate a third
   time without new information.

## 4. Make the eval suite one command (engineering, $0 model cost)

Implement `formcast eval` per MASTER_PLAN §6.8, minimal version:

- Read `benchmarks/manifest.json`; for each item with a champion, re-render
  champion + (optionally) latest candidate; recompute the free metrics
  (tri count, extents, base-y; crown-fill for the maple via the
  PHOTOREALISM_PLAN Appendix B.1 snippet); write `eval/scorecard.md` with a
  table (item, champion, faces, gates pass/fail, last judge result, links).
- No model calls by default; `--judge` flag opt-in.
- Update README (one short paragraph + example) — standing order: README must
  track behavior in the same change. Commit.

Acceptance: `python3 formcast.py eval` produces `eval/scorecard.md` listing
all 7 items in <60 s. This is your regression net for every later change.

## 5. Tree depth iteration (the flagship; PHOTOREALISM_PLAN §7 is the spec)

Maple v1.2 won 3/3 but is judged 4/5, not 5/5: crown too uniformly solid, the
photo's 4:1 sun/shade depth is missing, leaves are blobs not silhouettes.
Three sub-experiments, STRICTLY one at a time, each: free-loop prototype on
`outputs/dev/v12-maple/broadleaf-maple-tree.generator.py` → encode in the
foliage pack → one bake → judge vs v1.2 maple champion → journal → commit.

5a. **COLOR_0 sun/shade gradient** (the machinery exists and exports — see
    MASTER_PLAN Appendix C): per-card vertex tint = brighter toward crown
    top/outside (sample the photo's sunlit foliage color), darker toward
    interior/bottom (shade color). Target: rendered foliage luminance
    p90/p10 ≥ 2.2 (measure on the front render with numpy).
5b. **Crown gaps + branch glimpses**: 2–4 deliberate void pockets in the card
    distribution + make interior branches slightly visible through them
    (the photo shows dark struts). Watch the crown-fill metric — stay within
    ~12 points of the photo's 67%.
5c. **Leaf-silhouette atlas** (PHOTOREALISM_PLAN §7.1 verbatim): 4×4 atlas of
    drawn leaf-cluster tiles (PIL polygons, supersample, crisp alpha) instead
    of photo-swatch blobs. This is the largest texture win available.

## 6. Research detours (zero model cost; 1–2 h each; do between bakes)

Log findings + links in EVALS `## Research`; turn each into 1–3 candidate
prompt lines and queue them. Verify claims against the actual source.

- **Infinigen** (Princeton, procedural photoreal nature):
  https://github.com/princeton-vl/infinigen — read
  `infinigen/assets/objects/trees/` (branching + leaf placement parameters)
  for concrete crown/clump numbers to steal for the foliage pack.
- **LL3M** (LLMs writing Blender code with visual self-critique):
  https://github.com/threedle/ll3m + https://threedle.github.io/ll3m/ — read
  their critique-prompt wording; compare with our `REFINE_INSTRUCTION`
  (formcast.py); steal anything that makes critiques more concrete.
- **SpeedTree-style leaf cards**: search "leaf card cluster texture atlas
  speedtree best practices" — extract card-size/cluster-count heuristics for
  the foliage pack.
- **CADCodeVerify** (https://arxiv.org/abs/2410.05340): their corrective-
  feedback question list for geometry — candidate refine-prompt additions.

## 7. Backlog (in priority order, after the above)

1. Variant differentiation check: run a champion generator with seeds 0..3,
   render the row (`formcast view outputs/dev/v12-maple/ --save row.png`),
   judge-by-eye whether variants differ meaningfully; if near-clones, add
   seed-variation requirements to PASS2 (MASTER_PLAN WS6).
2. Boulder character: restore crack ridges via the character-features line
   (already in v1.2.1) — needs one re-bake + judge when budget allows.
3. Tulip facets: smooth-shading line is in v1.2.1 — verify on the next tulip
   bake (cheap: piggyback whenever tulip is re-baked for another reason).
4. Creature class: acquire a CC0 standing-dog side-view photo (use
   `benchmarks/fetch_candidates.py` pattern + Openverse `category=photograph`;
   verify visually — beware clipart), add to manifest, first bake with the
   creature pack. Expect Tier-B/stylized; judge by class credibility.
5. New classes from MASTER_PLAN P3 as photos become available (mug, bench,
   birdhouse — keep them SIMPLE).
6. Phase 5 research (reconstruction backend for faithful organics) — read
   MASTER_PLAN §6.7/P5 first; this is a bigger lift, propose to Joel before
   spending.

## 8. When to stop / ask Joel

Per MASTER_PLAN §2.5: paid API keys; phase budget 1.5×-exceeded twice; scope
calls; or three full failed attempts with contingencies exhausted (write the
POSTMORTEM first). Otherwise: decide, log the decision in EVALS, continue.
