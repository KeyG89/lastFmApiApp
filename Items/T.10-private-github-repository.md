# T.10 Private GitHub Repository

Status: In Progress
Commit Prefix: `[T.10]`

## Goal

Publish the existing project to a private GitHub repository without exposing local secrets or generated data.

## Acceptance Criteria

- The GitHub repository is private.
- The local `main` branch is pushed to GitHub.
- The GitHub repository is configured as the local `origin` remote.
- Local secrets, credentials, caches, databases, and generated data remain excluded from Git.

## Implementation Concept

Use the authenticated GitHub CLI to create a private repository from the current Git working tree, configure `origin`, and push `main`. Verify the resulting repository visibility and branch tracking through GitHub and Git.

## Development Notes

- The repository name defaults to the current project directory name: `lastFmApiApp`.
- GitHub CLI authentication must ignore the invalid injected `GITHUB_TOKEN` and use a locally authenticated account.

## Validation

Pending GitHub authentication, repository creation, visibility verification, and push verification.

## User Test Instructions

Open the resulting GitHub repository URL and confirm that its visibility is Private and that the `main` branch contains the project files.

## Feedback And Fix History

No feedback yet.

## Closure Notes

Not closed yet.
