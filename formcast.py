#!/usr/bin/env python3
# =============================================================================
# formcast.py  --  Image -> procedural GLB archetype baker (+ inspector + viewer)
# =============================================================================
#
# WHAT THIS IS
# ------------
# A single command-line tool with three subcommands:
#
#   bake     A reference photo of a natural object (a tree, a boulder, a shrub...)
#            goes IN; a small library of static .glb 3D models comes OUT. The
#            models are NOT a faithful reconstruction of the photographed object
#            -- they are convincing, seed-varied instances "of the same kind of
#            thing", in that style. This is the main event. (See PIPELINE below.)
#
#   inspect  Decode and print the custom metadata bundle we embed inside each
#            .glb (the prose description, the original source image, the exact
#            generator script that produced the model, and provenance). Can also
#            extract those embedded artifacts back out to files.
#
#   view     Open a 3D render of one .glb, or of a whole set laid out in a row
#            (e.g. all ten variants of an archetype, side by side, for review).
#
#
# THE ENGINE: the local `claude` CLI in headless mode (NOT the HTTP API)
# ---------------------------------------------------------------------
# `bake`'s three authoring passes call Claude Code on your machine in print /
# headless mode:  `claude -p "<prompt>" --output-format json --model ... \
#                          --allowedTools "Read"`.
# We parse the JSON it prints (its `result` text and `session_id`), and keep the
# multi-turn conversation going across passes and repairs with `--resume <id>`.
#
# Because the CLI has no --image flag, we hand it the photo by copying it into a
# scratch working directory and asking it to open the file with its Read tool
# (Read can view images). Read is the only tool we allow, so it can see the image
# but cannot write files or run commands, and it never stops to ask permission.
#
#
# THE PIPELINE behind `bake`  (four passes; only the first three call the CLI)
# ---------------------------------------------------------------------------
#   Pass 1  CLASSIFY + DESCRIBE   [reads the image]
#           -> an archetype id (used for filenames) + one long prose description
#              capturing style, structure, rough proportions, surface materials,
#              and which biomes it belongs to. Qualitative, not metrological --
#              that plays to the model's strengths and to our "style, not
#              reconstruction" goal.
#
#   Pass 2  AUTHOR THE GEOMETRY   [reads the image + the Pass 1 prose]
#           -> a Python function `build_mesh(seed, density) -> trimesh.Scene`
#              whose geometry is keyed by SEMANTIC SURFACE NAME ("trunk",
#              "branches", "canopy", "rock", ...). Deterministic given the seed;
#              `density` scales triangle / leaf-card counts so the same code can
#              later emit LOD levels. GATE: we actually run it and check the mesh
#              is non-empty with finite bounds. On failure we hand the error back
#              to the model and ask for a fix (bounded retries).
#
#   Pass 3  AUTHOR TEXTURING + EXPORT   [reads the image + everything so far]
#           -> the COMPLETE standalone generator script: it folds in the Pass 2
#              geometry, pulls tileable de-lit material swatches out of the source
#              image, applies UVs by surface type (cylindrical on trunks/branches,
#              triplanar-baked on rock, atlas quads on leaf cards), assigns
#              materials, and exports a .glb. It exposes a CLI:
#                   <script> --image IMG --seed N --density D --output OUT.glb
#              GATE: we run the whole script end-to-end and confirm the .glb opens
#              with real geometry. Same repair loop on failure.
#
#   Pass 4  BAKE   [deterministic plumbing -- no model]
#           -> run the frozen script N times with seeds 0..N-1 (optionally across
#              density/LOD levels), producing `<archetype>-NN.glb` files. Then we
#              inject the metadata bundle into each .glb.
#
# After bake, you load these static .glb files in whatever engine or tool you like
# (Blender, three.js, Godot, Unity, a Rust `gltf` loader, ...) and use them however
# you want -- scatter them, place them by hand, drop them into a scene. Everything
# this tool does happens ahead of time; nothing here runs at your app's runtime.
#
#
# TRUST NOTE  (please read once)
# ------------------------------
# `bake` does two things that run code on your machine:
#   (1) it invokes the `claude` CLI, which is an agent -- but we restrict it to
#       the Read tool only, so within bake it can read the image and nothing else;
#   (2) it EXECUTES the Python that the model wrote, in a subprocess, to build the
#       meshes. That is the whole point of the design, and you have signed off on
#       the trust model -- but run this only in an environment you control.
# `inspect` and `view` never execute embedded code; they only read data.
#
#
# WHY THE METADATA LIVES IN TOP-LEVEL glTF `extras` (not `asset.extras`)
# ---------------------------------------------------------------------
# Both are spec-valid glTF 2.0. In testing, the pygltflib serializer reliably
# round-trips the TOP-LEVEL `extras` through a binary .glb but silently drops
# `asset.extras`. So we use the top-level. The metadata sits in the JSON chunk;
# it is never uploaded to the GPU and your runtime loader can ignore it entirely.
#
#
# INSTALL
# -------
#   pip install -r requirements.txt
#   # and install Claude Code (the `claude` CLI) and sign in once:
#   #   npm install -g @anthropic-ai/claude-code     (needs Node.js)
#   #   claude   # run once interactively to authenticate (or set ANTHROPIC_API_KEY)
#
# `bake` needs the `claude` CLI on PATH and authenticated (a Claude subscription
# login works; it also honors ANTHROPIC_API_KEY if you prefer that). No API key is
# required by this tool directly.
#
# The 3D viewer (`view` without --save) needs a working OpenGL display.
# `view --save out.png` renders off-screen to an image instead.
#
#
# USAGE EXAMPLES
# --------------
#   python formcast.py bake inputs/maple-tree.png --out-dir outputs/ --count 10
#   python formcast.py bake inputs/maple-tree.png --count 10 --lods     # also emit LOD chain
#   python formcast.py bake inputs/maple-tree.png --model claude-opus-4-8  # pin a model
#   python formcast.py inspect outputs/maple-tree-03.glb
#   python formcast.py inspect outputs/maple-tree-03.glb --extract ./extracted/
#   python formcast.py view outputs/maple-tree-*.glb               # all ten in a row
#   python formcast.py view outputs/maple-tree-03.glb --save preview.png
#   python formcast.py bake inputs/maple-tree.png --verbose            # DEBUG on stdout too
#
# If a bake ever hangs or errors on a tool permission, you are on a trusted
# machine, so the simplest escape hatch is to pass extra CLI flags through, e.g.:
#   python formcast.py bake inputs/maple-tree.png --claude-extra "--dangerously-skip-permissions"
#
#
# LOGGING
# -------
# Everything is logged with the stdlib `logging` module: INFO to stdout, plus full
# DEBUG (timings, the exact CLI calls, model usage/cost) tee'd to a logfile
# (default: formcast.log, append mode). Pass -v/--verbose to also see DEBUG on the
# console. The logfile is the artifact to share when diagnosing a slow or odd run.
# =============================================================================

from __future__ import annotations

import argparse
import base64
import glob as globmod
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

# Third-party libs that are always needed (cheap to import):
import trimesh
import pygltflib

# NOTE: PIL is only needed by the *generated* bake scripts, not by this tool.


# -----------------------------------------------------------------------------
# Errors
# -----------------------------------------------------------------------------

class FormcastError(Exception):
    """An expected, user-facing failure: bad input, a failing authoring pass, a
    missing dependency, and so on. main() turns these into a clean one-line
    message plus a non-zero exit code instead of dumping a traceback. Genuine
    bugs are NOT this type -- those propagate and get logged with a full
    traceback so we can debug them."""


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
# Idiomatic stdlib logging. Both stdout and the logfile use the SAME timestamped,
# level-tagged format; they differ only in threshold. Stdout shows INFO+ by default
# (-v/--verbose drops it to DEBUG+); the logfile ALWAYS captures DEBUG+ -- timings,
# the exact CLI calls, model usage/cost -- so any run can be diagnosed after the
# fact, even one you ran at the default level.

log = logging.getLogger("formcast")

DEFAULT_LOG_FILE = "formcast.log"


def setup_logging(verbose: bool, log_file: str | os.PathLike) -> None:
    """Configure stdout + logfile handlers. Safe to call once per process.

    Both handlers share one timestamped, level-tagged format and differ only in
    threshold: stdout shows INFO and above (DEBUG with --verbose); the logfile
    keeps DEBUG and above, always.
    """
    log.setLevel(logging.DEBUG)            # handlers below do the level filtering
    log.handlers.clear()                   # idempotent across repeated calls
    log.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Console (stdout): INFO+ by default, DEBUG+ with --verbose.
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    log.addHandler(console)

    # Logfile: always DEBUG+, appended so history accrues across runs.
    try:
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    except OSError as e:  # e.g. an unwritable path -- degrade to stdout-only
        log.warning("could not open log file %s (%s); logging to stdout only",
                    log_file, e)
        return
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    log.debug("=== formcast start: %s ===", " ".join(sys.argv[1:]) or "(no args)")


# -----------------------------------------------------------------------------
# Configuration / constants
# -----------------------------------------------------------------------------

# Model passed to the CLI via --model. The CLI accepts aliases ("opus", "sonnet")
# or full ids ("claude-opus-4-8"). The alias tracks the current Opus automatically.
DEFAULT_MODEL = "opus"

DEFAULT_CLAUDE_BIN = "claude"       # the Claude Code executable (override with --claude-bin)
DEFAULT_ALLOWED_TOOLS = "Read"      # least privilege: it may read the image, nothing else
CLI_TIMEOUT_S = 1200                # per CLI call; agentic + thinking can be slow (20 min)

DEFAULT_COUNT = 10                  # variants per archetype
DEFAULT_DENSITY = "high"            # we bake "awesome" by default; dial down later
DENSITY_LEVELS = ("high", "med", "low")
LOD_FOR_DENSITY = {"high": 0, "med": 1, "low": 2}  # used when --lods is passed

DEFAULT_MAX_REPAIRS = 2             # how many times to ask the model to fix a failing pass
SUBPROCESS_TIMEOUT_S = 300          # generous cap for running a *generated* bake script

# A short, fixed description of the metadata schema. Identical across every .glb
# so that future-you (or future tooling) can interpret a file with no outside
# context. It is intentionally tiny.
SCHEMA_DOC = (
    "formcast archetype metadata. Fields: "
    "'schema_doc' (this string); "
    "'description' (long unstructured prose: style, structure, materials, biomes); "
    "'archetype_id' (operational identifier, also the filename stem); "
    "'class' (coarse category, e.g. tree/shrub/rock); "
    "'variant' ({index, seed, density, lod}); "
    "'source_image_b64' ({media_type, data} -- the original reference photo); "
    "'generator_script' (the exact standalone Python that baked this model); "
    "'provenance' ({tool, engine, model, prompt_version, created_utc} -- enough to re-bake)."
)

PROMPT_VERSION = "formcast/1.1-cli"  # bump when the prompts/engine below change materially


# -----------------------------------------------------------------------------
# Prompt templates for the three authoring passes
# -----------------------------------------------------------------------------
# These encode the entire design philosophy. They are deliberately strict about
# the OUTPUT CONTRACT (what shape the answer must take) because the orchestrator
# parses and runs the result. Each pass's "system" guidance is prepended into the
# prompt body (the headless CLI keeps Claude Code's default agent persona; we
# layer our task framing on top in the user prompt itself).

PASS1_SYSTEM = (
    "You are a botanist-geologist with a sculptor's eye, identifying natural "
    "objects from photographs for a procedural 3D asset pipeline. You are "
    "describing the KIND of thing in the image and its visual character -- you "
    "are NOT reconstructing the specific photographed object."
)

PASS1_INSTRUCTION = textwrap.dedent("""\
    Identify the natural object in the reference image (tree, shrub, plant,
    boulder, rock formation, etc.).

    Return ONLY a JSON object (no prose, no code fences) with exactly these keys:
      "archetype_id": a short kebab-case identifier, e.g. "sugar-maple" or
                      "granite-boulder". Lowercase letters, digits, hyphens only.
      "class":        a single coarse word: one of tree, shrub, plant, grass,
                      cactus, rock, boulder, cliff, log, stump (or the closest fit).
      "description":  ONE long, unstructured paragraph (150-350 words) describing,
                      QUALITATIVELY (not with precise measurements):
                        - overall silhouette and growth habit / form
                        - structural breakdown (trunk taper, how branches fork and
                          spread; or for rock: facets, stratification, roundedness)
                        - the distinct SURFACE MATERIALS present and where each sits
                          (e.g. "furrowed grey-brown bark on trunk and major limbs;
                          dense mid-green foliage in rounded clumps")
                        - color and texture character of each material
                        - the biomes / climates / terrain where this belongs.
                      Favor descriptive character over numbers. This text is the
                      sole semantic record stored with the model, so make it rich.
    """)

PASS2_SYSTEM = (
    "You are an expert technical artist who writes clean, deterministic Python "
    "for procedural 3D geometry using numpy and trimesh. You write GENERATORS: "
    "given a seed you produce a plausible, good-looking INSTANCE of an archetype, "
    "never a copy of one specific real object."
)

PASS2_INSTRUCTION = textwrap.dedent("""\
    Using the reference image and this description, write a Python module that
    procedurally generates the GEOMETRY for this archetype.

    DESCRIPTION:
    {description}

    Hard requirements for the code you return:
      * Use only `numpy` and `trimesh` (plus the Python stdlib). No file or
        network I/O. No textures yet -- geometry only.
      * Expose exactly this entry point:

            def build_mesh(seed: int, density: str = "high") -> trimesh.Scene:

      * It MUST be deterministic given `seed`. Seed all randomness from a local
        `rng = np.random.default_rng(seed)`. Do not touch the global RNG.
      * `density` is one of "high", "med", "low" and scales polygon / element
        counts (subdivision, number of branches, number of leaf cards, noise
        octaves, etc.). Read `density` and choose counts from it BEFORE building
        -- generate at the target density, never build dense then decimate.
        "high" should look genuinely good; "low" should be a cheap distant LOD.
      * Return a `trimesh.Scene` whose geometry is keyed by SEMANTIC SURFACE NAME.
        Use scene.add_geometry(mesh, geom_name="<name>"). Names must be the
        surface types the texturing step will paint, for example:
          - trees/shrubs: "trunk", "branches" (may merge with trunk), "canopy"
          - rocks/boulders/cliffs: "rock"
        Choose names that match the materials called out in the description.
      * For foliage, DO NOT model individual leaves as solid geometry. Build the
        canopy as LEAF CARDS: flat quads scattered through the canopy volume,
        oriented with some variation, to be textured later with an alpha-cutout
        leaf-cluster texture. A few hundred cards at "high" is plenty.
      * Every returned mesh must have valid vertices and faces (triangles) and
        sane, finite bounds. Recompute normals where appropriate.

    Think about good structure (organic branching, believable rock silhouettes
    via noise-displaced hulls, etc.). Return ONLY the Python module inside a
    single ```python code block. No commentary outside the block.
    """)

PASS3_SYSTEM = (
    "You are an expert technical artist who writes clean, deterministic Python "
    "for procedural 3D assets using numpy, trimesh and Pillow. You produce a "
    "single self-contained script that builds geometry, derives tileable "
    "materials from a reference photo, applies UVs by surface type, and exports "
    "a textured GLB."
)

PASS3_INSTRUCTION = textwrap.dedent("""\
    Combine the geometry below with texturing and export into ONE complete,
    standalone Python script.

    DESCRIPTION:
    {description}

    GEOMETRY MODULE (already validated -- reuse build_mesh, improving only if
    needed to attach UVs cleanly):
    ```python
    {geometry_code}
    ```

    The finished script must:
      * Use only `numpy`, `trimesh`, `PIL` (Pillow), and the Python stdlib.
      * Contain `build_mesh(seed, density)` from above (verbatim or lightly edited).
      * Read the SOURCE IMAGE from the --image path and derive TILEABLE, roughly
        DE-LIT material swatches for each semantic surface (e.g. a bark swatch, a
        foliage / leaf-cluster swatch, a rock swatch). Sample representative
        regions; make swatches tile without obvious seams; reduce baked-in
        lighting gradients so the material reads evenly when repeated. For leaf
        cards, build an alpha-cutout leaf texture (RGBA) so card corners read as
        leaves, not squares.
      * Apply UVs appropriate to each surface and assign materials:
          - trunk / branches: cylindrical UVs along the limb axis
          - rock: triplanar projection baked into per-vertex UVs (no manual unwrap)
          - canopy leaf cards: map the leaf texture onto each quad
        Attach via trimesh.visual.TextureVisuals (uv=..., material=PBRMaterial),
        so textures are embedded when exported to GLB.
      * Be DETERMINISTIC given --seed (geometry and any swatch jitter).
      * Expose this exact CLI and write a binary .glb to --output:

            python <thisscript> --image PATH --seed INT --density {{high,med,low}} --output OUT.glb

        Use argparse under `if __name__ == "__main__":`. Build the scene, then
        `scene.export(file_obj_or_path)` (or write `scene.export(file_type="glb")`
        bytes) to --output. Exit non-zero on error.

    Return ONLY the complete Python script inside a single ```python code block.
    No commentary outside the block.
    """)


# -----------------------------------------------------------------------------
# Small generic helpers
# -----------------------------------------------------------------------------

def _sanitize_id(raw: str) -> str:
    """Coerce a model-proposed id into a safe kebab-case filename stem."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)   # non-alphanumerics -> hyphen
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "archetype"


def _extract_code_block(text: str) -> str:
    """
    Pull Python source out of a model response. Prefers a fenced ```python block;
    falls back to any fenced block; falls back to the raw text. Tolerates the
    model wrapping or not wrapping its answer.
    """
    m = re.search(r"```(?:python|py)\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip("\n")
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip("\n")
    return text.strip()


def _extract_json(text: str) -> dict:
    """
    Parse the first JSON object found in a model response, tolerating code
    fences and stray prose around it.
    """
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)```", t, re.DOTALL | re.IGNORECASE)
    if fence:
        t = fence.group(1)
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model response:\n" + text[:500])
    return json.loads(t[start:end + 1])


def _run_python(script_path: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """
    Run a Python script in a subprocess using the SAME interpreter (so the
    installed libraries are available). Returns the CompletedProcess; never
    raises on non-zero exit (callers inspect returncode / stderr).
    """
    cmd = [sys.executable, str(script_path), *args]
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          timeout=SUBPROCESS_TIMEOUT_S)


# -----------------------------------------------------------------------------
# Image helpers (used by `bake`)
# -----------------------------------------------------------------------------

def _load_image_bytes(path: Path) -> tuple[bytes, str]:
    """Return (raw_bytes, media_type) for the original image, untouched."""
    raw = path.read_bytes()
    ext = path.suffix.lower().lstrip(".")
    media = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "webp": "image/webp", "gif": "image/gif",
    }.get(ext, "image/png")
    return raw, media


# -----------------------------------------------------------------------------
# The authoring engine: the local `claude` CLI in headless mode
# -----------------------------------------------------------------------------

class ClaudeCLI:
    """
    Drives the `claude` command-line tool in print/headless mode for our three
    authoring passes, and keeps the conversation going across passes + repairs.

    Transport details (grounded in the Claude Code headless docs):
      * `claude -p "<prompt>" --output-format json --model <m> --allowedTools Read`
        runs one non-interactive turn, completes any agentic tool calls (e.g.
        reading the image), and prints a single JSON object to stdout.
      * We read `result` (the assistant's final text) and `session_id` from that
        JSON. For every turn after the first we add `--resume <session_id>` so the
        model retains all prior context (including the image it already read).
      * `--allowedTools "Read"` lets the Read tool run without an interactive
        permission prompt; no other tool is permitted, so within bake the CLI can
        view the image but cannot write files or run commands.

    We do NOT set temperature/top_p/top_k -- those are not exposed here and the
    current models are intended to be called without them.
    """

    def __init__(self, model: str, workdir: Path, image_path: Path,
                 claude_bin: str, allowed_tools: str, extra_args: list[str], timeout: int):
        self.model = model
        self.workdir = workdir
        self.claude_bin = claude_bin
        self.allowed_tools = allowed_tools
        self.extra_args = extra_args
        self.timeout = timeout
        self.session_id: str | None = None

        # The CLI has no --image flag, so we copy the photo into the working dir
        # and let Claude Code open it with the Read tool. Read is scoped to the
        # working directory, so a relative name resolves cleanly and is allow-listed.
        ext = image_path.suffix.lower() or ".png"
        self.image_in_workdir = workdir / f"reference{ext}"
        shutil.copy2(image_path, self.image_in_workdir)

        self._check_cli()

    def _check_cli(self) -> None:
        """Fail early and clearly if the CLI isn't installed / runnable."""
        try:
            subprocess.run([self.claude_bin, "--version"],
                           capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            raise FormcastError(
                f"Could not find the Claude CLI ('{self.claude_bin}').\n"
                "Install it and make sure it is on your PATH (or pass --claude-bin):\n"
                "  npm install -g @anthropic-ai/claude-code\n"
                "Then authenticate once by running `claude` interactively.\n"
                "Docs: https://docs.claude.com/en/docs/claude-code/overview"
            )
        except Exception as e:  # noqa: BLE001
            raise FormcastError(f"Failed to run '{self.claude_bin} --version': {e}")

    def ask(self, system: str, text: str, attach_image: bool) -> str:
        """
        Send one turn and return the assistant's final text. `system` is folded
        into the prompt body; when `attach_image` is True we prepend a directive
        telling the model to Read the reference image first.
        """
        parts = [system, ""]
        if attach_image:
            parts.append("First, use the Read tool to view the reference image at "
                         f"this path: {self.image_in_workdir.name}")
            parts.append("")
        parts.append(text)
        prompt = "\n".join(parts)

        cmd = [self.claude_bin, "-p", prompt,
               "--output-format", "json",
               "--model", self.model,
               "--allowedTools", self.allowed_tools]
        if self.session_id is not None:
            cmd += ["--resume", self.session_id]   # continue the same conversation
        cmd += self.extra_args

        log.debug("claude call: model=%s resume=%s attach_image=%s prompt_chars=%d",
                  self.model, self.session_id, attach_image, len(prompt))
        # Log the invocation but elide the huge prompt payload from -p.
        printable = [f"<prompt:{len(prompt)} chars>" if part is prompt else part
                     for part in cmd]
        log.debug("claude argv: %s", " ".join(shlex.quote(p) for p in printable))

        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=str(self.workdir),
                                  capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise FormcastError(f"Claude CLI timed out after {self.timeout}s "
                                "(raise --cli-timeout if your passes are large).")
        elapsed = time.monotonic() - start

        if proc.returncode != 0:
            raise FormcastError(
                f"Claude CLI exited {proc.returncode} after {elapsed:.1f}s.\n"
                f"--- stderr ---\n{proc.stderr.strip()[-2000:]}\n"
                f"--- stdout ---\n{proc.stdout.strip()[-2000:]}"
            )

        out = proc.stdout.strip()
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            raise FormcastError("Could not parse Claude CLI JSON output. Raw stdout:\n"
                                + out[:2000])

        # Capture / refresh the session id so the next turn can --resume it.
        sid = data.get("session_id")
        if sid:
            self.session_id = sid

        # DEBUG diagnostics (best-effort; keys may be absent): wall time vs. the
        # CLI's self-reported duration, how many agent turns it ran, and token /
        # cost usage -- the numbers we need to reason about speed and spend.
        log.debug("claude reply: wall=%.1fs cli_duration_ms=%s turns=%s cost_usd=%s",
                  elapsed, data.get("duration_ms"), data.get("num_turns"),
                  data.get("total_cost_usd"))
        if data.get("usage"):
            log.debug("claude usage: %s", data["usage"])

        result = data.get("result")
        if not isinstance(result, str):
            raise FormcastError(
                "Claude CLI JSON had no 'result' string. "
                f"Top-level keys were: {list(data.keys())}"
            )
        if data.get("is_error"):
            raise FormcastError("Claude CLI reported an error result:\n" + result[:2000])

        # Surface a hint of what the model produced, at INFO, so a normal run shows
        # what's being thought about (full text goes to artifacts / the logfile).
        collapsed = " ".join(result.split())
        log.info("model reply (%d chars): %s%s", len(result),
                 collapsed[:200], "..." if len(collapsed) > 200 else "")
        return result


# -----------------------------------------------------------------------------
# Validation harnesses for the authoring gates
# -----------------------------------------------------------------------------

GEOMETRY_HARNESS = textwrap.dedent("""\
    import importlib.util, sys
    import numpy as np
    import trimesh

    path = sys.argv[1]
    spec = importlib.util.spec_from_file_location("candidate_geometry", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert hasattr(mod, "build_mesh"), "module has no build_mesh()"
    scene = mod.build_mesh(0, "high")
    assert isinstance(scene, trimesh.Scene), f"build_mesh must return trimesh.Scene, got {type(scene)}"
    assert len(scene.geometry) > 0, "scene has no geometry"

    total_faces = 0
    for name, geom in scene.geometry.items():
        total_faces += len(getattr(geom, "faces", []))
    assert total_faces > 0, "scene has zero faces"

    b = scene.bounds
    assert b is not None and np.all(np.isfinite(np.asarray(b))), "non-finite bounds"

    print("GEOMETRY_OK faces=%d surfaces=%s" % (total_faces, sorted(scene.geometry.keys())))
""")


def _validate_geometry(geometry_code: str, workdir: Path) -> tuple[bool, str]:
    """Run the geometry harness against candidate Pass-2 code. -> (ok, message)."""
    mod_path = workdir / "candidate_geometry.py"
    mod_path.write_text(geometry_code)
    harness_path = workdir / "_geometry_harness.py"
    harness_path.write_text(GEOMETRY_HARNESS)
    try:
        proc = _run_python(harness_path, [str(mod_path)], cwd=workdir)
    except subprocess.TimeoutExpired:
        return False, f"Geometry harness timed out after {SUBPROCESS_TIMEOUT_S}s."
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    return False, (proc.stdout + "\n" + proc.stderr).strip()


def _validate_full_script(script_code: str, image_path: Path, workdir: Path) -> tuple[bool, str]:
    """
    Run the full Pass-3 script once (seed 0, high density) and confirm it writes
    a loadable .glb with real geometry. -> (ok, message).
    """
    script_path = workdir / "candidate_generator.py"
    script_path.write_text(script_code)
    out_glb = workdir / "_validate.glb"
    args = ["--image", str(image_path), "--seed", "0", "--density", "high",
            "--output", str(out_glb)]
    try:
        proc = _run_python(script_path, args, cwd=workdir)
    except subprocess.TimeoutExpired:
        return False, f"Generator script timed out after {SUBPROCESS_TIMEOUT_S}s."
    if proc.returncode != 0:
        return False, (proc.stdout + "\n" + proc.stderr).strip()
    if not out_glb.exists() or out_glb.stat().st_size == 0:
        return False, "Script exited 0 but produced no .glb output."
    try:
        scene = trimesh.load(str(out_glb), force="scene")
        faces = sum(len(g.faces) for g in scene.geometry.values())
        if faces == 0:
            return False, "Produced .glb has zero faces."
    except Exception as e:  # noqa: BLE001
        return False, f"Produced .glb failed to load: {e}"
    return True, f"Full script OK ({faces} faces in validation bake)."


# -----------------------------------------------------------------------------
# Authoring passes (with repair loops)
# -----------------------------------------------------------------------------

def pass1_classify(llm: ClaudeCLI) -> dict:
    """Pass 1: classify + describe. Returns the parsed spec dict."""
    log.info("[pass 1] classifying and describing the image ...")
    reply = llm.ask(PASS1_SYSTEM, PASS1_INSTRUCTION, attach_image=True)
    spec = _extract_json(reply)
    for key in ("archetype_id", "class", "description"):
        if key not in spec:
            raise ValueError(f"Pass 1 spec missing '{key}'. Got keys: {list(spec)}")
    spec["archetype_id"] = _sanitize_id(spec["archetype_id"])
    log.info(f"        -> archetype_id='{spec['archetype_id']}' class='{spec['class']}'")
    log.info("        -> description: %s", " ".join(spec["description"].split()))
    return spec


def _author_with_repair(llm: ClaudeCLI, system: str, initial_instruction: str,
                        attach_image: bool, validate, max_repairs: int, label: str) -> str:
    """
    Generic author-then-validate-then-repair loop. Returns validated code or
    raises FormcastError after exhausting repairs.
    """
    instruction = initial_instruction
    attach = attach_image
    for attempt in range(max_repairs + 1):
        reply = llm.ask(system, instruction, attach_image=attach)
        code = _extract_code_block(reply)
        ok, message = validate(code)
        if ok:
            log.info(f"        -> {label} passed validation: {message}")
            return code
        last_line = message.splitlines()[-1] if message else "unknown error"
        log.warning(f"{label} attempt {attempt + 1} failed: {last_line}")
        if attempt == max_repairs:
            raise FormcastError(f"{label} still failing after {max_repairs} repair(s).\n"
                               f"Last error:\n{message}")
        # Ask for a fix; the image is already in the session, no need to resend.
        attach = False
        instruction = textwrap.dedent(f"""\
            That did not work. Running it produced this error:

            ----------------------------------------
            {message}
            ----------------------------------------

            Fix the problem and return the COMPLETE corrected code again, in a
            single ```python block, obeying all the original requirements. Do not
            explain -- just return the corrected code.
            """)
    raise RuntimeError("unreachable")


def pass2_geometry(llm: ClaudeCLI, spec: dict, workdir: Path, max_repairs: int) -> str:
    """Pass 2: author the geometry module, validated by the geometry harness."""
    log.info("[pass 2] authoring procedural geometry ...")
    instruction = PASS2_INSTRUCTION.format(description=spec["description"])
    return _author_with_repair(
        llm, system=PASS2_SYSTEM, initial_instruction=instruction, attach_image=True,
        validate=lambda code: _validate_geometry(code, workdir),
        max_repairs=max_repairs, label="geometry",
    )


def pass3_full_script(llm: ClaudeCLI, spec: dict, geometry_code: str,
                      image_path: Path, workdir: Path, max_repairs: int) -> str:
    """Pass 3: author the complete textured-export script, validated by a real bake."""
    log.info("[pass 3] authoring texturing + GLB export ...")
    instruction = PASS3_INSTRUCTION.format(description=spec["description"],
                                           geometry_code=geometry_code)
    return _author_with_repair(
        llm, system=PASS3_SYSTEM, initial_instruction=instruction, attach_image=True,
        validate=lambda code: _validate_full_script(code, image_path, workdir),
        max_repairs=max_repairs, label="full script",
    )


# -----------------------------------------------------------------------------
# Metadata embedding / reading
# -----------------------------------------------------------------------------

def _build_metadata(spec: dict, generator_code: str, image_b64: str, image_media: str,
                    model: str, variant: dict) -> dict:
    """Assemble the bundle we store in the GLB's top-level `extras`."""
    return {
        "schema_doc": SCHEMA_DOC,
        "description": spec["description"],
        "archetype_id": spec["archetype_id"],
        "class": spec.get("class", "unknown"),
        "variant": variant,                       # {index, seed, density, lod}
        "source_image_b64": {"media_type": image_media, "data": image_b64},
        "generator_script": generator_code,
        "provenance": {
            "tool": "formcast",
            "engine": "claude-cli",
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


def _inject_metadata(glb_path: Path, metadata: dict) -> None:
    """
    Load a .glb, attach `metadata` to its TOP-LEVEL extras, and save in place.
    (Top-level extras round-trips reliably through pygltflib; asset.extras does
    not -- see the header note.)
    """
    gltf = pygltflib.GLTF2().load(str(glb_path))
    existing = gltf.extras if isinstance(gltf.extras, dict) else {}
    existing.update(metadata)
    gltf.extras = existing
    gltf.save(str(glb_path))


def _read_metadata(glb_path: Path) -> dict:
    """Return the top-level extras dict embedded in a .glb (or {} if none)."""
    gltf = pygltflib.GLTF2().load(str(glb_path))
    return gltf.extras if isinstance(gltf.extras, dict) else {}


# -----------------------------------------------------------------------------
# Headless software renderer (no GL needed) + standard views
# -----------------------------------------------------------------------------
# Pure numpy+PIL rasterizer: baseColorTexture, alphaMode MASK + cutoff,
# doubleSided lighting, COLOR_0 vertex-color multiply, perspective-correct UVs.
# It applies scene-graph node transforms (via scene.dump()) -- geometry-local
# vertices alone render transform-bearing GLBs wrongly. Up-axis: formcast bakes
# from prompt_version 1.2+ are +Y-up (glTF convention); 1.0/1.1 bakes were Z-up.

def _yup_to_zup_matrix():
    """Y-up world -> the rasterizer's Z-up camera space: (x, y, z) -> (x, -z, y)."""
    import numpy as np
    return np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])


def _guess_up_axis(glb_path: Path) -> str:
    """'z' for old formcast bakes (prompt_version formcast/1.0-1.1), else 'y'."""
    try:
        meta = _read_metadata(glb_path)
        pv = (meta.get("provenance") or {}).get("prompt_version", "")
        if pv.startswith("formcast/1.0") or pv.startswith("formcast/1.1"):
            return "z"
    except Exception:  # noqa: BLE001 -- unreadable/foreign file: assume spec-compliant
        pass
    return "y"


def _gather_render_meshes(scene, up: str = "y"):
    """Render-ready tuples from a Scene, transforms applied, COLOR_0 extracted."""
    import numpy as np
    out = []
    geoms = scene.dump() if hasattr(scene, "dump") else [scene]
    for geom in geoms:
        if not hasattr(geom, "faces") or len(geom.faces) == 0:
            continue
        v = np.asarray(geom.vertices, dtype=np.float64)
        if up == "y":
            v = v @ _yup_to_zup_matrix().T
        f = np.asarray(geom.faces, dtype=np.int64)
        uv = tex = vcols = None
        amask, cutoff, ds = False, 0.5, False
        vis = geom.visual
        if hasattr(vis, "uv") and vis.uv is not None and len(vis.uv) == len(v):
            uv = np.asarray(vis.uv, dtype=np.float64)
        mat = getattr(vis, "material", None)
        if mat is not None:
            img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
            if img is not None:
                tex = np.asarray(img.convert("RGBA"), dtype=np.uint8)
            amask = getattr(mat, "alphaMode", None) == "MASK"
            c = getattr(mat, "alphaCutoff", None)
            if c is not None:
                cutoff = float(c)
            ds = bool(getattr(mat, "doubleSided", False))
        va = getattr(vis, "vertex_attributes", None)
        if va and "color" in va and len(va["color"]) == len(v):
            vc = np.asarray(va["color"], dtype=np.float64)
            if vc.max() > 1.0:
                vc = vc / 255.0
            vcols = vc[:, :3]
        out.append((v, f, uv, tex, vcols, amask, cutoff, ds))
    return out


def _soft_render(meshes, width=800, height=800, az_deg=-90.0, el_deg=8.0,
                 zoom=1.0, bg=(255, 255, 255)):
    """Rasterize gathered meshes to a PIL Image. Z-up camera space."""
    import numpy as np
    from PIL import Image

    allv = np.vstack([m[0] for m in meshes])
    lo, hi = allv.min(0), allv.max(0)
    center = (lo + hi) / 2.0
    radius = max(float(np.linalg.norm(hi - lo)) / 2.0, 1e-9)

    az, el = np.radians(az_deg), np.radians(el_deg)
    cam_dir = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    cam_pos = center + cam_dir * radius * 2.6 / zoom
    fwd = center - cam_pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 0.0, 1.0])
    n = np.linalg.norm(right)
    right = np.array([1.0, 0.0, 0.0]) if n < 1e-9 else right / n
    up = np.cross(right, fwd)
    fpx = (height / 2.0) / np.tan(np.radians(38.0) / 2.0)

    zbuf = np.full((height, width), np.inf)
    img = np.empty((height, width, 3))
    img[:] = np.asarray(bg, dtype=np.float64)
    l1 = np.array([0.5, -0.6, 0.62]); l1 /= np.linalg.norm(l1)
    l2 = np.array([-0.6, 0.4, 0.3]); l2 /= np.linalg.norm(l2)

    for v, f, uv, tex, vcols, amask, cutoff, ds in meshes:
        rel = v - cam_pos
        cx, cy, cz = rel @ right, rel @ up, rel @ fwd
        ok = cz > radius * 0.05
        sx = width / 2.0 + fpx * cx / cz
        sy = height / 2.0 - fpx * cy / cz
        e1 = v[f[:, 1]] - v[f[:, 0]]
        e2 = v[f[:, 2]] - v[f[:, 0]]
        fn = np.cross(e1, e2)
        nl = np.linalg.norm(fn, axis=1, keepdims=True)
        nl[nl == 0] = 1
        fn = fn / nl

        for ti in range(len(f)):
            i0, i1, i2 = f[ti]
            if not (ok[i0] and ok[i1] and ok[i2]):
                continue
            xs = np.array([sx[i0], sx[i1], sx[i2]])
            ys = np.array([sy[i0], sy[i1], sy[i2]])
            zs = np.array([cz[i0], cz[i1], cz[i2]])
            minx = max(int(np.floor(xs.min())), 0)
            maxx = min(int(np.ceil(xs.max())), width - 1)
            miny = max(int(np.floor(ys.min())), 0)
            maxy = min(int(np.ceil(ys.max())), height - 1)
            if minx > maxx or miny > maxy:
                continue
            d = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
            if abs(d) < 1e-12:
                continue
            gx, gy = np.meshgrid(np.arange(minx, maxx + 1) + 0.5,
                                 np.arange(miny, maxy + 1) + 0.5)
            w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / d
            w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / d
            w2 = 1.0 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any():
                continue
            iz = w0 / zs[0] + w1 / zs[1] + w2 / zs[2]
            zpix = 1.0 / np.maximum(iz, 1e-12)
            sub_z = zbuf[miny:maxy + 1, minx:maxx + 1]
            closer = inside & (zpix < sub_z)
            if not closer.any():
                continue

            if tex is not None and uv is not None:
                u = (w0 * uv[i0, 0] / zs[0] + w1 * uv[i1, 0] / zs[1]
                     + w2 * uv[i2, 0] / zs[2]) * zpix
                vv = (w0 * uv[i0, 1] / zs[0] + w1 * uv[i1, 1] / zs[1]
                      + w2 * uv[i2, 1] / zs[2]) * zpix
                th, tw = tex.shape[:2]
                txi = np.clip((u % 1.0) * (tw - 1), 0, tw - 1).astype(np.int32)
                tyi = np.clip((1.0 - (vv % 1.0)) * (th - 1), 0, th - 1).astype(np.int32)
                texel = tex[tyi, txi].astype(np.float64)
                rgb = texel[..., :3]
                if amask:
                    closer = closer & (texel[..., 3] >= cutoff * 255.0)
                    if not closer.any():
                        continue
            else:
                rgb = np.full(gx.shape + (3,), 185.0)

            if vcols is not None:
                c = (w0[..., None] * vcols[i0] / zs[0]
                     + w1[..., None] * vcols[i1] / zs[1]
                     + w2[..., None] * vcols[i2] / zs[2]) * zpix[..., None]
                rgb = rgb * np.clip(c, 0.0, 1.5)

            nrm = fn[ti]
            lam = max(0.0, nrm @ l1) + (max(0.0, -nrm @ l1) if ds else 0.0)
            lam2 = max(0.0, nrm @ l2) + (max(0.0, -nrm @ l2) if ds else 0.0)
            shade = min(0.45 + 0.45 * min(lam, 1.0) + 0.25 * min(lam2, 1.0), 1.25)

            colored = np.clip(rgb * shade, 0, 255)
            sub_img = img[miny:maxy + 1, minx:maxx + 1]
            sub_img[closer] = colored[closer]
            sub_z[closer] = zpix[closer]

    return Image.fromarray(img.astype("uint8"), "RGB")


STANDARD_VIEWS = [
    ("front", -90.0, 8.0, 1.0),
    ("side", 0.0, 8.0, 1.0),
    ("threequarter", -45.0, 30.0, 1.05),
    ("closeup", -70.0, 12.0, 2.1),
]


def _render_glb_views(glb_path: Path, out_dir: Path, stem: str, up: str = "auto",
                      width: int = 700, height: int = 800) -> list[Path]:
    """Render the four standard views + a contact sheet (returned last)."""
    from PIL import Image
    if up == "auto":
        up = _guess_up_axis(glb_path)
    scene = trimesh.load(str(glb_path), force="scene")
    meshes = _gather_render_meshes(scene, up=up)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for tag, az, el, zoom in STANDARD_VIEWS:
        im = _soft_render(meshes, width=width, height=height, az_deg=az,
                          el_deg=el, zoom=zoom)
        p = out_dir / f"{stem}-{tag}.png"
        im.save(p)
        paths.append(p)
    sheet = Image.new("RGB", (width * len(paths), height), "white")
    for i, p in enumerate(paths):
        sheet.paste(Image.open(p), (i * width, 0))
    sp = out_dir / f"{stem}-contact.png"
    sheet.save(sp)
    paths.append(sp)
    return paths


# -----------------------------------------------------------------------------
# VLM judge: photo + two render sheets -> preference + rubric (fresh sessions)
# -----------------------------------------------------------------------------

JUDGE_PROMPT = textwrap.dedent("""\
    You are an impartial judge of 3D-model quality for a procedural asset
    pipeline. Use the Read tool to view, in this order:
      1. photo.png    - the reference photograph
      2. render_a.png - renders of 3D model A (multiple angles in one sheet)
      3. render_b.png - renders of 3D model B (multiple angles in one sheet)

    Both models were generated from the photograph and aim to represent the
    KIND of object in it (shape character, proportions, surfaces, colors) -
    not a pixel-perfect copy. Judge which model is the better 3D representation.

    Return ONLY a JSON object (no prose, no code fences):
    {"preferred": "A" or "B",
     "why": "<one or two sentences>",
     "rubric": {"A": {"silhouette": 1-5, "proportions": 1-5, "surface_detail": 1-5,
                       "color_material": 1-5, "artifacts": 1-5},
                "B": {same keys}}}
    ("artifacts": 5 = clean, 1 = badly broken geometry/texture.)""")


def _judge_pair(photo: Path, a_png: Path, b_png: Path, trials: int = 3,
                model: str = "sonnet", claude_bin: str = "claude",
                timeout: int = 240) -> dict:
    """Fresh-session VLM judge. Alternates which model is labelled A per trial
    (position-bias control). Returns how often B (the 'candidate') won."""
    results = []
    for t in range(trials):
        swap = (t % 2 == 1)
        with tempfile.TemporaryDirectory(prefix="formcast_judge_") as td:
            tdp = Path(td)
            shutil.copy2(photo, tdp / "photo.png")
            shutil.copy2(b_png if swap else a_png, tdp / "render_a.png")
            shutil.copy2(a_png if swap else b_png, tdp / "render_b.png")
            cmd = [claude_bin, "-p", JUDGE_PROMPT, "--output-format", "json",
                   "--model", model, "--allowedTools", "Read"]
            start = time.monotonic()
            try:
                proc = subprocess.run(cmd, cwd=td, capture_output=True,
                                      text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                results.append({"error": f"judge timed out after {timeout}s"})
                continue
            wall = time.monotonic() - start
            if proc.returncode != 0:
                results.append({"error": proc.stderr.strip()[-400:]})
                continue
            try:
                data = json.loads(proc.stdout)
                verdict = _extract_json(data.get("result", ""))
            except Exception as e:  # noqa: BLE001
                results.append({"error": f"unparseable verdict: {e}"})
                continue
            pref_b = (verdict.get("preferred") == "A") == swap
            results.append({"prefers_candidate": bool(pref_b), "swap": swap,
                            "why": verdict.get("why", ""),
                            "rubric": verdict.get("rubric", {}),
                            "cost_usd": data.get("total_cost_usd"),
                            "wall_s": round(wall, 1)})
            log.debug("judge trial %d: prefers_candidate=%s (%.1fs, $%s)",
                      t, pref_b, wall, data.get("total_cost_usd"))
    wins = sum(1 for r in results if r.get("prefers_candidate"))
    valid = sum(1 for r in results if "prefers_candidate" in r)
    return {"candidate_wins": wins, "valid_trials": valid, "trials": results}


def cmd_judge(args: argparse.Namespace) -> int:
    photo, a, b = Path(args.photo), Path(args.a), Path(args.b)
    for p in (photo, a, b):
        if not p.exists():
            log.error(f"file not found: {p}")
            return 2
    out = _judge_pair(photo, a, b, trials=args.trials, model=args.model,
                      claude_bin=args.claude_bin)
    print(json.dumps(out, indent=1))
    log.info("judge: candidate (B) preferred %d/%d",
             out["candidate_wins"], out["valid_trials"])
    return 0


# -----------------------------------------------------------------------------
# Subcommand: bake
# -----------------------------------------------------------------------------

def cmd_bake(args: argparse.Namespace) -> int:
    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        log.error(f"image not found: {image_path}")
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # The full-res original is what gets embedded in the .glb and what the bake
    # script reads for texture extraction.
    image_raw, image_media = _load_image_bytes(image_path)
    image_raw_b64 = base64.b64encode(image_raw).decode("ascii")

    extra_args = shlex.split(args.claude_extra) if args.claude_extra else []

    # All authoring + validation happens in a scratch dir so failures stay local.
    bake_start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="formcast_") as tmp:
        workdir = Path(tmp)

        llm = ClaudeCLI(
            model=args.model, workdir=workdir, image_path=image_path,
            claude_bin=args.claude_bin, allowed_tools=args.allowed_tools,
            extra_args=extra_args, timeout=args.cli_timeout,
        )

        # ---- Passes 1-3 (authoring with gates) -----------------------------
        t0 = time.monotonic()
        spec = pass1_classify(llm)
        log.debug("pass 1 (classify) finished in %.1fs", time.monotonic() - t0)

        t0 = time.monotonic()
        geometry_code = pass2_geometry(llm, spec, workdir, args.max_repairs)
        log.debug("pass 2 (geometry) finished in %.1fs", time.monotonic() - t0)

        t0 = time.monotonic()
        generator_code = pass3_full_script(
            llm, spec, geometry_code, image_path, workdir, args.max_repairs
        )
        log.debug("pass 3 (texturing+export) finished in %.1fs", time.monotonic() - t0)

        archetype_id = spec["archetype_id"]

        # Save the authored artifacts next to the output, so you can inspect /
        # hand-edit and re-bake without re-calling the model.
        script_path = out_dir / f"{archetype_id}.generator.py"
        script_path.write_text(generator_code)
        (out_dir / f"{archetype_id}.description.txt").write_text(spec["description"])
        log.info(f"        -> saved generator script: {script_path.name}")

        # ---- Pass 4: deterministic bake ------------------------------------
        if args.lods:
            density_plan = [(d, LOD_FOR_DENSITY[d]) for d in DENSITY_LEVELS]
        else:
            density_plan = [(args.density, LOD_FOR_DENSITY.get(args.density, 0))]

        log.info(f"[pass 4] baking {args.count} variant(s)"
                + (f" x {len(density_plan)} LOD level(s)" if args.lods else "") + " ...")

        produced: list[Path] = []
        for idx in range(args.count):
            seed = idx  # seeds 0..count-1; reproducible and easy to reason about
            for density, lod in density_plan:
                stem = f"{archetype_id}-{idx:02d}"
                if args.lods:
                    stem += f"-lod{lod}"
                glb_path = out_dir / f"{stem}.glb"

                bake_args = ["--image", str(image_path), "--seed", str(seed),
                             "--density", density, "--output", str(glb_path)]
                variant_start = time.monotonic()
                proc = _run_python(script_path, bake_args, cwd=out_dir)
                if proc.returncode != 0 or not glb_path.exists():
                    log.error(f"variant {stem} failed to bake:\n"
                            f"{(proc.stdout + proc.stderr).strip()[-800:]}")
                    continue

                variant = {"index": idx, "seed": seed, "density": density, "lod": lod}
                metadata = _build_metadata(
                    spec, generator_code, image_raw_b64, image_media, args.model, variant
                )
                _inject_metadata(glb_path, metadata)
                produced.append(glb_path)
                log.info(f"        -> {glb_path.name}")
                log.debug("baked %s in %.1fs", glb_path.name,
                          time.monotonic() - variant_start)

    if not produced:
        log.error("No models were produced. Inspect the errors above.")
        return 1

    log.info("Done. %d model(s) written to %s in %.1fs",
             len(produced), out_dir, time.monotonic() - bake_start)
    log.info("Preview them all with:\n  python %s view %s/%s-*.glb",
             Path(sys.argv[0]).name, out_dir, archetype_id)
    return 0


# -----------------------------------------------------------------------------
# Subcommand: inspect
# -----------------------------------------------------------------------------

def cmd_inspect(args: argparse.Namespace) -> int:
    glb_path = Path(args.glb).expanduser().resolve()
    if not glb_path.exists():
        log.error(f"file not found: {glb_path}")
        return 2

    meta = _read_metadata(glb_path)
    if not meta:
        print(f"{glb_path.name}: no formcast metadata found in top-level extras.")
        return 0

    img = meta.get("source_image_b64") or {}
    img_bytes = len(img.get("data", "")) * 3 // 4  # approx decoded size
    script = meta.get("generator_script", "")
    prov = meta.get("provenance", {})
    var = meta.get("variant", {})

    print(f"File:         {glb_path.name}")
    print(f"Archetype:    {meta.get('archetype_id', '?')}  (class: {meta.get('class', '?')})")
    print(f"Variant:      index={var.get('index')} seed={var.get('seed')} "
          f"density={var.get('density')} lod={var.get('lod')}")
    print(f"Provenance:   tool={prov.get('tool')} engine={prov.get('engine')} "
          f"model={prov.get('model')} prompts={prov.get('prompt_version')} "
          f"created={prov.get('created_utc')}")
    print(f"Embedded:     image ~{img_bytes/1024:.1f} KB ({img.get('media_type', '?')}), "
          f"generator script {len(script)} chars")
    print("\nDescription:")
    print(textwrap.fill(meta.get("description", ""), width=88,
                        initial_indent="  ", subsequent_indent="  "))

    if args.json:
        trimmed = dict(meta)
        if "source_image_b64" in trimmed:
            d = dict(trimmed["source_image_b64"])
            d["data"] = f"<{img_bytes} bytes base64-omitted>"
            trimmed["source_image_b64"] = d
        if "generator_script" in trimmed:
            trimmed["generator_script"] = f"<{len(script)} chars omitted>"
        print("\nRaw metadata (blobs omitted):")
        print(json.dumps(trimmed, indent=2))

    if args.extract:
        out = Path(args.extract).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        stem = glb_path.stem
        if img.get("data"):
            ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(
                img.get("media_type"), "png")
            img_out = out / f"{stem}.source.{ext}"
            img_out.write_bytes(base64.b64decode(img["data"]))
            print(f"\nExtracted image:  {img_out}")
        if script:
            scr_out = out / f"{stem}.generator.py"
            scr_out.write_text(script)
            print(f"Extracted script: {scr_out}")
        if meta.get("description"):
            desc_out = out / f"{stem}.description.txt"
            desc_out.write_text(meta["description"])
            print(f"Extracted prose:  {desc_out}")

    return 0


# -----------------------------------------------------------------------------
# Subcommand: view
# -----------------------------------------------------------------------------

def _expand_paths(patterns: list[str]) -> list[Path]:
    """
    Expand the view arguments into a sorted, de-duplicated list of .glb files.
    Accepts explicit files, directories (-> all .glb inside), and glob patterns
    (expanded here too, in case the shell didn't).
    """
    found: list[Path] = []
    for pat in patterns:
        p = Path(pat).expanduser()
        if p.is_dir():
            found.extend(sorted(p.glob("*.glb")))
        elif any(ch in pat for ch in "*?[]"):
            found.extend(Path(m) for m in globmod.glob(os.path.expanduser(pat)))
        elif p.exists():
            found.append(p)
        else:
            log.warning(f"no match for '{pat}'")
    uniq = sorted({fp.resolve() for fp in found})
    return uniq


def _compose_row(paths: list[Path]) -> trimesh.Scene:
    """
    Load each .glb and lay them out left-to-right in a single scene, preserving
    each model's materials/textures. The combined scene is ephemeral -- we never
    write it to disk (storage stays one lean file per model; this is just for the
    eyes). Gap between models scales with the largest model's width.
    """
    loaded_lists: list[list[trimesh.Trimesh]] = []
    widths: list[float] = []
    for path in paths:
        scene = trimesh.load(str(path), force="scene")
        meshes = [g for g in scene.dump() if hasattr(g, "vertices")]
        loaded_lists.append(meshes)
        if scene.bounds is not None:
            widths.append(float(scene.bounds[1][0] - scene.bounds[0][0]))
        else:
            widths.append(1.0)

    gap = (max(widths) if widths else 1.0) * 0.4
    combined = trimesh.Scene()
    offset = 0.0
    for path, meshes, width in zip(paths, loaded_lists, widths):
        if not meshes:
            continue
        min_x = min(float(m.bounds[0][0]) for m in meshes)
        for m in meshes:
            mm = m.copy()
            mm.apply_translation([offset - min_x, 0.0, 0.0])
            combined.add_geometry(mm, geom_name=f"{path.stem}:{len(combined.geometry)}")
        offset += width + gap
    return combined


def cmd_view(args: argparse.Namespace) -> int:
    paths = _expand_paths(args.paths)
    if not paths:
        log.error("no .glb files matched the given paths.")
        return 2

    log.info(f"Loading {len(paths)} model(s):")
    for p in paths:
        log.info(f"  {p.name}")

    scene = _compose_row(paths) if len(paths) > 1 else trimesh.load(str(paths[0]), force="scene")

    if args.save:
        out = Path(args.save).expanduser().resolve()
        png = None
        if args.renderer in ("auto", "gl"):
            try:
                png = scene.save_image(resolution=(args.width, args.height), visible=True)
            except Exception as e:  # noqa: BLE001
                if args.renderer == "gl":
                    log.error("GL off-screen render failed (%s). This machine "
                              "likely has no display; use --renderer soft.", e)
                    return 1
                log.info("GL renderer unavailable (%s); falling back to the "
                         "built-in software renderer.", type(e).__name__)
        if png is None:
            # Software path: works headless. Up-axis from the first file's
            # provenance (old formcast bakes are Z-up, 1.2+ and foreign are Y-up).
            up = _guess_up_axis(paths[0])
            meshes = _gather_render_meshes(scene, up=up)
            im = _soft_render(meshes, width=args.width, height=args.height,
                              az_deg=-90.0, el_deg=8.0, zoom=1.0)
            im.save(out)
            log.info("Saved render (software, up=%s): %s", up, out)
            return 0
        out.write_bytes(png)
        log.info("Saved render: %s", out)
        return 0

    try:
        scene.show()
    except Exception as e:  # noqa: BLE001
        log.error("could not open an interactive 3D window -- no display / "
                f"OpenGL available here.\n  ({e})\n"
                "Use `--save out.png` instead: it renders headlessly via the "
                "built-in software renderer.")
        return 1
    return 0


# -----------------------------------------------------------------------------
# Argument parser
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="formcast",
        description="Turn a reference photo into a small library of static, "
                    "seed-varied procedural GLB models (via the local Claude CLI "
                    "in headless mode); inspect their embedded metadata; and "
                    "preview them in 3D.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Logging flags shared by every subcommand. INFO to stdout by default; the
    # logfile always captures full DEBUG. -v/--verbose also shows DEBUG on stdout.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="store_true",
                        help="show DEBUG detail on stdout (the logfile always has it)")
    common.add_argument("--log-file", default=DEFAULT_LOG_FILE,
                        help=f"file to tee logs into (default: {DEFAULT_LOG_FILE})")

    sub = p.add_subparsers(dest="command", required=True)

    # bake -------------------------------------------------------------------
    b = sub.add_parser("bake", parents=[common],
                       help="image -> procedural .glb variants (the main command)")
    b.add_argument("image", help="path to the reference photo")
    b.add_argument("--out-dir", default="archetypes",
                   help="directory for output .glb files (default: ./archetypes)")
    b.add_argument("--count", type=int, default=DEFAULT_COUNT,
                   help=f"number of variants to bake (default: {DEFAULT_COUNT})")
    b.add_argument("--density", choices=DENSITY_LEVELS, default=DEFAULT_DENSITY,
                   help=f"detail level when not using --lods (default: {DEFAULT_DENSITY})")
    b.add_argument("--lods", action="store_true",
                   help="also bake a high/med/low LOD chain per variant "
                        "(filenames gain -lod0/-lod1/-lod2)")
    b.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"model for --model on the CLI; alias or full id "
                        f"(default: {DEFAULT_MODEL})")
    b.add_argument("--claude-bin", default=DEFAULT_CLAUDE_BIN,
                   help=f"the Claude Code executable (default: {DEFAULT_CLAUDE_BIN})")
    b.add_argument("--allowed-tools", default=DEFAULT_ALLOWED_TOOLS, dest="allowed_tools",
                   help=f"value for --allowedTools (default: {DEFAULT_ALLOWED_TOOLS})")
    b.add_argument("--claude-extra", default="",
                   help="extra flags passed through to every claude call, as a "
                        "single string (e.g. \"--dangerously-skip-permissions\")")
    b.add_argument("--cli-timeout", type=int, default=CLI_TIMEOUT_S,
                   help=f"seconds to allow per CLI call (default: {CLI_TIMEOUT_S})")
    b.add_argument("--max-repairs", type=int, default=DEFAULT_MAX_REPAIRS,
                   help=f"times to ask the model to fix a failing pass "
                        f"(default: {DEFAULT_MAX_REPAIRS})")
    b.set_defaults(func=cmd_bake)

    # inspect ----------------------------------------------------------------
    i = sub.add_parser("inspect", parents=[common],
                       help="print the embedded metadata of a .glb")
    i.add_argument("glb", help="path to a .glb produced by `bake`")
    i.add_argument("--json", action="store_true",
                   help="also dump the raw metadata as JSON (big blobs omitted)")
    i.add_argument("--extract", metavar="DIR",
                   help="extract the embedded source image, generator script, "
                        "and prose into DIR")
    i.set_defaults(func=cmd_inspect)

    # view -------------------------------------------------------------------
    v = sub.add_parser("view", parents=[common],
                       help="render one .glb, or many laid out in a row")
    v.add_argument("paths", nargs="+",
                   help="one or more .glb files, a directory, or a glob "
                        "(e.g. outputs/maple-tree-*.glb)")
    v.add_argument("--save", metavar="PNG",
                   help="render to this PNG instead of opening a window "
                        "(needs OpenGL, works off-screen on most setups)")
    v.add_argument("--width", type=int, default=1600, help="render width for --save")
    v.add_argument("--height", type=int, default=900, help="render height for --save")
    v.add_argument("--renderer", choices=["auto", "gl", "soft"], default="auto",
                   help="--save backend: GL when available, else the built-in "
                        "software rasterizer (default: auto)")
    v.set_defaults(func=cmd_view)

    # judge ------------------------------------------------------------------
    j = sub.add_parser("judge", parents=[common],
                       help="VLM-judge two render sheets against a reference photo")
    j.add_argument("photo", help="reference photograph")
    j.add_argument("a", help="render sheet of model A (the baseline)")
    j.add_argument("b", help="render sheet of model B (the candidate)")
    j.add_argument("--trials", type=int, default=3,
                   help="judging trials; A/B labels alternate per trial (default: 3)")
    j.add_argument("--model", default="sonnet",
                   help="judge model for the CLI (default: sonnet -- cheap)")
    j.add_argument("--claude-bin", default=DEFAULT_CLAUDE_BIN,
                   help=f"the Claude Code executable (default: {DEFAULT_CLAUDE_BIN})")
    j.set_defaults(func=cmd_judge)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose, args.log_file)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        log.error("interrupted by user")
        return 130
    except FormcastError as e:
        log.error("%s", e)
        return 1
    except Exception:  # noqa: BLE001 -- last-resort net; full traceback to the log
        log.exception("unexpected error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
