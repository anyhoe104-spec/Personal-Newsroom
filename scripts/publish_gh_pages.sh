#!/usr/bin/env bash
#
# Publish a built site directory to a branch, as the branch's entire contents.
#
# This is the delivery path the config separation plan moves to: the private
# theme pack builds the site and pushes it here, and GitHub Pages serves this
# branch. Keeping it in a script rather than inline in the workflow means the
# behaviour can be exercised outside Actions.
#
#   scripts/publish_gh_pages.sh [source_dir] [branch]
#
# Defaults: public gh-pages
#
# The branch is created as an orphan on the first run, so it carries only the
# built site and none of the engine's history. When the built output matches
# what the branch already holds, nothing is committed or pushed.

set -euo pipefail

SOURCE_DIR="${1:-public}"
BRANCH="${2:-gh-pages}"
REMOTE="${PUBLISH_REMOTE:-origin}"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "publish_gh_pages: source directory not found: $SOURCE_DIR" >&2
    exit 1
fi

# Refuse to publish a directory that is missing the page itself: an empty or
# half-built directory would replace a working site with nothing.
if [ ! -f "$SOURCE_DIR/index.html" ]; then
    echo "publish_gh_pages: $SOURCE_DIR/index.html is missing; refusing to publish" >&2
    exit 1
fi

WORKTREE="$(mktemp -d)"
cleanup() {
    git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
    rm -rf "$WORKTREE"
}
trap cleanup EXIT

if git ls-remote --exit-code --heads "$REMOTE" "$BRANCH" >/dev/null 2>&1; then
    git fetch --force "$REMOTE" "$BRANCH:refs/remotes/$REMOTE/$BRANCH"
    git worktree add --force -B "$BRANCH" "$WORKTREE" "refs/remotes/$REMOTE/$BRANCH" >/dev/null
else
    echo "publish_gh_pages: $BRANCH does not exist on $REMOTE; creating it"
    git worktree add --force --detach "$WORKTREE" HEAD >/dev/null
    git -C "$WORKTREE" checkout --orphan "$BRANCH" >/dev/null
    git -C "$WORKTREE" rm -rf --cached . >/dev/null 2>&1 || true
fi

# The branch mirrors the source directory, so anything not rebuilt is removed.
find "$WORKTREE" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cp -R "$SOURCE_DIR"/. "$WORKTREE"/

# Without this, Pages runs the output through Jekyll, which skips files and
# directories whose names begin with an underscore.
touch "$WORKTREE/.nojekyll"

git -C "$WORKTREE" add -A
if git -C "$WORKTREE" diff --cached --quiet; then
    echo "publish_gh_pages: $BRANCH already matches $SOURCE_DIR; nothing to publish"
    exit 0
fi

git -C "$WORKTREE" \
    -c user.name="${PUBLISH_NAME:-github-actions[bot]}" \
    -c user.email="${PUBLISH_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}" \
    commit -q -m "Publish site ${GITHUB_SHA:-$(git rev-parse --short HEAD)}"

git -C "$WORKTREE" push "$REMOTE" "$BRANCH"
echo "publish_gh_pages: published $SOURCE_DIR to $BRANCH"
