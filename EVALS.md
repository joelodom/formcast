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
