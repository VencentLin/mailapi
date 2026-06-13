# Development Workflow

This project uses lightweight version control with clear commits. PRs are optional and should be used only when they add useful review or rollback value.

Task coordination between Codex and Claude is defined in `Agent.md`. Use that file as the entry point for active tasks and handoff records.

Local development does not require Docker. Claude should run backend, frontend, and test commands directly on the host; Docker is reserved for final server deployment and should be verified only on a machine where Docker is available.

## Rules For Claude Implementation

Claude can work directly in the local repository, but each task must leave a clean, reviewable commit.

For each task:

1. Start from the latest stable state.
2. Keep the task focused on one bounded change.
3. Run the relevant tests and checks before finishing.
4. Commit the completed task with a clear message.
5. Summarize what changed, how it was tested, and any remaining risk.

Use a separate branch when the task is large, risky, experimental, or may need to be abandoned without touching the stable line.

Open a PR only when:

- The user explicitly asks for a PR.
- The change is large enough to benefit from review.
- The change includes database migrations.
- The change affects authentication, permissions, token encryption, or deployment.
- The change should be easy to revert independently after review.

## Branch Naming

When a branch is useful, use a short descriptive name:

- `feat/backend-scaffold`
- `feat/api-keys`
- `feat/mail-fetch-graph`
- `fix/oauth-refresh-errors`
- `test/mail-account-claim`

## PR Expectations

When a PR is used, it should include:

- What changed.
- Why it changed.
- How it was tested.
- Any migration or deployment notes.
- Screenshots for frontend changes when useful.

## Rollback Strategy

Each completed task should have its own commit or small group of related commits. Regressions can be rolled back by reverting the relevant commit.

For larger or riskier work, prefer a feature branch or PR so the whole change can be reviewed and reverted as one unit.

Database migrations should be reviewed carefully. When possible, migrations should be backward compatible or include a clear rollback path.

## Main Branch

`main` should represent the latest known stable state. Small reviewed tasks may land directly through commits; larger or risky tasks should use a branch first.
