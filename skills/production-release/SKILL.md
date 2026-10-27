---
name: production-release
description: Promote this project's reviewed master snapshot to production, tag it and publish a release with generated assets when requested.
---

# Production release

Follow `AGENTS.md`, `README.md` and `QA.md`. Verify the version and changelog, run `make build` and `make verify`, visually inspect both A5 editions and the imposed A4 file, and complete the physical folded A4 short-edge-duplex proof and QR scans before a print release. Report outstanding checks; do not claim they were performed remotely.

Keep `master` private. Install the local push safeguard and check the remote and clean worktree. Commit reviewed changes on `master`, then check out `production` and apply `git diff --binary production master | git apply --index`; review and commit the staged snapshot as one production commit. Create an annotated version tag on that commit, never the master commit. Check out the tag and run `python3 scripts/release.py vX.Y.Z` with the project dependencies. Inspect the archive and checksum. Push only `production` and its tag when authorized, create the GitHub release, and upload the assets with `scripts/release.py vX.Y.Z --upload`. Confirm the deployment and published language views, XML and Skedz links. Return to `master` when done.
