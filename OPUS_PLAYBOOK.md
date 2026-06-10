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

- **Read everything first.** Start each session by reading every Markdown file
  and `formcast.py` in full (a CLAUDE.md standing order). Don't act on a stale
  summary — the champions and the open questions live in these docs.
- **Pacing, not budgeting.** Don't fuss over token or dollar cost — Joel runs on
  a subscription, and a long, token-heavy session is fine when the work genuinely
  needs it. Just keep making real progress; don't spin. The one hard constraint
  is the account **session cap**: when a bake's log shows
  `Claude CLI exited 1 after ~1s`, the cap is hit — STOP, note it in EVALS, wait
  for the reset, and re-run only the failed items. Never run two bakes at once
  (you lose attribution and hammer the machine). A bake takes ~8–17 min wall;
  serialize them.
- **The free loop comes first.** Every bake saves its generator at
  `outputs/dev/<run>/<id>.generator.py`. You can edit that script directly and
  re-run it without another bake (no model call):
  `python3 <gen>.py --image <photo> --seed 0 --density high --output /tmp/t.glb`
  Prototype texture/geometry ideas there; only once a hand edit visibly helps do
  you encode it as a prompt change and spend a bake. This is about fast iteration
  and clean attribution — not thrift.
- **One change per bake.** Otherwise you can't attribute the result.
- **Promotion protocol.** Render with
  `python3 -c "import formcast; formcast._render_glb_views(...)"` (see step 1
  for the exact snippet), then judge against the CURRENT CHAMPION (table
  below): `python3 formcast.py judge <photo> <champion-contact> <candidate-contact> --trials 3`.
  Promote only on ≥2/3. Tie/loss → log honestly, fix or pivot. **Never judge
  your own work by eye alone — your eyes scored the v1.2 chair ahead and the
  judge (and Joel) disagreed.** A human verdict from Joel outranks the judge.
- **Document every step**: EVALS.md entry (template at the top of that file),
  SAMPLES.md image row + verdict (Joel watches this file — commit the PNGs you
  reference!), then `git commit` (you have standing permission on this branch;
  follow the existing commit-message style; never push).
- **Refresh docs + code comments before every commit** (a CLAUDE.md standing
  order): re-read and update README, this playbook, SAMPLES.md, EVALS.md, and any
  stale inline comments in `formcast.py` in the *same* commit as the change.
- **Invite Joel's eyes regularly** (his standing direction — user review is
  welcome, not rare). At milestones, and whenever a result is interesting or
  you're unsure, proactively ask Joel to look at `SAMPLES.md` and its
  contact-sheet links and comment. Keep working while you wait — don't block —
  but ask often; his verdict outranks the judge and has recalibrated this effort
  twice (class credibility; the chair / simplicity-over-detail).
- **Class credibility over photo fidelity** (Joel's standing direction): the
  bar is "a convincing instance of this KIND of object", not resemblance to
  the exact photo.
- **Simplicity and geometric essence beat detail-chasing** (Joel, on the chair,
  2026-06-10): a clean model that nails the essential masses and proportions of
  the kind beats a busier one that chases fine surface or geometric detail —
  *"what I like about [the v1.1 chair] is that it's simple and it captures the
  geometric essence."* When a change adds detail at the cost of a clean, legible
  silhouette and clear masses, that is the wrong direction. Reach for the
  simplest geometry that reads unmistakably as the kind.

### Champion registry (update after every promotion)

| Item | Champion | Contact sheet |
|---|---|---|
| maple | v1.2 (`outputs/dev/v12-maple/`) | `eval/v12-maple-contact.png` |
| table | v1.2 (`outputs/dev/v12-table/`) | `eval/v12-table-contact.png` |
| boulder | v1.2 (`outputs/dev/v12-boulder/`) | `eval/v12-boulder-contact.png` |
| tulip | v1.2 (`outputs/dev/v12-tulip/`) | `eval/v12-tulip-contact.png` |
| chair | **v1.1** (`outputs/dev/base-chair/`) — confirmed by Joel 2026-06-10 | `eval/baselines/v11-chair-contact.png` |
| teapot | v1.2.2 (`outputs/dev/v122-teapot/`) — first champion, 2026-06-10 | `eval/v122-teapot-contact.png` |
| tiffany-lamp | — (never baked) | — |
| azalea | — (photo acquired 2026-06-10, CC0 → `benchmarks/cache/picked/azalea.jpg`; first bake pending) | — |

## 1. Chair verdict — DECIDED by Joel: v1.1 stays champion

Joel gave a direct human verdict (2026-06-10): **the v1.1 chair is the best.**
*"I still think the 1.1 chair is the best. I see that 1.2.1 is trying to capture
geometry details like the swirls on the top. What I like about 1.1 is that it's
simple and it captures the geometric essence."* A human verdict outranks the
judge, so the chair question is closed: **v1.1 is and stays the chair champion.**
Do **not** re-bake the chair to try to win it back.

The lesson generalizes — see step 3: v1.2 → v1.2.1 chased mass and fine detail
(turned swirls, heavy balusters) and went silhouette-black; that was the wrong
direction. The win condition for the chair was the *simple, legible essence* that
v1.1 already had.

Optional, calibration only (NOT a gate): run the judge once to see whether the
automated A/B agrees with Joel — a third judge–human data point (currently 2/2).
It changes nothing about the champion.

```bash
python3 formcast.py judge benchmarks/cache/picked/chair.jpg \
  eval/baselines/v11-chair-contact.png eval/v121-chair-contact.png \
  --trials 3 --log-file /tmp/fcj.log 2>/dev/null
```

(The JSON is the last stdout output; `candidate_wins` counts B = v1.2.1. Log it
in EVALS as a calibration check; v1.1 remains champion regardless of the result.)

## 2. First bakes: teapot, tiffany-lamp, and azalea (no champion yet)

Serialize these — one bake at a time (§0).

```bash
python3 formcast.py bake benchmarks/cache/picked/teapot.jpg \
  --out-dir outputs/dev/v121-teapot --count 2 --refine 1
python3 formcast.py bake benchmarks/cache/picked/tiffany-lamp.jpg \
  --out-dir outputs/dev/v121-lamp --count 2 --refine 1
python3 formcast.py bake benchmarks/cache/picked/azalea.jpg \
  --out-dir outputs/dev/v121-azalea --count 2 --refine 1
```

Then render each (this is the standard render snippet for ALL steps):

```bash
python3 - <<'EOF'
import sys, glob
sys.path.insert(0, ".")
import formcast
from pathlib import Path
for run, stem in [("v121-teapot", "v121-teapot"), ("v121-lamp", "v121-lamp"),
                  ("v121-azalea", "v121-azalea")]:
    glbs = sorted(glob.glob(f"outputs/dev/{run}/*-00.glb"))
    if glbs:
        print(formcast._render_glb_views(Path(glbs[0]), Path("eval"), stem)[-1])
EOF
```

View the contact PNGs yourself (Read tool); write Tier-2 rubric scores
(silhouette/proportions/surface/color/artifacts, 1–5) in EVALS. No judge
needed (no champion) — these become the first champions. Add SAMPLES.md rows
(photo thumbnails already exist: `eval/photos/teapot.jpg`,
`eval/photos/tiffany-lamp.jpg`, `eval/photos/azalea.jpg`). Commit renders +
journal.

Expected: teapot should do well (revolve body + handle = the manmade pack's
home turf). The lamp is a deliberate stretch (mosaic glass) — a mediocre lamp
is fine; document what specifically fails (likely the stained-glass texture).
The azalea is the foliage pack on a non-tree shrub; the bar is class credibility
(a believable rounded flowering shrub — the dome silhouette + bloom-over-foliage
texture are what sell it). Palette sampling should target the magenta flowers +
green leaves, not the green hedge backdrop. CC0 (WordPress Photo Directory), so
no license caveat.

## 3. Chair lesson → pipeline principles (NO chair re-bake)

> **STATUS: encoded 2026-06-10 as `formcast/1.2.2-cli`.** Both lessons are now in
> `formcast.py` (PASS2 "simplicity/essence first" bullet; manmade turned-part
> temper; PASS3 very-dark-finish sampling). Still to do: **validate on the next
> bakes** (step 2) — watch that furniture keeps its mass while shedding fussiness,
> and that dark surfaces keep a visible value range. See EVALS P-122.1.

The chair is closed (step 1), but it taught two things worth encoding into the
prompts so *other* objects benefit. Study-the-champion is still the method —
**read the code that won**:

1. Read `outputs/dev/base-chair/windsor-armchair.generator.py` (v1.1 champion):
   note how *little* it does — simple turned masses, one value-rich dark wood
   swatch (it accidentally used bark-style sampling), a legible silhouette. That
   simplicity is *why* Joel prefers it.
2. Read `outputs/dev/v121-chair/comb-back-windsor-armchair.generator.py`: see
   where v1.2.1 went wrong — it piled on swirl/turning detail and sampled the
   photo's near-black paint as one flat color, so it reads as a black blob.

Encode the lessons generically (these help every class — not the chair):

- **Simplicity / essence** (the headline lesson, Joel's standing direction):
  add a line to `CRAFT_PASS2` / PASS2 that the goal is the *simplest geometry
  that reads unmistakably as the kind* — prioritize clean, legible essential
  masses and a clear silhouette over fine surface or turned detail; never add
  geometric detail that muddies the silhouette.
- **Dark materials still need value variation** (a real, general bug): very
  dark painted/finished objects must still show albedo value variation — sample
  the photo's highlight/sheen zones, not just the average, and modulate albedo
  with grain-scale noise — or they render as black silhouettes. One sentence in
  the PASS3 material rules.

Bump `PROMPT_VERSION` to `formcast/1.2.2-cli` (up-axis detection only keys on
1.0/1.1 prefixes — safe). **Do not re-bake the chair to chase a win.** Verify
these changes on the *next* objects you bake (teapot / lamp / azalea), where
simpler-is-better and dark-material-variation both apply. For a regression
check, re-render an existing champion after the prompt change lands in code;
never spend a bake trying to beat v1.1's chair.

## 4. Make the eval suite one command (engineering, no bake needed)

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
   (already in v1.2.1) — needs one re-bake + judge.
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

Per MASTER_PLAN §2.5: paid API keys/accounts; scope or ethics calls; or three
full failed attempts with contingencies exhausted (write the POSTMORTEM first).
**Cost/budget is not a stopping reason** — Joel runs on a subscription.
Otherwise: decide, log the decision in EVALS, continue.
