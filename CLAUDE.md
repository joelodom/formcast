# CLAUDE.md

Guidance, preferences, and standing orders for working in this repository.

## What this project is

`formcast` is a single-file Python CLI (`formcast.py`) that turns a 2D reference
photo into a small library of seed-varied procedural 3D models (`.glb`). It drives
the local `claude` CLI (headless, Read-tool-only) to author the modeling code, runs
that code to bake the models, and embeds metadata in each `.glb`. Three subcommands:
`bake`, `inspect`, `view`. See `README.md` for the user-facing guide and the header
docstring in `formcast.py` for the full design.

Keep the tool **generic 2D → 3D**. It was adapted from a planet-generator context;
do **not** re-narrow it back to planets. Natural-object examples are welcome — the
bundled sample and the worked examples use a **maple tree** (`inputs/maple-tree.png`);
oaks, rocks, and shrubs are fine too.

## Standing orders / preferences

- **Do not commit or push until explicitly told to.** Standing order for the whole
  session, not just one change. Wait for the user to say "commit".
- **`formcast.py` started untracked** — `git add` it when first committing.
- **Keep `README.md` up to date.** Any change to behavior, flags, commands, or the
  workflow must be reflected in the README as part of the same change. The README is
  the front door; never let it drift from the code.
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

- `inputs/`  — source photos. Local-only EXCEPT `inputs/maple-tree.png`, which is
  tracked as the README's example.
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
