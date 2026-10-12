# Changelog fragments

Add one short, user-facing note per coherent change. Name it
`<number>.<category>.md` using the issue number, or the PR number when there is no
issue, such as `123.fixed.md`. Use additional fragments when a change needs more
than one category; Towncrier also supports numbered suffixes such as `123.fixed.1.md`.

Categories, in release order: `breaking`, `added`, `changed`, `deprecated`,
`removed`, `fixed`, and `security`. Name affected options or APIs and explain
migration for breaking changes. Explain observable behavior; keep implementation
details, validation results, and benchmark methodology in PRs or documentation.

Internal changes (refactors, CI, development docs) and fixes to bugs introduced since
the last release don't need a fragment: apply the `no-changelog` label to the PR instead.

```bash
./.venv/bin/towncrier create --content "Corrected an existing behavior." 123.fixed.md
./.venv/bin/python tools/changelog.py --preview
```

The second command validates all fragments and prints the Unreleased section. The
documentation site's changelog page renders the same preview; `CHANGELOG.md` itself
only gains notes when a release is assembled (see [RELEASING.md](../RELEASING.md)).

The `+0160-*` orphan fragments migrate work that predates the issue-based process.
They intentionally have no invented issue references.
