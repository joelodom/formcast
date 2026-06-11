# CLAUDE.md

Guidance, preferences, and standing orders for working in this repository.

## What this project is

`formcast` is a single-file Python CLI (`formcast.py`) that turns a 2D reference
photo into a small library of seed-varied procedural 3D models (`.glb`). It drives
the local `claude` CLI (headless, Read-tool-only) to author the modeling code, runs
that code to bake the models, and embeds metadata in each `.glb`. Four subcommands:
`bake`, `inspect`, `view`, and `judge` (a fresh-session VLM A/B comparison of two
render contact sheets against the photo). See `README.md` for the user-facing guide
and the header docstring in `formcast.py` for the full design.

Keep the tool **generic 2D → 3D**. It was adapted from a planet-generator context;
do **not** re-narrow it back to planets. Natural-object examples are welcome — the
bundled sample and the worked examples use a **maple tree** (`inputs/maple-tree.png`);
oaks, rocks, and shrubs are fine too.

## Standing orders / preferences

- **Start every session by reading the docs and the code, before anything else.**
  Read every Markdown file in the repo (`README.md`, `SAMPLES.md`, `ROADMAP.md`,
  `TECHNICAL.md`, `EVALS.md`, this file) and `formcast.py` in full before doing
  any work. They carry the standing plan, the experiment history, and the current
  champions — don't act on a stale summary or a half-remembered state.
- **Do not commit or push until explicitly told to.** Standing order for the whole
  session, not just one change. Wait for the user to say "commit".
- **Refresh the docs and code comments before every commit.** Re-read the docs and
  inline comments touched by the change (README, the planning/journal docs above,
  any stale comments in `formcast.py`) and bring them up to date in the *same*
  commit. Documentation tracks the code; never let it drift, never fix it "later".
- **Do not create new branches unless explicitly asked.** Work directly on `main`
  by default.
- **Keep `README.md` up to date.** Any change to behavior, flags, commands, or the
  workflow must be reflected in the README as part of the same change. The README is
  the front door; never let it drift from the code.
- **This file (`CLAUDE.md`) is the single source of truth for standing orders.**
  Other docs (`README.md`, `SAMPLES.md`, `ROADMAP.md`, `TECHNICAL.md`) should
  *refer* here for the standing behavioral constraints, not re-derive or duplicate
  them. Where a working doc restates a rule for the reader's convenience, it cites
  CLAUDE.md as the source so the rules can't drift.
- **Document what worked AND what didn't — always.** The docs exist to keep us from
  repeating mistakes, and this is working well: keep it up. `EVALS.md` holds
  per-experiment verdicts plus a `Rejected ideas` section; `SAMPLES.md` carries a
  per-item "what worked / what didn't / what got worse" for each version; the plans
  keep honest field notes. Every experiment records its outcome — wins, regressions,
  and dead ends — before moving on.
- **Favor getting it right over saving tokens.** Joel works on a subscription;
  long, token-heavy sessions are fine when the work genuinely needs them. Don't
  navel-gaze on cost, and don't stop early to conserve budget — but don't spin
  without making progress either. Dollar amounts and per-phase money budgets have
  been removed from the docs on purpose; they were a distraction from getting it
  right. The only real pacing constraint is the account **session cap** (see
  Logging & diagnosis / the playbook).
- **Prefer `ct`** (the in-memory code-intelligence daemon) over the built-in
  Read / Grep / Glob tools for indexed files: `ct_read`, `ct_grep`, `ct_outline`,
  `ct_lookup`, `ct_search`, etc. Built-in tools are fine for unindexed / newly
  added / non-source files.

## Logging & diagnosis

formcast uses stdlib `logging`: **INFO to stdout, full DEBUG always tee'd to
`formcast.log`** (gitignored). When something is slow or misbehaving, run with
`-v`/`--verbose` (DEBUG on the console too) and/or read `formcast.log` — it records
per-pass and per-variant timings plus each `claude` call's duration, turn count, and
token/cost usage. That logfile is the shared artifact for diagnosing runs together.

Expected, user-facing failures raise `FormcastError` and exit cleanly; anything else
is logged with a full traceback (to the logfile, always). Keep that convention.

## Working directories

- `inputs/`  — source photos. Local-only EXCEPT the tracked permanent examples
  `inputs/maple-tree.png` and `inputs/pencil.png` (the README's / benchmark's
  worked examples).
- `outputs/` — baked `.glb` models. Never tracked; the user creates it (formcast
  also makes it on first bake).

## Running it

```bash
pip install -r requirements.txt
mkdir -p outputs
python formcast.py bake inputs/maple-tree.png --out-dir outputs/ --count 10
```

`bake` needs the `claude` CLI installed and authenticated (a Claude subscription
login works, or set `ANTHROPIC_API_KEY`).
