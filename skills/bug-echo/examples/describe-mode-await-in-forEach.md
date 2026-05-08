# bug-echo Report: `await` inside `Array.forEach` (describe mode)

> [!NOTE]
> This is a **synthesized example** of bug-echo's describe-mode workflow on a TypeScript codebase. The skill's other example file in this directory shows inferred-from-diff mode against a real Stuffolio Swift codebase; this one shows describe mode (the user types out the pattern instead of pointing at a recent fix) on a non-Swift project. File paths and report shape are illustrative.

**Date:** 2026-04-22
**Pattern source:** user-described
**Scan tool:** ast-grep over `src/**/*.{ts,tsx}` (project: a Node.js + TypeScript backend)
**Files scanned:** 412 TypeScript files
**Pattern validated:** N/A (user-described)

---

## How this run started

The user noticed a problem during code review: a teammate's PR included a function that looped over an array with `forEach`, awaited an async call inside, and assumed the loop would wait for each iteration. It doesn't. `Array.prototype.forEach` ignores the return value of its callback, so the `await` inside the callback resolves into a discarded Promise, and the next iteration starts immediately.

The user fixed the PR but suspected the same shape lived elsewhere in the codebase. There was no fix to infer from (the PR hadn't merged yet) and the bug shape was conceptual, not textual. So they invoked bug-echo in describe mode:

```
/bug-echo "any place where we await inside Array.forEach — the await
is silently discarded because forEach ignores callback return values"
```

---

## Pattern

**Anti-pattern:** A function calls `.forEach((...) => { ... await ... ... })` (or its equivalent shapes — see search criterion below) and depends on the loop awaiting each iteration. Because `Array.prototype.forEach` does not return a Promise and discards each callback's return value, the `await`s do not block the loop. All iterations run their async work in parallel; the function after the loop continues without waiting.

**Correct pattern:** When sequential awaiting is intended, use `for...of`. When parallel awaiting is intended, use `await Promise.all(arr.map(...))`. Both forms make the intent explicit and actually wait.

**Search criterion (ast-grep query):** any `MemberExpression` whose property is `forEach`, whose argument is an `ArrowFunctionExpression` or `FunctionExpression` containing an `AwaitExpression` in its body. AST-grep is required here because regex on `forEach` + `await` produces too many false positives (the two can appear in unrelated parts of a file). The structural query catches only the buggy shape.

---

## Summary

- BUG findings: 3
- OK findings: 2
- REVIEW findings: 1

---

## BUG Findings — Issue Rating Table

| # | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | `src/jobs/email-batch.ts:42` — `recipients.forEach(async (r) => { await sendEmail(r); })` inside `processBatch()`. The function returns `Promise.resolve()` immediately while emails fire in parallel. The downstream code that logs "batch complete" runs before any email is actually sent. | 🔴 CRITICAL | ⚪ Low | 🔴 Critical | 🟠 Excellent | ⚪ 1 file | Trivial | Open |
| 2 | `src/migrations/run-pending.ts:18` — migrations are awaited inside `pending.forEach(async ...)`. Two migrations targeting the same table can run concurrently and the second overwrites the first's changes. Has produced silent schema drift in staging twice in the last quarter. | 🔴 CRITICAL | ⚪ Low | 🔴 Critical | 🟠 Excellent | ⚪ 1 file | Trivial | Open |
| 3 | `src/api/audit-log.ts:97` — `events.forEach(async (e) => { await persistEvent(e); })`. Events are written to the audit log in parallel, so the audit log's chronological order does not match the order events arrived. Any tool downstream that reads the log assuming sequential ordering is wrong. | 🟡 HIGH | ⚪ Low | 🟡 High | 🟠 Excellent | ⚪ 1 file | Trivial | Open |

---

## OK Findings (intentional, no action needed)

- `src/utils/parallel-fetch.ts:23` — `urls.forEach(async (u) => { void prefetch(u); })`. The `void` operator and the explicit "fire and forget" comment immediately above show the author intentionally launched parallel work and discarded the return value. Intentional design.
- `tests/__fixtures__/setup.ts:11` — `mocks.forEach(async (m) => { await m.reset(); })`. Inside a test fixture; the test runner's `beforeEach` awaits the wrapper function but the mocks themselves don't depend on each other. Test-only code; not a production correctness issue.

---

## REVIEW Findings (need human judgment)

- `src/realtime/broadcast.ts:55` — `subscribers.forEach(async (s) => { await s.notify(payload); })`. Whether parallel notification is correct depends on whether subscribers' `notify()` calls are idempotent and whether ordering matters. The codebase has no documentation on this; ask the author.

---

## Detailed Findings

### 1. `src/jobs/email-batch.ts:42` — emails fire in parallel; "batch complete" logged before any send

```typescript
async function processBatch(recipients: User[]) {
  recipients.forEach(async (r) => {
    await sendEmail(r);
    await markSent(r.id);
  });
  logger.info(`Batch processed: ${recipients.length} recipients`);
  return { sent: recipients.length };
}
```

**Why this is a bug:** The function's contract — implied by its `await`s and its log line — is "process recipients one at a time, then return when done." What actually happens: each `sendEmail` call fires immediately, no iteration waits for the previous, and `logger.info()` runs *before any email has been sent*. The returned object claims `sent: recipients.length` but at the time of return, zero emails have been confirmed sent. Network failures are also lost — `sendEmail` may reject, and the rejection is swallowed because `forEach` doesn't see callback return values.

**Suggested fix (sequential, matches author's apparent intent):**
```typescript
for (const r of recipients) {
  await sendEmail(r);
  await markSent(r.id);
}
```

**Or (parallel, if that's what was actually wanted):**
```typescript
await Promise.all(recipients.map(async (r) => {
  await sendEmail(r);
  await markSent(r.id);
}));
```

The choice depends on whether your email provider rate-limits and whether marking sent depends on the previous mark having completed. The `for...of` form is the safe default — switch to `Promise.all` only if profiling shows the sequential version is too slow and you've confirmed parallel is safe.

---

### 2. `src/migrations/run-pending.ts:18` — migrations run concurrently; second overwrites first

```typescript
async function runPendingMigrations() {
  const pending = await loadPending();
  pending.forEach(async (m) => {
    await m.run();
    await markApplied(m.id);
  });
  logger.info('All pending migrations applied');
}
```

**Why this is a bug:** Migrations *must* run sequentially. Two migrations that both add columns to the `users` table can race each other and one's commit will conflict with the other. The codebase already had this incident twice — a migration appeared to apply but a column was missing because a later concurrent migration's transaction overwrote the table state. The bug pattern is the same shape as #1.

**Suggested fix:**
```typescript
for (const m of pending) {
  await m.run();
  await markApplied(m.id);
}
```

`Promise.all` would be wrong here — migrations explicitly require sequential execution.

---

### 3. `src/api/audit-log.ts:97` — audit log entries arrive out of order

```typescript
async function logEventBatch(events: AuditEvent[]) {
  events.forEach(async (e) => {
    await persistEvent(e);
  });
  return { count: events.length };
}
```

**Why this is a bug:** Audit logs are read chronologically by downstream tools (compliance reports, security investigations). Without sequential awaiting, events with a recorded timestamp of `T+0ms` might be persisted *after* events with `T+5ms`, depending on database response times. The bug compounds with #1 and #2: when this function is called from the email batch processor, the audit entries for "email batch processed" can land before the actual emails are sent.

**Suggested fix:**
```typescript
for (const e of events) {
  await persistEvent(e);
}
```

If audit log writes are slow enough that sequential becomes a bottleneck, the right fix is queueing events to a separate writer process — *not* parallelizing the writes.

---

## Pattern context

All three BUG findings share the exact same shape: `arr.forEach(async (x) => { await ... })`. The fix is mechanically the same in each case (`for...of`). They were not caught by the type checker because TypeScript's `forEach` signature accepts an async callback (its return type is `Promise<void>`, which `forEach` simply discards). They were not caught by ESLint because the project doesn't have `no-misused-promises` enabled. They were not caught by tests because two of the three only fail intermittently under load.

Recommendations:

1. **Fix the three findings.** Trivial work, immediately reduces real risk.
2. **Enable `@typescript-eslint/no-misused-promises`** with `checksVoidReturn: true` in `.eslintrc`. Catches every future instance at lint time.
3. **Run bug-echo against the diff** of the email-batch fix (BUG #1) once it merges, to see if the inferred-from-diff mode finds anything the describe-mode scan missed. The two modes have slightly different signature shapes; running both is reasonable on high-stakes patterns.

---

## After You Fix These Findings

The companion skill [bug-prospector](https://github.com/Terryc21/bug-prospector) runs forward-looking lenses to find bugs that haven't fired yet, including a State Machine lens that often catches concurrency-shaped issues bug-echo can't. After fixing the three findings above, consider running:

```
/bug-prospector
```

scoped to `src/jobs/`, `src/migrations/`, and `src/realtime/` with the State Machine + Error Path lenses. These directories are concurrency-heavy and bug-prospector's questions are different from bug-echo's pattern matching.

---

*Real bug-echo describe-mode runs produce reports in this format. The pattern in this example was synthesized for documentation; the report shape, classification rules, and rating table format match what real runs produce.*
