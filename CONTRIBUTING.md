# Contributing to the project

## Workflow

- Do not push directly to `main`.
- Every change must be made in its own branch.
- All changes must be merged through a Pull Request.

## Branch naming

We will use the Jira issue key at the beginning of the branch name.

Examples:
- `FSYNC-7-configurar-ci-github`
- `FSYNC-6-elegir-tecnologia-ocr`

## Pull Requests

- The PR title must include the Jira issue key.
- Before merging, the CI must pass.
- `main` has branch protection and required checks.

## Code quality

For Python, the following checks will be validated:
- linting with Ruff
- formatting with Black
- tests with Pytest, when available
