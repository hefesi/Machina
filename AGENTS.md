# AGENTS.md

Instructions for AI coding agents working in this repository.

## How to Approach Coding Tasks

### Phase 0: Think About Intent

Before doing anything, ask yourself: **what is the human actually trying to accomplish?**

- The user's words describe a task. The task exists in a context. Understand the context — the product, the users, the business goal — and reason about whether the literal request achieves the actual intent.
- If the request is ambiguous, generate 2-3 plausible interpretations and pick the most likely one based on context. If genuinely unclear, note your assumption.
- If the request seems wrong (contradicts existing code, would break something, solves the wrong problem), flag it. Polite pushback is better than silent compliance.
- Think about second-order effects: if I make this change, what else is affected? What will break? What assumption am I making?
- **Separate "what" from "how."** Understand the "what" (desired outcome) fully before jumping to "how" (implementation). Most bad implementations come from starting to code before the goal is clear.

### Phase 1: Understand Before Acting

**Most bad output comes from skipping this phase.**

1. **Read before you write.** Read the files you'll modify, the files adjacent to them, and at least one similar feature that already exists. You need to understand the local conventions, not just the language syntax.
2. **Trace the data flow.** Before changing anything, understand how data arrives (API, loader, props, store) and where it goes (render, action, redirect, external service).
3. **Find prior art.** Search the codebase for something similar to what you're about to build. If it exists, reuse it. If something close exists, follow its patterns. Don't invent new patterns when the codebase already has established ones.
4. **Read the tests.** Tests reveal the intended behavior, the edge cases the author cared about, and the mocking/testing style you should match.
5. **Identify constraints.** Check for: build systems, linters, formatters, type checkers, coverage requirements, CI pipelines. Know what "done" means before starting.

### Phase 2: Implement Incrementally

1. **Smallest change first.** Get something working end-to-end, then iterate. A 10-line change that works beats a 200-line change with a bug somewhere in the middle.
2. **One concern per change.** Don't mix a bug fix with a refactor with a new feature. If you notice something unrelated that needs fixing, note it — don't fix it in the same diff.
3. **Match existing style exactly.** Naming, spacing, file organization, import order, error handling patterns — copy what's already there. Consistency beats your preference.
4. **Write tests alongside code.** Not after. The test immediately validates your understanding. If you can't write a test for it, you probably don't understand it well enough yet.
5. **Run the test suite after every meaningful change.** Don't accumulate a large diff and pray. Finding a failure after 1 change is easy; after 10 changes it's archaeology.
6. **Don't guess at library APIs.** Read how the library is already used in the codebase. The existing usage is more reliable than your training data, which may be outdated.

### Phase 3: Verify

1. **Run the full test suite.** Not just "your" tests — you might have broken something else.
2. **Run the build.** Type checking, linting, coverage gates, and bundling all catch different classes of errors.
3. **Test in the browser if it's UI.** Type-checking and test suites verify code correctness, not feature correctness. If the task has visual output, look at it.
4. **Check edge cases.** Empty states, error states, loading states, long text, missing data. The happy path is never enough.

### What Separates Good From Bad Agent Output

**Good agents:**
- Read 5 files before writing 1
- Produce diffs of 20-50 lines for most tasks
- Follow existing patterns even when they'd do it differently
- Run tests and fix failures before reporting done
- Ask clarifying questions rather than guessing at ambiguous requirements

**Bad agents:**
- Start writing immediately without reading context
- Generate 300+ lines of new code with new abstractions and new patterns
- Invent their own conventions instead of matching the codebase
- Report "done" without running tests or the build
- Add unnecessary error handling, comments, type annotations, and wrapper functions
- Create new files when they should be editing existing ones
- Add features that weren't requested ("while I'm here, I also...")

### Anti-Patterns to Avoid

- **Over-engineering** — no abstractions until there are 3+ concrete uses. No helper functions for one-off logic. No "just in case" error handling for impossible states.
- **Premature commenting** — if the code needs a comment to explain WHAT it does, rename the variables instead. Only comment the WHY when it's genuinely non-obvious (workarounds, hidden constraints, surprising behavior).
- **Speculative generalization** — don't design for hypothetical future requirements. Build for the task at hand.
- **Fabricating APIs or options** — if you're not sure a function, method, flag, or config option exists, verify it by reading the source. Don't invent plausible-sounding APIs from memory. Wrong guesses waste more time than admitting uncertainty.
- **Cosmetic cleanup** — don't reformat, rename, or reorganize code that's unrelated to your task. Every line you touch is a line that could introduce a bug.
- **Ignoring test failures** — a failing test is a signal that your mental model is wrong. Don't "fix the test" without understanding why it failed. The test might be right and your code might be wrong.

### Workflow Checklist

```
1. Read the task — what exactly is being asked?
2. Explore the codebase — find relevant files and similar features
3. Identify patterns — how does this codebase do things?
4. Plan the change — what's the smallest diff that achieves the goal?
5. Implement — match existing style, write tests alongside
6. Test — run the full suite, fix failures
7. Build — verify types, lint, coverage all pass
8. Review your own diff — would you approve this PR?
```
