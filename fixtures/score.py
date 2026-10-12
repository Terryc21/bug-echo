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
it reads verdicts from Markdown table rows, labeled bullets, and finding sections,
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


def parse_report(text):
    """Return {(basename, line): verdict} for every file:line citation found."""
    found = {}
    priorities = {}
    section = None
    fenced = False
    verdict_re = r"(OK\s*\(CANON(?:,[^)]*)?\)|CANON|BUG|WATCH|OK|REVIEW)(?=\W|$)"
    citation_re = r"([\w/\.\-]+\.(?:swift|tsx?|jsx?)):(\d+)"
    for raw in text.splitlines():
        if raw.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
            continue
        if fenced:
            continue
        plain = raw.replace('**', '').replace('`', '').strip()
        heading = re.match(r'^#{1,6}\s+(.+)', plain)
        if heading:
            title = heading.group(1)
            tag = re.match(verdict_re, title, re.I)
            section = normalize(tag.group(1)) if tag else None
            if re.match(r'reference implementation', title, re.I):
                section = 'CANON'
        matches = list(re.finditer(citation_re, plain))
        if not matches:
            continue
        # Validation/baseline citations are evidence about old code, not findings.
        if re.search(r'HEAD(?:[~^:]|\b)|git show|pre-fix|validation:', plain, re.I):
            continue
        verdict, priority = section, 1
        cells = [cell.strip() for cell in plain.strip('|').split('|')]
        table_tag = next((re.match(verdict_re, cell, re.I) for cell in cells
                          if re.match(verdict_re, cell, re.I)), None) if '|' in plain else None
        direct = re.match(r'^[-*]?\s*' + verdict_re, plain, re.I)
        after = re.match(r'^[\s:–—\-\d]*' + verdict_re, plain[matches[0].end():], re.I)
        tag = table_tag or direct or after
        if tag:
            verdict, priority = normalize(tag.group(1)), 3
        elif re.search(r'reference implementation', plain, re.I):
            verdict, priority = 'CANON', 2
        elif re.search(r'suggested fix|mirror |see |baseline', plain, re.I):
            continue
        if verdict:
            for match in matches:
                key = (os.path.basename(match.group(1)), int(match.group(2)))
                if priority > priorities.get(key, 0):
                    found[key], priorities[key] = verdict, priority
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
    lenient = {tuple(p) for p in key["tolerance"].get("lenient_pairs", [])}

    failures, notes, passes = [], [], []

    for site in key["sites"]:
        base = os.path.basename(site["file"])
        want = site["expect"]
        accepted = {want} | set(site.get("also_accept", []))

        # Exact line first, then a small window. A citation can legitimately
        # point at a function signature rather than the offending line inside
        # it -- a CANON site especially, since "the shape to converge on" is
        # arguably the whole function. Failing that as MISSING understates a
        # correct identification, which is what happened on this fixture's
        # first real run (SafeStore :22 vs :24, both defensible).
        got = actual.get((base, site["line"]))
        matched_line = site["line"]
        if got is None:
            tolerance = site.get("line_tolerance", 3)
            for offset in range(1, tolerance + 1):
                for cand in (site["line"] - offset, site["line"] + offset):
                    if (base, cand) in actual:
                        got = actual[(base, cand)]
                        matched_line = cand
                        break
                if got is not None:
                    break
            if got is not None and matched_line != site["line"]:
                notes.append(
                    f"○ {base}:{matched_line}  cited instead of :{site['line']} "
                    f"(within tolerance) -> {got}"
                )

        if got is None:
            if site.get("optional"):
                notes.append(f"○ {base}:{site['line']}  absent (optional site -- see note in key)")
            else:
                failures.append(f"✘ {base}:{site['line']}  MISSING from report (expected {want})")
            continue

        alternate = any(
            verdict == "CANON" and base_name == os.path.basename(ref["file"])
            and abs(line_num - ref["line"]) <= ref.get("line_tolerance", 3)
            for ref in site.get("alternate_canon", [])
            for (base_name, line_num), verdict in actual.items()
        )
        if want == "CANON" and got == "OK" and alternate:
            passes.append(f"✔ {base}:{site['line']}  OK (another valid CANON selected)")
        elif got in accepted:
            passes.append(f"✔ {base}:{site['line']}  {got}")
        elif (want, got) in strict or (want, got) not in lenient:
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
            if v in banned.get("forbidden_verdicts", ("BUG", "WATCH", "CANON")):
                failures.append(f"✘ {b}:{l}  flagged {v} but must not be flagged -- {banned['because'][:70]}")

    print(f"\nbug-echo fixture: {key['fixture']}  ({key['language']})")
    print(f"pattern: {key['pattern']}\n")
    for line in passes + notes + failures:
        print("  " + line)

    total = len(key["sites"])
    print(f"\n  {len(passes)}/{total} accepted · {len(notes)} note(s) · {len(failures)} failure(s)")
    print(f"\n  Scope: classification verified on {key['language'].upper()} only "
          f"({total} sites, 1 fixture). NOT verified on any other language.")

    if failures:
        print("\n❌ FAIL\n")
        return 1
    print("\n✅ PASS" + (" (with notes)" if notes else "") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
