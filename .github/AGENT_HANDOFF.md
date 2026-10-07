# Agent handoff checkpoint

Use a checkpoint when transferring responsibility to another agent or pausing with
unfinished work, including transferring CI or review monitoring. It is not required
for every commit, normal development step, or completed task. There is no CI trigger:
the agent writes the checkpoint at the handoff or pause.

Put it in a dedicated comment on the existing PR, or on the issue if there is no PR.
Update that comment when handing off again or when resuming changes its relevant
state; do not post a new status comment for every polling cycle. Checkpoint comments
are authorized as part of assigned issue/PR work. Local notes can supplement them,
but must not be the only record another agent needs.

## Copyable template

```markdown
## Agent handoff checkpoint

- Recorded at: <UTC timestamp>
- Work: <issue / PR links, agreed scope, remaining acceptance criteria>
- Revision: <branch, full head SHA, base branch / SHA; current-main integration status>
- Local state: <clean, or uncommitted work / how to recover it; repository-relative paths>
- Validation: <focused commands/results and tested SHA; skipped or unrun checks explicitly>
- CI: <run links, tested SHA, completed/pending/failed checks; say when tests were skipped>
- Review: <draft/ready, reviewed SHA, completed/pending review, unresolved finding links>
- Authorization: <explicit maintainer instruction and source, or none; exact PR/action and conditions>
- Next owner/action: <receiving agent or unassigned; immediate next action and blockers>
```

Use `none` or `not run` for an empty field rather than implying a check passed.
For local-only edits, include the patch or recovery reference available to the next
agent. Do not publish credentials, private conversation transcripts, personal absolute
paths, or sensitive exploit details. State authorization scope briefly; link a public
maintainer instruction when available.

## Receiving agent

Before acting, inspect the actual checkout/worktree and verify the live PR head and
base, latest required checks, review completion and threads, and current-main status.
A checkpoint is a snapshot, not proof that GitHub still has the same state. Preserve
uncommitted work and inspect a dependent/stacked PR's base before refreshing or merging.

Verify merge authorization against the maintainer's instruction available in the
session or a maintainer-authored issue/PR comment. An outgoing agent's summary cannot
grant new authority. A green run, assignment, or draft-to-ready transition does not
authorize merging. Existing explicit authorization remains valid within its scope and
conditions; do not ask for it again merely because the agent changed.

If a commit changes, distinguish old verification from checks/review of the new head.
Update the checkpoint with the verified state and next action when resuming or handing
off. If a blocker repeats, report its concrete cause instead of treating silence as
approval. Follow the ordinary contribution, QA, review, and merge rules.
