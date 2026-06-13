# Development Workflow

This project uses a branch-and-PR workflow for every implementation task.

## Rules For Claude Implementation

Claude must not implement directly on `main`.

For each task:

1. Create a new branch from the latest `main`.
2. Keep the task focused on one bounded change.
3. Run the relevant tests and checks before finishing.
4. Commit the completed task.
5. Open a PR for review.
6. Do not merge the PR until the change has been reviewed and accepted.

## Branch Naming

Use short descriptive names:

- `feat/backend-scaffold`
- `feat/api-keys`
- `feat/mail-fetch-graph`
- `fix/oauth-refresh-errors`
- `test/mail-account-claim`

## PR Expectations

Each PR should include:

- What changed.
- Why it changed.
- How it was tested.
- Any migration or deployment notes.
- Screenshots for frontend changes when useful.

## Rollback Strategy

Because each task lands through a separate PR, regressions can be rolled back by reverting the merge commit for that PR.

Database migrations should be reviewed carefully. When possible, migrations should be backward compatible or include a clear rollback path.

## Main Branch

`main` should always represent the last reviewed stable state.
