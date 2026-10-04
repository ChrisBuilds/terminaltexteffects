# Changelog fragments

Add one short, user-facing note per coherent change. Name it
`<issue-number>.<category>.md`, such as `123.fixed.md`. Use additional fragments
when a change needs more than one category; Towncrier also supports numbered
suffixes such as `123.fixed.1.md`.

Categories, in release order: `breaking`, `added`, `changed`, `deprecated`,
`removed`, `fixed`, and `security`. Name affected options or APIs and explain
migration for breaking changes. Explain observable behavior; keep implementation
details, validation results, and benchmark methodology in PRs or documentation.

For internal refactors, CI changes, or fixes to bugs introduced in the same
unreleased version, add `<issue-number>.skip.md` containing the reason no release
note is needed. Skip reasons are checked but omitted from release output.

```bash
./.venv/bin/towncrier create --content "Corrected an existing behavior." 123.fixed.md
./.venv/bin/python tools/generate_changelog.py
./.venv/bin/python tools/generate_changelog.py --check
```

Commit the fragment and refreshed `CHANGELOG.md` preview together. Never edit the
generated Unreleased preview directly. Published entries are assembled in a
release-preparation PR; see [the release procedure](../CONTRIBUTING.md#release-notes).

The `+0160-*` orphan fragments migrate work that predates the issue-based process.
They intentionally have no invented issue references. Use real issue numbers for new work.
