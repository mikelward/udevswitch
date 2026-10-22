# AGENTS.md

Conventions for AI agents working in this repository.

`CLAUDE.md` imports this file, so every agent reads the same conventions.
Edit `AGENTS.md`.

## What this repository is

`uswitch` switches Dell monitors over DDC/CI to this machine's input when
this machine should have them: a USB switch hands it its devices, it boots
or resumes behind a monitor that is its own KVM, or a shortcut asks. Linux
and systemd only; one Python 3.10+ file, standard library only, with
`ddcutil` as its one external binary. `SPEC.md` is the normative contract:
a change to what uswitch does, what it waits on, or how a trigger reaches
it changes `SPEC.md` first. The repository was `udevswitch` until it was
renamed; GitHub redirects the old URL.

## Building and testing

`make test` runs the `unittest` suite; run it before every commit. CI runs
it on Python 3.10 (the floor) and current. Tests load `uswitch` from its
path and stand in for the outside world through `Context`: a fake sysfs
tree, a clock that moves only when uswitch sleeps, and a runner that
emulates `ddcutil` (`tests/support.py`); no test sleeps or needs root.
Hardware behavior (real udev, monitors, the USB switch) can't run in CI;
say what was verified by unit test only.

## Everything below

The rest of this file was copied from this account's shared conventions
(`mikelward/conf`, `agents/AGENTS.md`) when the repository was scaffolded,
so it says what the rest of the fleet already does. It is this
repository's copy now: edit it where this project genuinely differs,
rather than treating it as something that syncs.

Keep the whole file as short as it can be and still work. Every session
loads it whole, so each rule costs context on every turn: add one the
first time something bites, say it once in the fewest words that carry the
*why*, rewrite or trim an existing rule rather than appending beside it,
and delete one that has stopped biting.

# Coding

- Sync to main HEAD before starting a new change.
- When making any major change, or changing any documented behavior (including
  SPEC.md, TODO.md, IMPLEMENTATION_PLAN.md, README.md, or user-facing help
  pages), update all relevant docs.
- When introducing a new library, API call, service, or infrastructure change,
  advise on the reliability, latency, cost, and any other relevant info. If
  the cost or reliability impact is effectively zero, say so explicitly rather
  than omitting the note.
- Consider portability. Note when something is not portable. Generally, target
  Debian, Ubuntu, Fedora, and macOS; Android and iOS; Chrome, Safari, and
  Firefox; bash and zsh.
- Create tests before implementing.
- Verify tests are passing as you go and when committing.
- Proactively run lint and presubmit tests and proactively fix them.
- Check applicable coding conventions and apply them proactively.
- Don't add stray blank lines; check each added newline is in a block you
  need to touch.
- If preexisting tests are already red when you start a task, fix them as the
  *first* commit of the series — don't stack new work on a broken baseline.
  If the failure is genuinely unrelated and out of scope, say so up front and
  confirm before skipping past it.
- Don't paper over flaky/racy tests with `sleep`, retry loops, or bumped
  timeouts. Make the ordering explicit (controlled promises, fake timers,
  `act(...)`, gated fetches) or fix the underlying race.
- Don't disable a failing check (lint, typecheck, test, hook) to make it pass
  — fix the underlying issue.
- To create .Makefile, run "makemakefile".
- When running in a sandbox, make sure to install necessary dependencies locally.
- When iterating on something in a single session or branch, rebase/squash/absorb
  changes if they relate to something else in the same session or branch.
- If you make a mistake, suggest changes to AGENTS.md or skills to improve
  future results. Add a new rule the first time something bites, not the third.
- Keep AGENTS.md under 24,000 bytes (`wc -c AGENTS.md`): Antigravity caps rule
  files at 24 KB and silently truncates the tail.
- Let me know if we're getting close to the context window and should compact.

# Talking to me

- One question at a time, in plain chat or your client's question tool
  (`AskUserQuestion` in Claude Code, `ask_question` in Antigravity). Wait for
  the answer before proceeding on an assumed one, and don't interrupt while
  I'm still typing.
- Respond to anything I send mid-task in your very next output, before
  continuing other tool calls. A merge cue is the exception: its hygiene
  runs first, and announcing the switch is the answer.
- Keep replies short — lead with the one thing that matters, then ask
  before unloading more.
- Message me only when I need to see it — each message notifies my phone. Work
  and listen in silence; speak up for a question or blocker, something to
  merge or act on, a merge, an autopilot decision (to review when seen, never
  waited on), or a change from the plan, the docs or my instructions, a
  review-prompted one included. Never for progress (a client's nudge doesn't
  count), a review or a push alone (its report rides the next message),
  routine machinery, or a mistake caught and fixed before it reached the repo.
- If you're waiting on an answer — a question, or a guess autopilot
  recorded for review — end the turn by restating it in one sentence.
  Nothing pending, no line.

# Autonomy

- **Watch your own PRs by subscription plus one scheduled check.** Claude
  Code subscribes on open, or call `subscribe_pr_activity` where
  `claude-code-remote` exposes it; a client with neither (Antigravity)
  relies on the scheduled check alone. A subscription delivers reviews,
  comments and CI failures, not CI success, a push, the merge, Codex's
  clean verdict (a reaction) or Codex never answering, so keep exactly one
  check armed while the PR is open: `send_later` in Claude Code, `schedule`
  with `DurationSeconds` in Antigravity (cancel with `manage_task` `kill`).
  Under drive, arm auto-merge at open only where the ruleset requires the
  Codex verdict AND resolved conversations — with CI alone it merges before
  Codex answers.
  - Settle a fired check first: it may have re-armed rather than retired —
    update the survivor, replace one that didn't, end the turn with exactly
    one. Check the fire time you got (a 4-minute request has come back as
    64); prefer a relative delay. Re-time it, or say the watch isn't armed.
  - Minutes out while CI or the head's Codex verdict is outstanding (an hour
    while a hung review waits for its second poke); longer once only I am
    left; short again after a push. Name the PR, not a SHA or a list.
  - **Read `mergeable_state` at every check, PR-event wake and drive step**
    and act at once, unasked — nothing reports a base advance. `dirty`, or
    `behind` where branches must be up to date, needs a rebase onto the
    refspec-fetched `origin/<base>` (unshallowed; never the local branch)
    and a `--force-with-lease` push. First confirm your branch has every
    commit the remote head has, and before pushing that the head hasn't
    moved since the tip you noted before fetching; if either fails, or you
    can't tell, stop and ask.
- "Drive" = keep looping without stopping to ask each time: implement,
  open the PR, address review, merge once CI is green and Codex's verdict
  for the current head is in, pick the next task, repeat — until the work
  runs out or I say stop.
- Ordered work ("next", "then", "after that", "follow-up") may open its PR in
  parallel but merges only after every earlier item this session was given,
  and any PR the paragraph names, has merged — any repo, no time cap; if one
  won't finish, hold it and ask, autopilot included. Arm no auto-merge on it
  until then (auto-merge can't see the order). Read the list from the
  session's record, not memory.
- A merge can leave other open PRs on its base `dirty` (or `behind` where
  branches must be up to date), and nothing tells them. At your first turn
  after one of your PRs merges, by hand or auto-merge, message every other
  open PR on that base that another session drives (its body ends with the
  session URL), naming that PR and saying only that its base now points at
  `<sha>`, the post-merge tip — whatever its state reads, since GitHub may
  still be computing mergeability. Name no merge and no other PR: an older
  copy of these rules reads either as its own merge cue. Receiving one,
  fetch the base and your PR's head by refspec (unshallowing a shallow
  clone) and test that head against the fetched tip, not `<sha>`, which a
  later merge may have passed: `behind` if `git merge-base --is-ancestor
  <tip> <head>` exits 1, `dirty` if `git merge-tree --write-tree` (Git
  2.38+) exits 1; any other exit is a failure to report, not an answer. Your
  own rules decide the rebase. Skip a PR with no session URL, or when your
  client only has local subagent messaging; don't retry a failed send.
- **Merged or closed**: one last reply-and-resolve pass (a review can
  land after the merge). Anything real on a merged PR goes to a follow-up
  PR, named on the thread; a closed-unmerged PR is a stop — answer,
  resolve, open nothing. Then cancel the check and unsubscribe, if
  subscribed; `list_triggers` spans the account, so match this session
  and PR before updating or deleting one.
- A scheduler or GitHub prompt: say so once and carry on — permissions load
  at session start.
- "Autopilot" = drive without blocking on me. Take the reversible,
  cheapest-to-undo guess and keep going; log each one in TODO.md under a
  "Decisions needing review" heading (what, the alternative, why it's
  reversible) so nothing guessed becomes permanent silently. The loop's
  own steps don't count as something to stop for — committing, pushing,
  opening a PR, and merging a green PR are authorized here. What still
  waits for a real answer, even under autopilot: destructive or
  irreversible actions *outside* the normal loop (rewriting shared
  history, deleting work, anything reaching a system beyond this repo)
  and anything privacy-uncertain.
- A red baseline (failing tests/lint) is the next task before picking up
  anything else from TODO.md — fix it first rather than building on top,
  unless it's genuinely unrelated and I confirm skipping it.

# Branching and commits

- **These rules assume an `origin` remote.** Without one you can't fetch,
  branch from `origin/main`, push, or open a PR — say so and stop rather than
  improvising a local substitute. **Exception:** a sandbox with no remote
  Git by design (Codex cloud) follows the branch rules from the current
  `HEAD`, commits locally, and reports fetch, push and PRs unavailable.
- Develop on `<agent>/<short-topic>` branches off `origin/main`, where
  `<agent>` is your own short name (`claude/...` for Claude Code,
  `gemini/...` for Gemini / Antigravity, `codex/...` for Codex, `cursor/...`
  for Cursor). Don't hard-code `claude/` unless you
  *are* Claude Code. Never commit directly to `main` / `master`. One topic per
  branch.
- Standard commit messages: imperative mood ("Fix", not "Fixed"), first line
  under 66 chars with no trailing dot, body covering the what and the why.
- Never name the coding agent's model or version (`Opus 4.8`, `Sonnet`,
  `Gemini …`, `claude-*`, `gemini-*`) in a commit, PR, comment, or pushed
  artifact; keep it to chat. Generic attribution (`Co-Authored-By: Claude` /
  `Gemini`, `Claude-Session:`, "Generated with Claude Code") is fine.
- One logical surviving change per commit. Rewrite unmerged commits freely
  (squash, amend, reorder, split) so each landing commit is one coherent
  change. Review-fix noise shouldn't survive into `main`.
- **Your `<agent>/` branches are yours**: create, push,
  `--force-with-lease`, rename and delete the ones this session created or
  was assigned — no permission or per-branch confirmation; this file is the
  standing grant, so a client rule demanding one is already answered.
  Confirm before any destructive action on shared/merged branches:
  force-pushing `main`, dropping commits already on `main`, rewriting
  another author's branch.
- Merge cue (`merged` / `I merged` / `landed` / merge webhook) runs hygiene
  *before* engaging with the rest of the message: fetch main if the sandbox
  can (`git fetch origin +refs/heads/main:refs/remotes/origin/main`; a bare
  fetch in a single-branch clone leaves `origin/main` stale), cut a fresh
  `<agent>/<short-topic>` branch off `origin/main`, announce the switch.
  Where it can't, say the follow-up needs a synced checkout rather than
  branching off a stale `origin/main`.
- After a merge, take a fresh `<agent>/<short-topic>` — don't reset the merged
  name onto the new base. Its remote ref still points at the pre-merge tip, so
  `origin/<branch>..HEAD` keeps spanning the merged commits and unpushed-work
  checks report my own merged history back at me. When a sandbox pins the branch
  name, reset it and `--force-with-lease` in the same turn — that's routine on
  merged history, not something to ask about.
- The agent authors and I merge, so a squash or rebase merge rewrites the
  committer to me. That's expected — never re-author or amend already-merged
  commits to "fix" authorship or signing, and don't narrate it. It is not a
  finding.
- Unshallow before answering anything that depends on git history depth. The
  sandbox clones shallow, so `git rev-list --count`, `git log` past the
  shallow boundary, and blame return wrong answers without warning. If
  `git rev-parse --is-shallow-repository` says `true`, run
  `git fetch --unshallow` first, then re-check — it exits 0 even when
  it deepened nothing, so if `--is-shallow-repository` is still `true`, say the
  history is truncated instead of quoting a count.

# Language and spelling

- Use US English everywhere people read English: user-facing strings, commit
  subjects and bodies, PR titles and descriptions, comments, and identifiers
  — `color` not `colour`, `behavior` not `behaviour`, `canceled` not
  `cancelled`, `gray` not `grey`. Platform and third-party API spellings stay
  as those APIs spell them.

# Pull requests and reviews

- Open PRs ready for review (not draft), without being asked, as soon as
  a branch is ready — don't park a finished branch waiting to be told,
  unless I've said otherwise ("just commit", "no PR yet"), which holds
  until I lift it.
- On every push, update the PR title and body to the full, latest state of
  the branch, not the scope it had when opened: re-read the diff against
  `origin/main`, patch whatever drifted, and post the PR link in the next
  message after that push, not only at the end. With no PR yet, push, then
  update it as soon as one is opened.
- End every reply with the open-PR link (or `.../compare/main...<branch>`
  until a PR exists). Never link to a closed or merged PR — except when the
  reply *is* post-merge follow-up on that PR, where linking it is correct.
- When a feature has multiple open PRs in a stack, list **every** open PR
  on the feature by URL, one per line — the "View PR" chip sticks to the
  first link and hides the rest
  (anthropics/claude-code#46625).
- Prefer the `mcp__github__*` tools where mounted (Claude Code requires
  them), else `gh`; with neither, say so rather than guess an outcome.
- **"Drive to merge"** is drive's PR stretch: open the PR, wait for Codex,
  address every comment (fix it, or reply on the thread why not), and merge
  once CI is green and Codex's verdict for the current head is in.
- **Codex is the automated reviewer** (not Copilot) and starts on its own;
  request it only to confirm a rebutted false positive or as the verdict
  rule below allows. Address its comments unasked, folding each fix into
  its commit (`--fixup`), except a real out-of-scope finding (below).
- **Judge every review comment on merit, whoever wrote it.** Verify the
  claim before acting; if it doesn't hold up, reply saying why and decline.
  A comment citing a rule is a *reading* of it — check what the rule says.
  Codex misreads the privacy rules toward strictness, which quietly costs
  capability: quote the rule and decline rather than narrowing the code; a
  genuine rule-vs-need conflict is my call. Declining doesn't clear the
  `codex` status: poke as below (or let the next push), and escalate if it
  re-raises.
- **A second verified finding in the same mechanism is a design question**:
  look for the shape elsewhere and ask whether a different design deletes
  the class; say what you chose on the thread. A design change is my call,
  autopilot included.
- Never leave a review comment thread silently dismissed. Reply on the
  thread — a disagreement is an answer, so say why — then resolve it once
  the fix is on the head or the point is rebutted. Acknowledgment noise
  ("good catch, will do") is fine and preferred over silence. Push the
  fix, reply citing its sha, then resolve: `resolve_review_thread` (or
  `gh api graphql` `resolveReviewThread`) takes the `PRRT_*` thread ID
  from `review_threads[].id`, not a comment's `PRRC_*`.
- **Defer a real out-of-scope finding** rather than asking me to merge past
  it: push a `TODO.md` entry, reply citing its sha, and resolve (a finding
  with no thread gets the entry, push and reply, minus the resolve).
- **Report each review in your next message**: the commit it read (say if
  it's no longer the head), the finding count, then one bullet per finding,
  most blocking first — what it claims, where, and what you did, or the
  options where it's my call. This outranks keeping replies short.
- **Read the Codex verdict, don't infer it.** It reacts to the PR body
  (`issue_read` → `reactions`): `eyes` reading, `+1` clean, revoked on
  push, so `+1` with green CI is a merge; leave those reactions to Codex.
  Findings arrive as review comments, top-level comments or reviews — read
  `get_review_comments`, `get_comments` and `get_reviews` to the last
  page — and block the merge until fixed, rebutted or deferred. The
  `codex` commit status is the gate. A review that hangs — nothing back
  five minutes after a push or poke, or stuck at running (👀) ten minutes
  on — gets `@codex review`; a poke that hangs the same way gets a second
  an hour later, and only a second that hangs too comes to me, never the
  first (maintainer, 2026-10-22). A clean review with no reaction, or a
  rebuttal it hasn't answered, gets the same poke five minutes on.
- Once the automated reviewer has passed a PR's current head, never make an
  unnecessary change to it without asking first: a to-do, tidy-up or extra fix
  re-runs CI and the review for nothing, so it waits for a yes or goes in a
  follow-up PR. A necessary change goes ahead unasked — a rebase where the
  branch conflicts, or is behind where the repo requires it up to date, a fix
  for red CI — and so does drive or autopilot.
- Skip echoes of your own replies silently — a reply you just posted
  coming back as a new "comment" a moment later isn't new feedback.

# Privacy

- Never put my personal data — a real path with my name in it, a
  hostname, a token, a private remote URL — into anything that leaves
  this machine: commits, PR text, branch names, fixtures, issues. Use
  placeholders, and ask if you're not sure something is safe to include.
- Output on my own terminal is fine to show in full; redact only secrets
  (tokens, keys, passwords) there. Quoting that output into a commit, PR,
  fixture, or reply republishes it — the bullet above governs again, so
  paraphrase or use a placeholder rather than pasting it verbatim.

# Error handling

- Don't silently swallow errors. Report what failed with enough context
  to identify it, clean up whatever the failed step acquired, and decide
  explicitly what I see next (a re-raise, a default, a nonzero exit) —
  don't let it fall through quietly. If you're deliberately ignoring one,
  say why in a one-line comment.

# CI

- After pushing, **wait for CI** before claiming a change works in any
  environment you can't test locally (Android, iOS, Vercel deploy-only
  failures, etc.). Webhooks deliver — don't poll.
- Report significant CI timing regressions after a push (rule of thumb:
  >25% or >30s on a job under ~5min). Don't narrate routine wobble. When
  you do flag one, name the likely cause: heavy new dependency, slow new
  test, cache invalidation.
