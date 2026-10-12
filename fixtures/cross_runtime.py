#!/usr/bin/env python3
"""Run real Codex/Claude scans on isolated fixtures. Uses existing CLI sign-ins.

Usage: python3 fixtures/cross_runtime.py --output /absolute/path/to/results
Optional: --runtimes codex claude --cases committed unstaged described
The output directory must be new. Reports, transcripts, prompts and scores stay
outside the source repository. No model override or application source edit is used.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def git(cwd, *args):
    return subprocess.check_output(['git', *args], cwd=cwd)


def snapshot(cwd):
    files = {str(p.relative_to(cwd)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in cwd.rglob('*') if p.is_file()
             and '.git' not in p.relative_to(cwd).parts
             and '.agents' not in p.relative_to(cwd).parts}
    return {'head': git(cwd, 'rev-parse', 'HEAD').decode().strip(),
            'status': git(cwd, 'status', '--porcelain').decode(),
            'index': hashlib.sha256((cwd / '.git/index').read_bytes()).hexdigest(),
            'files': files}


def prepare(dest, case):
    if case == 'described':
        dest.mkdir()
        shutil.copytree(ROOT / 'fixtures/typescript-await/src', dest / 'src')
        git(dest, 'init', '-q')
        git(dest, 'config', 'user.email', 'fixture@bug-echo.local')
        git(dest, 'config', 'user.name', 'bug-echo fixture')
        git(dest, 'add', 'src')
        git(dest, 'commit', '-qm', 'Add batch-save example')
    else:
        subprocess.run(['bash', str(ROOT / 'fixtures/setup.sh'), 'swift-try-fetch', str(dest)],
                       check=True, stdout=subprocess.DEVNULL)
        if case == 'unstaged':
            seed = dest / 'src/SettingsStore.swift'
            fixed = seed.read_bytes()
            seed.write_bytes(git(dest, 'show', 'HEAD^:src/SettingsStore.swift'))
            (dest / 'notes.txt').write_text('Unrelated staged user notes.\n')
            git(dest, 'add', 'src/SettingsStore.swift', 'notes.txt')
            seed.write_bytes(fixed)
            (dest / 'notes.txt').write_text('Unrelated staged user notes.\nUnstaged addition.\n')
    # Ignore installation plumbing so the committed case stays clean.
    with (dest / '.git/info/exclude').open('a') as f:
        f.write('\n.agents/\n')
    skills = dest / '.agents/skills'
    skills.mkdir(parents=True)
    (skills / 'bug-echo').symlink_to(ROOT / 'skills/bug-echo', target_is_directory=True)


def run_case(runtime, case, out):
    folder = out / (runtime + '-' + case)
    folder.mkdir()
    repo = folder / 'project'
    prepare(repo, case)
    before = snapshot(repo)
    instruction = {
        'committed': 'Infer from the latest commit and scan the Swift source in src/.',
        'unstaged': 'Infer specifically from the UNSTAGED fix to src/SettingsStore.swift and scan src/. '
                    'The staged changes and notes are intentional; preserve them and do not commit.',
        'described': 'Scan src/ for awaiting forEach with an async callback when the caller '
                     'expects all work to finish before returning or showing success.'
    }[case]
    invocation = '$bug-echo' if runtime == 'codex' else '/bug-echo:bug-echo'
    prompt = (f'{invocation} {instruction}\n'
              'Report only. Do not edit source, stage, commit, or write report files. '
              'Put the complete report in your final response, including classifications for '
              'all candidate sites (including OK and WATCH), ratings and user impact for findings. '
              'Identify the loaded skill version and path. Use the supplied local skill/plugin, '
              'not an older personal installation. Read only this fixture project and the '
              'supplied skills/bug-echo directory and its references; do not read answer keys, '
              'other fixture directories, prior reports, or the test runner. '
              'This request authorizes the scan now; ask only if materially ambiguous. '
              'Shell permissions cover simple read commands such as git, rg, ls and cat; '
              'use the Read tool for file contents rather than shell loops.\n')
    if runtime == 'codex':
        prompt += 'The project skill is .agents/skills/bug-echo/SKILL.md.\n'
        command = ['codex', 'exec', '--ignore-user-config', '--ephemeral', '--sandbox',
                   'read-only', '--json', '-C', str(repo), '--output-last-message',
                   str(folder / 'report.md'), '-']
    else:
        command = ['claude', '--print', '--no-session-persistence', '--output-format',
                   'stream-json', '--verbose', '--setting-sources', '',
                   '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                   '--plugin-dir', str(ROOT), '--permission-mode', 'dontAsk',
                   '--tools', 'Read,Grep,Glob,Bash,Skill', '--allowedTools',
                   'Read', 'Grep', 'Glob', 'Skill', 'Bash(git:*)', 'Bash(rg:*)',
                   'Bash(grep:*)', 'Bash(find:*)', 'Bash(wc:*)', 'Bash(which:*)',
                   'Bash(ls:*)', 'Bash(cat:*)', 'Bash(sed:*)', 'Bash(head:*)',
                   'Bash(nl:*)', '--', prompt]
    (folder / 'prompt.txt').write_text(prompt)
    started = time.time()
    with (folder / 'transcript.jsonl').open('w') as stdout, (folder / 'stderr.txt').open('w') as stderr:
        try:
            result = subprocess.run(command, cwd=repo, input=prompt if runtime == 'codex' else None,
                                    text=True, stdout=stdout, stderr=stderr, timeout=600)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    if runtime == 'claude':
        for line in (folder / 'transcript.jsonl').read_text().splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get('type') == 'result':
                (folder / 'report.md').write_text(event.get('result', ''))
    after = snapshot(repo)
    unchanged = before == after
    (folder / 'before.json').write_text(json.dumps(before, indent=2))
    (folder / 'after.json').write_text(json.dumps(after, indent=2))
    key = 'typescript-await' if case == 'described' else 'swift-try-fetch'
    report = folder / 'report.md'
    score = subprocess.run(['python3', str(ROOT / 'fixtures/score.py'), str(report), key],
                           capture_output=True, text=True)
    (folder / 'score.txt').write_text(score.stdout + score.stderr)
    row = {'runtime': runtime, 'case': case, 'exit_code': code, 'score_exit_code': score.returncode,
           'inputs_unchanged': unchanged, 'seconds': round(time.time() - started),
           'report': str(report)}
    (folder / 'result.json').write_text(json.dumps(row, indent=2) + '\n')
    print(json.dumps(row), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtimes', nargs='+', choices=['codex', 'claude'], default=['codex', 'claude'])
    parser.add_argument('--cases', nargs='+', choices=['committed', 'unstaged', 'described'],
                        default=['committed', 'unstaged', 'described'])
    args = parser.parse_args()
    out = args.output.resolve()
    if out.is_relative_to(ROOT):
        parser.error('put runtime results outside the source repository')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'versions.txt').write_text('\n'.join(
        subprocess.check_output([runtime, '--version'], text=True).strip()
        for runtime in args.runtimes) + '\n')
    (out / 'skill-sha256.json').write_text(json.dumps({
        name: hashlib.sha256((ROOT / 'skills/bug-echo' / name).read_bytes()).hexdigest()
        for name in ['SKILL.md', 'WORKFLOW.md']}, indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_case, runtime, case, out)
                   for runtime in args.runtimes for case in args.cases]
        rows = [f.result() for f in concurrent.futures.as_completed(futures)]
    (out / 'results.json').write_text(json.dumps(rows, indent=2) + '\n')
    return int(any(r['exit_code'] or r['score_exit_code'] or not r['inputs_unchanged'] for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
