# formcast evidence log (append-only; newest at bottom)

Per MASTER_PLAN §9. Entry template:

```markdown
## <date> <phase>.<step> — <short title>
- Hypothesis/goal:
- What ran: (commands, model, flags)            Cost: $X.XX  Wall: Xm
- Artifacts: (paths)
- Gates: (pass/fail or n/a)
- Tier-2 (my eyes, rubric 1–5): silhouette X, proportions X, surface X, color X, artifacts X — notes
- Tier-3 judge: prefer K/3 vs <baseline-id>, rubric deltas
- Verdict: KEEP/REJECT/PIVOT(branch) — one sentence why
- Next:
```

## Cost ledger
| Phase | Spent | Soft budget |
|---|---|---|
| Pre-plan experiments (2026-06-09, Fable session) | ≈$2.30 | — |
| P2-early acquisition | $0 (no LLM) | — |
| P-baselines (v1.1 bakes) | see entries | ≈$6 |

## Rejected ideas
- Wikimedia Commons full-text File-namespace search for benchmark photos: returns
  book scans/PDFs; thumbor 429s rapid downloads. Use Openverse API instead.
- Openverse without `category=photograph`: returns clipart/illustrations/stylized
  art (rawpixel "png sticker" = often line art; "3 tulips" = posterized art).

## Decisions
- Benchmark v1 = 5 items (maple, tulip, met-console-table, windsor-chair,
  moeraki-boulder); all CC0/local; manifest at `benchmarks/manifest.json`;
  photos cached (gitignored), re-fetchable by URL (+crop derivation for boulder).
- Boulder is intentionally in-situ (no clean cutout exists in the wild) —
  exercises the unmeasurable-background path.
- Maple v1.1 baseline = the user's existing `outputs/broadleaf-maple-*.glb`
  (do not re-bake; frozen).

---

## 2026-06-09 P2-early.1 — Benchmark photo acquisition
- Hypothesis/goal: assemble 4–5 CC0 single-object photos (tree/flower/boulder/
  chair/table) simple enough to be v1 templates, with license provenance.
- What ran: Openverse API (license=cc0,pdm, category=photograph, source=met for
  furniture) + Wikimedia Commons API (fallback; rate-limited). Downloader:
  `benchmarks/fetch_candidates.py`; scorer: `benchmarks/analyze_candidates.py`
  (border-uniformity + blob analysis — doubles as the Pass-0 preflight
  prototype). ~30 candidates fetched, scored, visually verified. Cost: $0.
- Artifacts: `benchmarks/manifest.json`, `benchmarks/cache/picked/{tulip,table,
  chair,boulder}.jpg`, candidates in `benchmarks/cache/candidates/`.
- Findings: automated score alone is insufficient — top scorers included line-art
  and vector clipart (uniform background + single blob ≠ photo). Visual
  verification caught: posterized tulips, woodcut chair, vector desk, B&W
  archival chair, chair-leg detail closeup. Met Museum studio shots (via
  Openverse source=met) are the best furniture source. Final picks:
  | id | class | source quality |
  |---|---|---|
  | maple-tree | tree | bundled, white-bg cutout |
  | tulip | flower | in-situ, bokeh bg, single bloom |
  | met-console-table | furniture | studio grey, ornate (stress case) |
  | windsor-chair | furniture | studio grey, clean |
  | moeraki-boulder | boulder | derived crop, busy beach bg |
- Verdict: KEEP — set is honest: 2 easy-bg, 2 medium, 1 hard-bg.
- Next: bake v1.1 baselines for the 4 new items; expect furniture to expose the
  "natural object"-only taxonomy in PASS1 (documented failure = evidence for
  MASTER_PLAN §6.2).

## 2026-06-09 P0.1 — Soft renderer + VLM judge validated (standalone fcviz.py)
- Hypothesis/goal: headless transform-aware renderer (COLOR_0, MASK, up-axis
  handling) + fresh-session sonnet judge with A/B swap, per MASTER_PLAN P0.
- What ran: `fcviz.py render/views` on maple-00.glb (Z-up, v1.1 metadata),
  t2_dog_yup.glb + t3_table_yup.glb (genuine Y-up re-exports); judge self-test
  maple-render vs dog-render against the maple photo, 2 trials (swap both ways).
  Cost: $0.14 (judge), renders free.
- Artifacts: `fcviz.py` (to be merged into formcast.py), /tmp/p0test/*,
  `outputs/experiments/2026-06-09/{t2_dog_yup,t3_table_yup}.glb`.
- Findings: (1) up-axis auto-detect via embedded provenance.prompt_version works
  (1.1→Z-up, else Y-up). (2) **Up-axis bit me a third time**: the original
  t2_dog.glb/t3_table.glb are Z-up *files* (my earlier harness baked a +90°X
  rotation in before export) — "known-good test assets" must have their
  conventions verified, not assumed; regenerated genuine Y-up copies (`*_yup.glb`).
  (3) Judge self-test: 0/2 candidate wins, correct object-class reasoning in BOTH
  A/B orders — swap logic confirmed; ~$0.07, ~18 s per sonnet trial.
- Verdict: KEEP — Phase-0 components validated; merge into formcast.py after
  baseline bakes finish (not editing formcast.py while bakes re-exec it).
- Next: v1.1 baselines render + freeze; then v1.2 overhaul.

## 2026-06-09 P-baselines.1 — v1.1 baselines on the new benchmark items
- Hypothesis/goal: freeze "before" state of current prompts across classes;
  expected the nature-only PASS1 taxonomy to fail on furniture.
- What ran: `bake <item> --count 2` for tulip/boulder/chair/table with frozen
  v1.1 prompts (sequential background loop). Costs in formcast.log (~$1.3-1.6
  each, 1 repair typical).
- Artifacts: `outputs/dev/base-*/`, frozen sheets `eval/baselines/v11-*.png`.
- Findings so far (tulip, boulder, chair pass-1):
  - **tulip** (`white-tulip`/plant, 7.5k tris): recognizable bloom + stem;
    defects: faceted petals, stem striped PURPLE (texture crop pulled bokeh
    background), invented floating leaf scraps, umbrella-like basal leaf.
    Tier-2 rubric: silhouette 3, proportions 4, surface 2, color 2, artifacts 2.
  - **boulder** (`spherical-concretion-boulder` — correctly recognized the
    Moeraki concretion): shape+cracks concept right; texture ruined by blind
    crop boxes sampling ocean/foam — dark mud with blue/red blotches.
    Tier-2: silhouette 4, proportions 4, surface 2, color 1, artifacts 2.
  - **chair**: PASS1 forced `class='log'` for a correctly-identified
    `windsor-armchair` — the predicted taxonomy failure, verbatim evidence for
    MASTER_PLAN §6.2 (bake continued; geometry quality TBD).
- Verdict: baselines confirm the plan's diagnosis: in-situ photos break blind
  crop-box texture sampling; taxonomy must broaden; palette must be measured.
- Next: v1.2 wiring (already staged as unused functions), re-bake, A/B judge.
- Addendum (chair/table renders): chair v1.1 is structurally a real Windsor
  chair despite class='log' (rich description drove geometry; wrong class drove
  bark-like charred texturing); table v1.1 is a legless mottled stone slab
  (class='white-statuary-marble'). **Learning: description ⇒ geometry, class ⇒
  materials/craft — both channels must be right.** Tier-2 table: 1/1/2/1/3.

## 2026-06-09 P-v12.1 — v1.2 table: first full A/B promotion
- Hypothesis/goal: v1.2 (taxonomy + manmade craft pack + texture rules + refine
  loop) fixes the furniture failure mode end-to-end.
- What ran: `bake table.jpg --count 2 --refine 1` (831 s, ~$2.3 incl. refine);
  judge 3 trials sonnet (~$0.21). Cost: ≈$2.5.
- Artifacts: `outputs/dev/v12-table/`, `eval/v12-table-*.png`, SAMPLES.md entry.
- Gates: all passed in-bake (validation + audit; no repairs needed this run).
- Tier-2 (my eyes): silhouette 4, proportions 4, surface 3, color 2.5,
  artifacts 4 — real two-shelf console with cameo medallion; wood too
  grey-mauve, no gilt on "ormolu", veining smudgy.
- Tier-3 judge: **v1.2 preferred 3/3** vs frozen v1.1 baseline; candidate
  rubric ≈ 4/3.5/3/3/3.5 vs baseline ≈ 1/1/1.3/1.3/3.
- Refine-loop first live use: model critiqued its own render ("Color is
  completely wrong"), revised, revision validated and adopted (169.6 s round).
- Verdict: KEEP — promotes v1.2 for furniture; the craft→render→judge loop is
  validated end-to-end exactly as MASTER_PLAN designed.
- Next: chair/boulder/tulip/maple as the suite completes; journal in SAMPLES.md.

## 2026-06-09 P-v12.2 — v1.2 chair: first judge REJECTION (kept honestly)
- What ran: `bake chair.jpg --count 2 --refine 1` (~14 min; refine round fixed
  seat shape per its own critique); judge 3 trials. Suite items 3-5 (boulder/
  tulip/maple) died in ~1 s each — the user's session usage limit hit mid-suite
  ("Claude CLI exited 1 after 1.2s"); re-launched after reset.
- Tier-2 (my eyes): scored v1.2 ahead (cleaner comb-back structure, correct
  class/materials channel).
- Tier-3 judge: **v1.1 preferred 2/3.** Reasons: v1.1 has turned-wood MASS —
  bulbous ball feet, chunky balusters, sculpted seat; v1.2 reads thin/wiry,
  flat-disc seat. The one v1.2 win cited the comb-back silhouette + scrolled
  ears.
- Verdict: REJECT promotion for chair (protocol ≥2/3). **The judge overruled my
  own eyes — anti-self-deception machinery working as designed.** Learning:
  "crisp edges / no smoothing" guidance under-serves *turned* furniture; v1.2.1
  manmade pack must add: pronounced turned-profile curvature (bulbs/coves/rings
  from the photo), sculpted-not-flat seats (displaced slab), member thickness
  measured off the photo, and a no-floating-parts rule (+audit).
- Next: apply v1.2.1 manmade craft edits AFTER the retry suite finishes (prompt
  edits are unsafe mid-suite), re-bake chair only, re-judge.

## 2026-06-09 P-v12.3 — v1.2 boulder promoted 3/3; judge-human calibration 2/2
- What ran: retry `bake boulder.jpg --count 2 --refine 1` (359.7 s; refine
  adopted a revision); judge 3 trials (~$0.21). The earlier suite attempt died
  at pass 3 with "Claude CLI exited 1 after 1.2 s" — the account session cap;
  documented as an ops failure mode (bakes fail fast and cleanly, no corruption).
- Tier-3 judge: **v1.2 preferred 3/3**; color/material 4 vs 1 — the
  anti-contamination texture rules fixed the ocean-blue blotches.
- Honest regression: lost v1.1's septarian crack ridges (distinctive Moeraki
  character); surface reads concrete-ish in closeup. Queue with texture-fidelity
  iteration ("keep the character features the photo shows" prompt line).
- **Tier-4 calibration:** Joel independently judged "chair v1.1 far better,
  table v1.2 far better" — matches the automated judge on both items (including
  the chair, where the judge overruled my Tier-2 scoring). Judge-human
  agreement 2/2 so far.
- Verdict: KEEP boulder promotion; raise judge trust; add per-item "what got
  worse" tracking to the journal (done).
