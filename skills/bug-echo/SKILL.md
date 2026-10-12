---
name: bug-echo
description: 'After a bug fix, find and rate other instances of the same defect. Infer and validate a pattern from the fix or use a supplied description, then classify each match against current code. Use for "run bug-echo", "echo this fix", "scan for similar bugs", "find other instances", or an "after-fix scan"; not a general bug hunt without a fix or described pattern.'
license: Apache-2.0
metadata:
  version: 1.8.0
  author: Terry Nyberg, Coffee & Code LLC
  tier: execution
  category: debugging
---

# bug-echo

Find sibling instances of a bug the user just fixed, or of a pattern they describe.
Read [WORKFLOW.md](WORKFLOW.md) and perform its scan, classification, and reporting procedure.
Read linked examples only when relevant. Both Codex and Claude Code use these same files.

For a `--version` request, report the version above and the actual loaded skill path, then stop.

## Runtime and scope

- **Invocation:** Codex uses `$bug-echo`; Claude Code plugins use `/bug-echo:bug-echo`
  (or the command listed by that installation). A manual Claude skill uses `/bug-echo`.
  Plain-language requests work in either app. These are assistant requests, not shell commands.
- **Tools:** Names such as Read, Write, Edit, Bash, Grep, Glob, and Agent in the procedure
  describe operations. Use the tools actually available in the current app; prefer `rg`
  and `rg --files` for shell searches. Do not call nonexistent Claude tools from Codex.
  Use the app's question interface or ordinary conversation for necessary clarification.
- **Resources:** Resolve bundled links from this skill's directory, not the project's
  working directory. Companion skills are optional; never claim an absent skill ran.
- **Authorization:** A clear request to scan authorizes that scan. Ask only about material
  ambiguity. Report-only requests do not authorize fixes or commits. When fixes or commits
  are already requested, carry that authorization forward without asking for each edit.
- **Baseline:** A dirty tree does not block a read-only scan. Preserve unrelated changes.
  Validate inferred patterns against the actual old side: HEAD for a staged diff, the
  index for an unstaged diff, and the selected commit's parent for a commit diff.
- **Current evidence:** Read current code before classifying. A prior fix commit is not
  evidence that a current match is still fixed. Keep candidate and precondition patterns
  separate, and label approximate preconditions as the procedure requires.
- **Reports:** Use the labels BUG, WATCH, OK, OK (CANON), and REVIEW. When a correct
  site is cited as the reference to copy, label it **OK (CANON)** explicitly. Give BUG
  and WATCH findings the procedure's six ratings and their own user impact. Describe
  unobserved consequences conditionally; do not claim data loss, rendered UI behavior,
  or runtime verification that the available code and checks do not establish.
- **Batching:** Above 500 files, use sub-agents only when supported and allowed. Otherwise
  run the same batches locally with the same aggregation contract and report the fallback.
- **Outputs:** Honor the user's destination and workspace permissions. The default report
  location is `.agents/research/`; in a projectless Codex chat use its writable outputs
  directory. A report's existence does not prove its findings were fixed or verified.
