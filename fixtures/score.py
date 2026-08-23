#!/usr/bin/env python3
"""
score.py -- compare a bug-echo report against a fixture's answer key.

WHY: bug-echo is LLM-driven, so two runs on identical input produce different
prose. Comparing reports as text would be flaky and useless. This compares
VERDICTS ONLY -- the BUG / WATCH / OK / CANON label attached to each file:line
-- and ignores wording entirely.

TOLERANCE (set per-fixture in answer-key.json, not here):
  strict   BUG<->OK and anything<->CANON always FAIL. A bug scored OK is a real
           miss; a wrong CANON points every other finding at the wrong answer.
  lenient  BUG<->WATCH and WATCH<->OK are NOTES, never failures. That boundary
           is honest judgment, and failing on it produces a flaky suite -- and
           a flaky suite gets ignored, which is worse than no suite.

USAGE:
    python3 fixtures/score.py <report-file> [fixture-name]

The report file is whatever bug-echo produced: a saved .agents/research/ report
or an inline report pasted into a file. Parsing is deliberately forgiving --
it looks for `path/to/File.swift:NN` citations and the nearest verdict word,
because the report format is prose for humans, not a machine format (SKILL.md
Step 5 says so explicitly, and says not to emit a JSON sidecar).

EXIT: 0 if every strict check passed, 1 otherwise.
"""

import json
import os
import re
import sys

VERDICTS = ("CANON", "BUG", "WATCH", "OK", "REVIEW")


def load_key(fixture_dir):
    path = os.path.join(fixture_dir, "answer-key.json")
    if not os.path.isfile(path):
        sys.exit(f"❌ No answer key at {path}")
    with open(path) as f:
        return json.load(f)


def normalize(verdict):
    """`OK (CANON)` and `CANON` are the same verdict."""
    v = verdict.upper()
    return "CANON" if "CANON" in v else v


def find_verdict_near(text, idx, window=400):
    """
    Find the verdict word closest to a citation.

    Looks backward first: in both report formats the classification heading or
    table cell precedes the file:line citation. Falls back to a forward look.

    ⚠️ The `**Reference implementation:**` line is checked FIRST and wins. It is
    how SKILL.md Step 5 renders a CANON site, and it usually sits directly under
    a "## BUG Findings" heading -- so a naive backward scan reads the heading and
    scores the reference implementation as a BUG. Caught by the harness's own
    positive control on the first run.
    """
    line_start = text.rfind("\n", 0, idx) + 1
    line_end = text.find("\n", idx)
    line = text[line_start:line_end if line_end != -1 else len(text)]
    if re.search(r"reference\s+implementation", line, re.I):
        return "CANON"

    before = text[max(0, idx - window):idx]
    for m in reversed(list(re.finditer(r"\b(OK\s*\(CANON\)|CANON|BUG|WATCH|OK|REVIEW)\b", before))):
        return normalize(m.group(1))
    after = text[idx:idx + window]
    m = re.search(r"\b(OK\s*\(CANON\)|CANON|BUG|WATCH|OK|REVIEW)\b", after)
    return normalize(m.group(1)) if m else None


def parse_report(text):
    """Return {(basename, line): verdict} for every file:line citation found."""
    found = {}
    for m in re.finditer(r"([\w/\.\-]+\.swift):(\d+)", text):
        basename = os.path.basename(m.group(1))
        line = int(m.group(2))
        verdict = find_verdict_near(text, m.start())
        if verdict:
            found.setdefault((basename, line), verdict)
    return found


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    report_path = sys.argv[1]
    fixture = sys.argv[2] if len(sys.argv) > 2 else "swift-try-fetch"
    fixture_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), fixture)

    if not os.path.isfile(report_path):
        sys.exit(f"❌ No report at {report_path}")

    key = load_key(fixture_dir)
    with open(report_path) as f:
        actual = parse_report(f.read())

    strict = {tuple(p) for p in key["tolerance"]["strict_pairs"]}

    failures, notes, passes = [], [], []

    for site in key["sites"]:
        base = os.path.basename(site["file"])
        want = site["expect"]
        got = actual.get((base, site["line"]))
        accepted = {want} | set(site.get("also_accept", []))

        if got is None:
            if site.get("optional"):
                notes.append(f"○ {base}:{site['line']}  absent (optional site -- see note in key)")
            else:
                failures.append(f"✘ {base}:{site['line']}  MISSING from report (expected {want})")
            continue

        if got in accepted:
            passes.append(f"✔ {base}:{site['line']}  {got}")
        elif (want, got) in strict:
            failures.append(f"✘ {base}:{site['line']}  got {got}, expected {want}  [strict]")
        else:
            notes.append(f"○ {base}:{site['line']}  got {got}, expected {want}  [lenient -- judgment call]")

    for banned in key.get("must_not_flag", []):
        base = os.path.basename(banned["file"])
        hits = [(b, l) for (b, l) in actual if b == base]
        if "line" in banned:
            hits = [(b, l) for (b, l) in hits if l == banned["line"]]
        for b, l in hits:
            v = actual[(b, l)]
            if v in ("BUG", "WATCH", "CANON"):
                failures.append(f"✘ {b}:{l}  flagged {v} but must not be flagged -- {banned['because'][:70]}")

    print(f"\nbug-echo fixture: {key['fixture']}  ({key['language']})")
    print(f"pattern: {key['pattern']}\n")
    for line in passes + notes + failures:
        print("  " + line)

    total = len(key["sites"])
    print(f"\n  {len(passes)}/{total} exact · {len(notes)} note(s) · {len(failures)} failure(s)")
    print(f"\n  Scope: classification verified on {key['language'].upper()} only "
          f"({total} sites, 1 fixture). NOT verified on any other language.")

    if failures:
        print("\n❌ FAIL\n")
        return 1
    print("\n✅ PASS" + (" (with notes)" if notes else "") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
