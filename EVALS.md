# formcast evidence log (append-only; newest at bottom)

References to `MASTER_PLAN` / `OPUS_PLAYBOOK` / `PHOTOREALISM_PLAN` in older
entries point at retired planning docs (folded into `ROADMAP.md` 2026-06-11;
full texts in git history). Entry template:

```markdown
## <date> <phase>.<step> — <short title>
- Hypothesis/goal:
- What ran: (commands, model, flags)            Wall: Xm
- Artifacts: (paths)
- Gates: (pass/fail or n/a)
- Tier-2 (my eyes, rubric 1–5): silhouette X, proportions X, surface X, color X, artifacts X — notes
- Tier-3 judge: prefer K/3 vs <baseline-id>, rubric deltas
- Verdict: KEEP/REJECT/PIVOT(branch) — one sentence why
- Next:
```

## Pacing note (cost tracking retired 2026-06-10)

Dollar/cost tracking has been dropped — Joel runs on a subscription and money
budgets were a distraction from getting it right (CLAUDE.md standing order;
MASTER_PLAN §2.1). Use the **right model for the task, biased toward the stronger
one** (author bakes on opus, judge on sonnet); no strict budget rules. Wall-clock
times and session-cap events are still worth logging; the one real pacing
constraint is the account **session cap**.

## Rejected ideas
- Wikimedia Commons full-text File-namespace search for benchmark photos: returns
  book scans/PDFs; thumbor 429s rapid downloads. Use Openverse API instead.
- Openverse without `category=photograph`: returns clipart/illustrations/stylized
  art (rawpixel "png sticker" = often line art; "3 tulips" = posterized art).

## Decisions
- **2026-06-09 (Joel): class credibility > photo fidelity.** "I care less about
  it looking like the original photo than getting the class of objects right."
  Consequences: archetype is the quality bar everywhere (faithful mode drops in
  priority); judge prompt re-weighted to class credibility first; craft/prompt
  lines aim at "convincing instance of the kind" (class-typical mass, materials,
  character) rather than photo replication; the boulder's lost cracks matter
  only insofar as cracks make a *more convincing concretion boulder*.
- **2026-06-10 (Joel): simplicity / geometric essence over detail-chasing.**
  v1.1 chair preferred over v1.2.1 — *"simple and it captures the geometric
  essence"* vs v1.2.1 *"trying to capture geometry details like the swirls on
  the top."* Corollary to class credibility: prefer the simplest geometry that
  reads unmistakably as the kind; clean essential masses + a legible silhouette
  beat fine surface/geometric detail. **Chair is decided — v1.1 stays champion**
  (a human verdict outranks the judge). See SAMPLES.md chair section; OPUS_PLAYBOOK
  §0/§1/§3.
- **2026-06-10 (Joel): cost/budget tracking retired.** Subscription; money
  budgets were a distraction from getting it right. Removed dollar amounts and
  per-phase money budgets from all docs and the "stop when over budget" rules.
  Kept: right-model-for-the-task (biased toward the stronger model; cheaper only
  where the task allows), the free loop, one-change-per-bake, and session-cap
  handling. (CLAUDE.md; MASTER_PLAN §2.1/§2.5.)
- **2026-06-10 (Joel): user evaluation is welcome, not rare.** Proactively ask
  Joel to review SAMPLES.md + its links from time to time; don't block on him.
  (MASTER_PLAN §2.4 Tier 4; OPUS_PLAYBOOK §0.)
- **2026-06-10 (Joel): two new standing rules.** Start every session by reading
  all the Markdown files + `formcast.py` before anything else; refresh docs and
  code comments before every commit. (CLAUDE.md.)
- **2026-06-10 (Joel): repeatability is a soft aim, not a hard rule.** "Make
  quality repeatable instead of a per-run dice roll" was too strong — LLMs do
  best with some temperature, and run-to-run randomness is welcome when it
  improves results. Two same-parameter runs should land in *about* the same
  place, but that's a soft aim; Joel may prefer to be shown a few samples and
  pick the best (formcast already bakes a seed-varied library). The bar is a
  reliable quality *floor* (every run good), not bit-exact output. Softened the
  "dice roll / coin flip / byte-stable / determinism" language across the docs.
- **2026-06-10 (Joel): CLAUDE.md is the single source of truth for standing
  orders.** Other docs refer to it rather than duplicating standing constraints
  (he flagged PHOTOREALISM_PLAN repeating them). Keep documenting what worked AND
  what didn't — that practice is working and should continue. (CLAUDE.md.)
- **2026-06-10 (Joel): azalea (shrub) added to the benchmark** — a 6th class
  (shrub/foliage). Joel first supplied an AI-generated bush of unknown license;
  on his direction it was swapped for a **CC0 round azalea** (WordPress Photo
  Directory). See `benchmarks/manifest.json` and the P-docs entries at the bottom.
- **2026-06-10 (Joel): optimize the GENERAL case; don't over-index on specifics.**
  Prompted by the chair: the v1.1 chair beats every newer version, which means
  the current pipeline is a *regression for that one example* — and that's
  acceptable if the pipeline is better overall. The v1.1 chair is a lucky
  old-pipeline outlier; we accept it rather than special-case the prompts to
  reproduce it. Decision: keep the chair as v1.1 champion, do ONE v1.2.2
  checkpoint re-bake (to de-outlier the benchmark + get a second furniture signal
  under the current pipeline), then move on regardless of result. Forward
  investment goes to what helps the broadest set of objects (foliage atlas first),
  learning from patterns across all samples — not from any single example.
- **2026-06-10 (Joel): pencil added as a permanent tracked example.** A
  Joel-supplied yellow #2 pencil (`inputs/pencil.png`, tracked like
  `maple-tree.png`; `.gitignore` exception), class `tool` — a deliberately simple
  man-made object plus a multi-material / elongated-proportions test. Bakes under
  v1.2.2.
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
  prototype). ~30 candidates fetched, scored, visually verified. (No model calls.)
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
  Renders free; judge ran on sonnet.
- Artifacts: `fcviz.py` (to be merged into formcast.py), /tmp/p0test/*,
  `outputs/experiments/2026-06-09/{t2_dog_yup,t3_table_yup}.glb`.
- Findings: (1) up-axis auto-detect via embedded provenance.prompt_version works
  (1.1→Z-up, else Y-up). (2) **Up-axis bit me a third time**: the original
  t2_dog.glb/t3_table.glb are Z-up *files* (my earlier harness baked a +90°X
  rotation in before export) — "known-good test assets" must have their
  conventions verified, not assumed; regenerated genuine Y-up copies (`*_yup.glb`).
  (3) Judge self-test: 0/2 candidate wins, correct object-class reasoning in BOTH
  A/B orders — swap logic confirmed; ~18 s per sonnet trial.
- Verdict: KEEP — Phase-0 components validated; merge into formcast.py after
  baseline bakes finish (not editing formcast.py while bakes re-exec it).
- Next: v1.1 baselines render + freeze; then v1.2 overhaul.

## 2026-06-09 P-baselines.1 — v1.1 baselines on the new benchmark items
- Hypothesis/goal: freeze "before" state of current prompts across classes;
  expected the nature-only PASS1 taxonomy to fail on furniture.
- What ran: `bake <item> --count 2` for tulip/boulder/chair/table with frozen
  v1.1 prompts (sequential background loop; ~1 repair typical; timings in
  formcast.log).
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
- What ran: `bake table.jpg --count 2 --refine 1` (831 s incl. refine);
  judge 3 trials sonnet.
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
  adopted a revision); judge 3 trials. The earlier suite attempt died
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

## 2026-06-09 P-v12.4 — v1.2 tulip promoted 3/3
- What ran: retry `bake tulip.jpg --count 2 --refine 1` (1033 s — slowest item;
  refine adopted a revision after 275.8 s); judge 3 trials under the NEW
  class-credibility prompt.
- Tier-3 judge: **v1.2 preferred 3/3**; color/material 4 vs 1–2. Cited: closed
  egg-shaped bud silhouette, correct stem-to-bloom proportions, clean green
  stem, no broken geometry.
- Fixed vs v1.1: background-purple stem (anti-contamination rules), floating
  leaf scraps (connectivity language), petal coherence.
- Remaining defects (queued): faceted petals (needs smooth vertex normals or
  more segments — add a "smooth-shade curved organic surfaces" line to the
  foliage pack), onion-dome pinch at the bud tip, flat white vs the photo's
  cream/grey-green gradients (COLOR_0 gradient hint exists but wasn't used
  strongly).
- Running scoreboard: table 3/3 ✓, boulder 3/3 ✓, tulip 3/3 ✓, chair 1/3 ✗
  (v1.2.1 queued), maple baking.

## 2026-06-09 P-v12.5 — MILESTONE: v1.2 suite complete, 4/5 promoted
- Maple: `bake --count 2 --refine 2` (1044.8 s; BOTH refine rounds adopted
  revisions); judge **3/3 with straight 4s** vs 2–3s for the user's original
  v1.1 bake. Crown now full/rounded/dense with clump light-dark variation; the
  wispy gaps, floating clumps and narrow silhouette are gone.
- **Suite verdict: maple ✓ 3/3, table ✓ 3/3, boulder ✓ 3/3, tulip ✓ 3/3,
  chair ✗ 1/3.** Every promotion cleared the ≥2/3 protocol bar; the one
  rejection produced a specific, mechanistic fix (turned-wood mass).
- What v1.2 proved: (1) the render→critique→revise loop improves results the
  authoring model can SEE (it adopted revisions in 6 of 6 refine rounds across
  the suite); (2) anti-contamination texture rules fixed every in-situ photo
  failure; (3) the broadened taxonomy + craft packs fixed furniture end-to-end;
  (4) judge-human agreement held on both items the user checked.
- What v1.2 didn't fix (next iteration targets): turned-wood/material mass on
  the chair (v1.2.1, applying now); foliage depth (4:1 sun/shade range still
  partially flat; COLOR_0 underused); maple crown slightly too solid (needs
  branch glimpses through gaps); petal facets (smooth-shading line added);
  surface character preservation (boulder cracks).
- Maple remaining vs PHOTOREALISM_PLAN §13 bar: not yet at "clearly the same
  kind of tree AND clearly much better" full criteria (atlas leaf silhouettes,
  measured crown-fill gate, two-run quality consistency) — Phase 1 continues.
- Session output (timings in formcast.log): a 5-class CC0 benchmark, the eval
  infrastructure (headless renderer + A/B judge), two pipeline versions
  (v1.1 → v1.2), and 5 A/B verdicts — across baselines, the v1.2 suite (incl. a
  session-cap retry), and judges.
- Next: v1.2.1 (applied) → chair re-match + teapot + tiffany-lamp first bakes.

## 2026-06-10 P-v121.1 — v1.2.1 chair baked; session cap ends the Fable shift
- What ran: `bake chair.jpg --count 2 --refine 1` (956 s; refine adopted a
  revision). Teapot + lamp bakes and the chair judge were killed by the
  session cap (`Claude CLI exited 1 after ~1s`).
- Chair v1.2.1 render (`eval/v121-chair-contact.png`): **turned-wood mass
  arrived** — baluster bulbs/coves on the legs, substantial members, curled
  comb ears, surfaces `[arms, comb, legs, seat, spindles, stretchers]`,
  11,760 tris. New defect: near-silhouette BLACK — the script honored the
  photo's dark paint but skipped the requested grain/wear value variation, so
  internal detail vanishes in renders. Judge verdict pending (cap).
- Verdict: handoff. **Continuation is scripted in `OPUS_PLAYBOOK.md`** (step 1
  = chair judge; step 2 = teapot/lamp; step 3 = chair material fix via
  study-the-champion + free-loop prototyping; step 4 = `formcast eval` runner;
  step 5 = tree depth iteration; research detours with URLs; budget + cap
  protocol; champion registry).
- Champion registry at handoff: maple/table/boulder/tulip = v1.2;
  chair = v1.1; teapot/lamp = none yet.

## 2026-06-10 P-docs.1 — Opus takes over; doc pass on Joel's review comments
- Goal: Joel switched to Opus, read the docs, and gave a batch of direction.
  Revise all docs to match before resuming mainline bakes.
- What ran: documentation only (no model bakes).
- Joel's directions, applied:
  1. **Chair decided — v1.1 stays champion.** *"I still think the 1.1 chair is
     the best… simple and it captures the geometric essence"*; v1.2.1 was
     *"trying to capture geometry details like the swirls."* New standing
     principle: **simplicity / geometric essence over detail-chasing** (corollary
     to class credibility). Chair is closed; do not re-bake to win it.
     OPUS_PLAYBOOK §1 reframed (decided; judge is optional calibration only); §3
     reframed from "fix-and-rebake the chair" to "extract two general lessons"
     (simplest-geometry-that-reads; dark materials still need albedo value
     variation).
  2. **Cost/budget tracking retired.** Removed all dollar amounts, per-phase money
     budgets, and "stop when over budget" rules across CLAUDE.md, MASTER_PLAN,
     OPUS_PLAYBOOK, EVALS, PHOTOREALISM_PLAN. Kept right-model-for-the-task
     (biased toward the stronger model; cheaper where the task allows), the free
     loop, one-change-per-bake, and session-cap handling.
  3. **Repeatability softened.** "Repeatable instead of a per-run dice roll" was
     too strong; some temperature/randomness is welcome; two same-param runs land
     in *about* the same place (a soft aim). Bar = reliable quality floor, not
     bit-exact; Joel may want to pick the best of a few samples. Softened "dice
     roll / coin flip / byte-stable / determinism" wording everywhere.
  4. **New standing rules (CLAUDE.md):** read all md + `formcast.py` at session
     start; refresh docs + code comments before every commit; CLAUDE.md is the
     single source of truth for standing orders (other docs refer, don't
     duplicate — PHOTOREALISM_PLAN de-duplicated); keep documenting what worked
     AND what didn't.
  5. **User evaluation is welcome, not rare** (Tier 4): proactively invite Joel to
     review SAMPLES.md + its links; don't block on him.
  6. **Bush added to the benchmark** (Joel-supplied image): rounded multi-stem
     deciduous shrub, AI-composed green/autumn split, soft bokeh bg. Cached at
     `benchmarks/cache/picked/bush.png` (gitignored); thumbnail
     `eval/photos/bush.jpg` committed; manifest entry added. **License unknown
     (third-party site)** — local test use only; flag before any public push.
     First bake pending (OPUS_PLAYBOOK §2).
- Verdict: KEEP — docs now reflect Joel's current direction; mainline (teapot /
  lamp / bush first bakes, then encode the chair lessons + tree-depth iteration)
  resumes from OPUS_PLAYBOOK.
- Champion registry: maple/table/boulder/tulip = v1.2; chair = v1.1 (confirmed by
  Joel); teapot/lamp/bush = none yet.

## 2026-06-10 P-docs.2 — bush → CC0 azalea swap; advisor enabled
- Joel: replace the unknown-license bush with a known-license shrub ("Wikimedia
  may be a good source; maybe pick an azalea"). Searched Openverse + Wikimedia via
  the `benchmarks/fetch_candidates.py` helpers (`azalea bush/shrub/plant/...`); 14
  candidates downloaded (mostly CC0/PDM) and **visually vetted** (the standing
  rule — automated scoring alone accepts crops/clipart). Picked a **CC0 round
  azalea bush in full magenta bloom** (WordPress Photo Directory,
  `wordpress.org/photos/photo/985680f1d1/`, 1536×2048) — the cleanest whole-plant
  mounded dome silhouette of the set; rejects were diffuse/off-frame shrubs and a
  nursery of potted plants.
- Changes: removed the bush source (gitignored) and `git rm`'d the committed
  `eval/photos/bush.jpg`; added `eval/photos/azalea.jpg` (CC0) + manifest entry
  (id `azalea`, class `shrub`); updated SAMPLES, OPUS_PLAYBOOK (§2 bake + registry),
  and the MASTER_PLAN banner (now an 8-item CC0 benchmark). First bake still
  pending.
- Ops: Joel enabled Claude Code's **advisor** (Opus main → Fable 5) and asked me
  to consult Fable at the most appropriate, high-stakes pipeline points (e.g.
  prompt-pack changes, ambiguous judge verdicts, architecture) — not on routine
  picks like this image swap.
- Verdict: KEEP — benchmark is now fully CC0/PD with verified provenance.

## 2026-06-10 P-122.1 — v1.2.2 prompts: simplicity/essence + dark-material (encoded)
- Hypothesis/goal: encode Joel's chair lessons as general prompt principles so
  EVERY future bake benefits (no chair re-bake, per his verdict). Two additions
  with deliberate counterweights to avoid regressing the v1.2 wins.
- What changed (`formcast.py`, PROMPT_VERSION → `formcast/1.2.2-cli`):
  1. PASS2: new **"SIMPLICITY / ESSENCE FIRST"** bullet (simplest geometry that
     reads as the kind; essential masses + clean silhouette before fine detail;
     no detail that muddies the silhouette) — placed right after the character-
     features bullet as an explicit balance to it.
  2. `manmade` craft pack: **tempered** the turned-parts bullet — capture the
     2–4 MAJOR profile moves cleanly and stop; no fine rings/flutes/micro-
     ornament. Kept "thicker, substantial members" so we don't regress the v1.2
     thin-wiry failure.
  3. PASS3: sharpened the dark-material line — VERY DARK / near-black finishes
     must also sample the photo's lit-edge/sheen zones and keep a visible albedo
     value range (~2–3× lightest:darkest), or they render as black silhouettes
     (the v1.2.1 chair failure mode).
- Regression risk (flagged before writing — this was the planned advisor-consult
  point; the explicit advisor tool was unavailable so I reasoned it through):
  items 1–2 could strip needed mass/character. Mitigated by the framing above
  ("capture features with the simplest geometry", "major moves cleanly", kept the
  member-thickness line).
- Gates: `py_compile` OK; up-axis auto-detect unaffected (keys only on 1.0/1.1).
- Verdict: KEEP (encoded). **Validation pending** on the next bakes (teapot /
  lamp / azalea) — watch that furniture keeps its mass while shedding fussiness,
  and that any dark surface keeps a visible value range.
- Next: first bakes under 1.2.2.

## 2026-06-10 P-122.2 — teapot first bake (v1.2.2); dark-material rule VALIDATED
- What ran: `bake teapot.jpg --out-dir outputs/dev/v122-teapot --count 2
  --refine 1` (1122 s; refine round 1 adopted a revision — it diagnosed the body
  as too squat at front aspect 2.24 and rounded it). Class `vessel`
  (`black-ceramic-teapot`), 37,472 faces, surfaces [body, lid, spout, handle,
  accent] from revolved profiles + swept tubes.
- Tier-2 (my eyes, rubric 1–5): silhouette 4, proportions 4, surface 4,
  color/material 4, artifacts 4. Unmistakably a teapot; all four parts present
  and placed right; oxblood accent band on the lid rim + spout lip.
- **Dark-material rule (1.2.2) VALIDATED:** the black glaze renders as *form*
  with a speckled stony texture and a visible value range — NOT a flat black
  silhouette (the v1.2.1 chair failure). This is the first dark object baked
  under the new rule and it behaved exactly as intended.
- Honest gaps vs photo: body slightly wider/squatter; glaze more speckled than
  the photo's smooth matte; spout a hair long.
- Verdict: KEEP — teapot becomes its own first champion (no prior bake to beat).
  No judge needed (no champion). Renders: `eval/v122-teapot-{front,contact}.png`.
- Next: azalea, then tiffany-lamp.

## 2026-06-10 P-122.3 — azalea first bake (v1.2.2); foliage-on-shrub
- What ran: `bake azalea.jpg --out-dir outputs/dev/v122-azalea --count 2
  --refine 1` (1120 s; refine round 1 adopted a revision — it diagnosed the first
  attempt as reading like "a little tree" with an exposed woody trunk + hollow
  underside, and rebuilt it as a solid mound). Class `shrub`
  (`mounded-azalea-shrub`), 8,060 faces, surfaces [branches, flowers, foliage].
- Tier-2 (my eyes): silhouette 4, proportions 4, surface 3, color/material 4,
  artifacts 4. Reads unmistakably as a flowering mounded shrub.
- What worked: the refine→mound rescue is a clean win for the simplicity/essence
  principle (a legible dome silhouette beats a fussy tree); correct magenta-bloom
  + green palette; solid base, no floaters.
- What didn't (queued, points straight at step 5): flowers concentrate as a pink
  "cap" with green only at the base, not distributed over the whole mound with
  foliage interspersed (the photo); bloom texture is a blotchy painted blanket,
  not distinct azalea flowers — the foliage pack needs the leaf/flower-silhouette
  ATLAS (step 5c) and more sun/shade depth (5a). Strong evidence to prioritize 5c.
- Verdict: KEEP — azalea is its own first champion. Renders:
  `eval/v122-azalea-{front,contact}.png`.
- Next: tiffany-lamp.

## 2026-06-10 P-122.4 — tiffany-lamp: timeout then session cap (still chasing it)
- Stretch case (mosaic stained-glass shade + cast-bronze base). Attempts:
  1. Default cli-timeout (1200 s): pass 1 classified correctly; **pass 2 timed
     out** authoring the mosaic — no GLB. NOT a session cap (which dies in ~1 s);
     a real authoring timeout.
  2. `--cli-timeout 2700`: **pass 2 cleared** (9,056 faces; surfaces
     [shade, base, arms, foot, fittings]) and built the shade as a FACETED DOME
     surface rather than hundreds of tile solids (the v1.2.2 simplicity line
     helping). Then **pass 3 was killed by the session cap** (429, "session
     limit · resets 11:20am") — nothing persisted (the generator saves after
     pass 3).
  3. After the cap reset: re-baking at `--cli-timeout 2700` (in progress).
- Findings: (a) heavy geometry needs `--cli-timeout` raised for the lamp class;
  (b) the simplicity principle is already steering the mosaic toward a faceted
  surface instead of tile solids — worth reinforcing in the prompt (mosaic shade
  = faceted surface + mosaic TEXTURE, never per-tile geometry).
- Verdict: lamp NOT yet a champion (acceptable — the documented stretch case).
  **7 of 8 benchmark items have champions.**
- Hand-off: the 7 champions + reference photos are staged at
  `~/Public/formcast-champions/` (with README) for Joel to view as interactive
  3D; lamp added when it lands.
- Next: lamp re-bake result; reinforce the mosaic-as-texture lesson if it helps.

## 2026-06-10 P-122.5 — tiffany-lamp COMPLETED (3rd attempt); stretch case cleared
- What ran: re-bake after the cap reset, `--cli-timeout 2700` (1829 s; refine
  round adopted a revision — made it tall/slender at aspect 0.66, fixed the arms,
  flattened the dome, flipped the shade color bands). 22,744 faces; surfaces
  [shade, base, arms, foot, fittings]. Mosaic built as a FACETED textured dome,
  not tile solids.
- Tier-2 (my eyes): silhouette 4, proportions 4, surface 3, color/material 4,
  artifacts 3. For the hardest item, a genuinely credible Tiffany lamp: two-mass
  mushroom silhouette, jewel-toned leaded-glass dome (blue-green + amber skirt +
  suggested eyes), patinated-bronze vasiform base.
- What worked: mosaic-as-texture (the simplicity principle) cleared the tile-
  geometry timeout AND looks right. What didn't: peacock "eyes" are abstract
  blobs, came-lines not crisp, bronze base a bit soft/lumpy.
- Verdict: KEEP — lamp is its own first champion; the stretch case beat the
  "mediocre is fine" bar. **All 8 original benchmark items now have champions.**
- Lesson to bank in the prompt (general): heavy repeating surface detail
  (mosaic/leaded glass, fish scales, brickwork) = faceted surface + TEXTURE,
  never per-tile/-unit geometry.
- Next: copy lamp to ~/Public; bake the pencil (now unblocked).

## 2026-06-10 P-122.6 — pencil first bake (v1.2.2); simplicity principle's clearest win
- What ran: `bake inputs/pencil.png --out-dir outputs/dev/v122-pencil --count 2
  --refine 1` (1941 s; refine matched the photo's diagonal pose — aspect 1.50 ≈
  1.46 — and brightened the yellow). Class `tool` (`yellow-graphite-pencil`);
  surfaces by zone (paint / wood / graphite / ferrule / eraser).
- Tier-2 (my eyes): silhouette 5, proportions 5, surface 4, color/material 4,
  artifacts 5. A textbook pencil — the simplicity/essence principle's clearest
  win (a simple object rendered cleanly and unmistakably).
- What didn't: brass ferrule reads slightly orange (not metallic); bare-wood
  collar near the tip faint.
- Verdict: KEEP — pencil is its own first champion. Renders:
  `eval/v122-pencil-{front,contact}.png`; staged at ~/Public.
- Next: the 5 v1.2.2 re-bakes (maple/table/boulder/tulip/chair) so every SAMPLES
  item shows reference + champion + 1.2.2 (Joel's request).

## 2026-06-11 P-122.7 — v1.2.2 re-bake sweep (parity + v1.2→v1.2.2 comparison)
- Goal (Joel): every SAMPLES item shows reference + champion + 1.2.2; re-bake the
  5 older items under v1.2.2; promote where 1.2.2 wins/ties. (Survived two session
  caps mid-batch — maple's then chair's pass 3; re-run each after reset.)
- Results (Tier-2 eye calls; A/B judge deferred to avoid competing with the bake
  batch for the cap):
  - **maple** — v1.2.2 ≈ v1.2 (near tie). Champion **STAYS v1.2**. Simplicity/
    dark-material don't target foliage → no gain. Confirms the foliage atlas is
    the real plant lever, not prompt tweaks.
  - **table** — **PROMOTED to v1.2.2.** Now renders the Met piece's blue
    jasperware panels + gilt banding + cameo (the documented v1.2 "no gilt/
    grey-mauve" weakness). Material fidelity, not geometric clutter. Legs a bit
    thin/brassy. 4/4/4/4/4.
  - **boulder** — **PROMOTED to v1.2.2 (Joel's call).** My eye flagged a
    spherical-UV pole-pinch (streaky apex) as a regression; Joel reviewed the 3D
    model and prefers the richer v1.2.2 texture — his verdict outranks the eye
    call. (Pole-pinch still worth fixing later: cellular texture + crack ridges.)
  - **tulip** — **PROMOTED to v1.2.2.** Fixes the documented onion-dome pinch
    (softer-shouldered closed bud matching the photo) + adds leaves. 5/4/3/3/4.
  - **chair** — **STAYS v1.1.** The de-outlier checkpoint came back NEGATIVE:
    v1.2.2 has better structure (full comb-back, writing-tablet arm, splayed legs
    + stretcher) but renders silhouette-BLACK again (the v1.2.1 failure). The
    dark-material rule (which fixed the black teapot) didn't take — the chair's
    paint is matte/low-sheen, so there's little sheen to *sample*. Finding: the
    rule must LIFT/synthesize a value range for matte near-black surfaces, not
    just sample one. Queued, NOT chased (general-case direction). The chair
    outlier persists — now for an understood reason.
- **PATTERN (general-case learning):** a blanket prompt rev helps UNEVENLY.
  Three of four re-bakes promoted to v1.2.2 — material (table), silhouette
  (tulip), and rock character (boulder, on Joel's call) — while only **foliage
  (maple) was a wash.** So the single highest-value next lever is a **foliage/
  petal silhouette atlas**; secondary is a cellular (non-streaky) rock texture +
  geometric crack ridges to fix the pole-pinch the boulder promotion carries.
  Also: Joel's human review overruled my eye on the boulder — keep inviting it on
  close calls.
- Next: chair checkpoint result → sweep complete.

## 2026-06-11 P-docs.3 — Fable: doc restructure + low-hanging-fruit pass (pre-1.0)
- Joel merged `experiments` into `main`, switched the session to Fable, and asked
  for a release-1.0 prep: simplify the docs into README (overview + gallery),
  SAMPLES (visual journal), ROADMAP (all future work + Opus directions), and
  TECHNICAL (how it works + a 3D-modeling primer for a computing reader).
- Done: created `ROADMAP.md` (release checklist, quick wins, experiment program
  with sweep-updated priorities, research links, Opus directions, champion
  registry) and `TECHNICAL.md`; retired `MASTER_PLAN.md`, `OPUS_PLAYBOOK.md`,
  `PHOTOREALISM_PLAN.md` (open items folded into ROADMAP; full texts in git
  history); README got a Documentation section + gallery footnote fix; SAMPLES
  and CLAUDE.md repointed.
- Low-hanging fruit found (now ROADMAP §1–2): no session-cap detection (generic
  "exited 1" — cost 4 dead bakes this week); CLI_TIMEOUT_S=1200 too low (lamp
  needed 2700); requirements.txt unpinned while prompts hard-assume numpy 2.x /
  Pillow≥10 / trimesh 4.x; no __version__/--version; DEFAULT_COUNT=10 vs every
  real run using --count 2; three banked prompt lines (matte-dark value lift,
  repeating-detail-as-texture, no pole-pinch UVs) not yet folded in; judge
  confirmations of the table/tulip eye-call promotions still pending.
- Verdict: docs are now four human-readable files + this log; handoff to Opus is
  ROADMAP §1 (release checklist) then §2–3.
