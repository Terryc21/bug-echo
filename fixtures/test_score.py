"""Regression checks for actual report shapes; no model output text matching."""
import unittest
import subprocess
import sys
import tempfile
from pathlib import Path
from score import parse_report


class ReportParsing(unittest.TestCase):
    def test_table_verdict_belongs_to_its_own_row(self):
        text = '''| Site | Classification | Evidence |
| `src/Bad.swift:22` | **BUG** | silently discards error |
| `src/Cache.swift:25` | **WATCH** | non-authoritative cache |
| `src/Tests.swift:13` | **OK** | intentionally accepts nil |
| `src/Safe.swift:24` | **OK (CANON)** | catches error |
| `src/Seed.swift:18` | **OK — original fix** | handled |
'''
        self.assertEqual(parse_report(text), {
            ('Bad.swift', 22): 'BUG', ('Cache.swift', 25): 'WATCH',
            ('Tests.swift', 13): 'OK', ('Safe.swift', 24): 'CANON',
            ('Seed.swift', 18): 'OK'})

    def test_historical_and_example_citations_are_not_findings(self):
        text = '''**BUG** inferred from the fix.
- **Validation:** matched `HEAD^:src/Seed.swift:18`.
```markdown
## BUG Findings
`src/Example.swift:30`
```
'''
        self.assertEqual(parse_report(text), {})

    def test_same_line_ok_beats_previous_canon(self):
        text = '''## OK Findings
- `src/Safe.swift:22`: **OK (CANON).** It catches the error.
- `src/Seed.swift:15`: **OK.** The fix is applied.
'''
        self.assertEqual(parse_report(text), {('Safe.swift', 22): 'CANON', ('Seed.swift', 15): 'OK'})

    def test_reference_is_not_bug_because_of_enclosing_section(self):
        text = '''## BUG Findings
**Reference implementation:** `src/Safe.swift:24`
**1. `src/Bad.swift:22`**
Suggested fix: mirror `src/Safe.swift:24`.
'''
        self.assertEqual(parse_report(text), {('Safe.swift', 24): 'CANON', ('Bad.swift', 22): 'BUG'})

    def test_typescript_and_negative_control(self):
        text = '| `src/SaveJobs.ts:7` | **BUG** | returns too soon |'
        self.assertEqual(parse_report(text), {('SaveJobs.ts', 7): 'BUG'})
        self.assertEqual(parse_report(text.replace('BUG', 'OK')), {('SaveJobs.ts', 7): 'OK'})
        self.assertEqual(parse_report('| `src/Safe.swift:24` | **OK (CANON, stronger variant)** |'),
                         {('Safe.swift', 24): 'CANON'})

    def test_scoring_accepts_correct_report_and_rejects_wrong_findings(self):
        report = '''## BUG Findings
src/ItemStore.swift:22
src/CardView.swift:19
## WATCH Findings
src/PrefetchCache.swift:25
## OK Findings
src/ItemStoreTests.swift:13
src/ItemStoreTests.swift:21
**Reference implementation:** src/SafeStore.swift:24
'''
        controls = {
            'correct': (report, 0),
            'fixed_seed_as_reference': (report + '\n**Reference implementation:** src/SettingsStore.swift:18\n', 0),
            'alternate_reference': (report.replace('**Reference implementation:** src/SafeStore.swift:24',
                                                  'src/SafeStore.swift:24: OK')
                                    + '\n**Reference implementation:** src/SettingsStore.swift:18\n', 0),
            'no_reference_label': (report.replace('**Reference implementation:** src/SafeStore.swift:24',
                                                  'src/SafeStore.swift:24: OK'), 1),
            'missed_bugs': (report.replace('BUG Findings', 'OK Findings'), 1),
            'undecided_bugs': (report.replace('BUG Findings', 'REVIEW Findings'), 1),
            'missing_site': (report.replace('src/CardView.swift:19', ''), 1),
            'false_positive': (report + '\n## BUG Findings\nsrc/Support.swift:36\n', 1),
            'wrong_reference': (report + '\n**Reference implementation:** src/Support.swift:36\n', 1),
            'fixed_seed_as_bug': (report + '\n## BUG Findings\nsrc/SettingsStore.swift:18\n', 1),
        }
        with tempfile.TemporaryDirectory() as folder:
            for name, (text, expected) in controls.items():
                with self.subTest(name=name):
                    path = Path(folder) / (name + '.md')
                    path.write_text(text)
                    result = subprocess.run([sys.executable, str(Path(__file__).with_name('score.py')),
                                             str(path)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
