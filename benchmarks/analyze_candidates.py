#!/usr/bin/env python3
"""Score benchmark candidate photos for 'simple template' suitability.

This is also the prototype of formcast's Pass-0 preflight: background mask via
alpha channel or border-median tolerance, content fraction, blob count, border
uniformity. Higher score = better single-object-on-plain-background template.

Run from repo root: python3 benchmarks/analyze_candidates.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def analyze(path):
    im = Image.open(path)
    has_alpha = im.mode in ("RGBA", "LA", "PA")
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32)
    h, w = rgb.shape[:2]
    if min(h, w) < 350:
        return {"file": str(path), "score": 0, "reason": f"too small {w}x{h}"}

    if has_alpha:
        a = np.asarray(im.convert("RGBA"), dtype=np.float32)[..., 3]
        fg = a > 128
        border_std = 0.0  # alpha cutout: background is perfect
    else:
        frame = np.concatenate([rgb[:12].reshape(-1, 3), rgb[-12:].reshape(-1, 3),
                                rgb[:, :12].reshape(-1, 3), rgb[:, -12:].reshape(-1, 3)])
        med = np.median(frame, axis=0)
        border_std = float(frame.std(axis=0).mean())
        fg = (np.abs(rgb - med).max(axis=2) > 38)
        fg = ndimage.binary_opening(fg, iterations=2)

    content = float(fg.mean())
    lbl, ncomp = ndimage.label(fg)
    if ncomp:
        sizes = ndimage.sum(fg, lbl, range(1, ncomp + 1))
        main_frac = float(sizes.max() / max(fg.sum(), 1))
        big = int((sizes > fg.sum() * 0.02).sum())
    else:
        main_frac, big = 0.0, 0

    ys, xs = np.where(fg)
    aspect = float((xs.max() - xs.min() + 1) / (ys.max() - ys.min() + 1)) if len(xs) else 0

    # scoring: plain border, one dominant blob, content 8-75%, decent res
    score = 0.0
    score += max(0, 1 - border_std / 60) * 30          # uniform background
    score += main_frac * 30                            # single object
    score += (1 if big <= 2 else max(0, 1 - 0.2 * (big - 2))) * 10
    score += (1 if 0.08 <= content <= 0.75 else 0.3) * 20
    score += min(min(h, w) / 1000, 1) * 10             # resolution
    return {"file": str(path), "score": round(score, 1), "size": f"{w}x{h}",
            "alpha": has_alpha, "border_std": round(border_std, 1),
            "content": round(content, 2), "main_frac": round(main_frac, 2),
            "blobs>2%": big, "aspect": round(aspect, 2)}


def main():
    base = Path(__file__).parent / "cache" / "candidates"
    for klass in sorted(p.name for p in base.iterdir() if p.is_dir()):
        rows = []
        for f in sorted((base / klass).glob("*.[jp][pn]g")):
            try:
                rows.append(analyze(f))
            except Exception as e:
                rows.append({"file": str(f), "score": 0, "reason": str(e)})
        rows.sort(key=lambda r: -r["score"])
        print(f"\n== {klass} ==")
        for r in rows:
            print(" ", json.dumps(r))


if __name__ == "__main__":
    main()
