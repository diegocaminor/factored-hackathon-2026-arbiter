#!/usr/bin/env bash
# Deploy the demo to Railway from a minimal staging directory.
#
# Only the files the image needs are uploaded: requirements, app/, src/propensity/,
# and artifacts/propensity/. Secrets such as .env never leave this machine; set
# OPENAI_API_KEY as a Railway service variable instead.
#
# Usage: scripts/deploy_railway.sh [railway up options, e.g. --service arbiter --ci]
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifacts="$repo_root/artifacts/propensity"

if [[ ! -d "$artifacts" ]]; then
  echo "Missing $artifacts; copy the NBA artifacts there first (see README)." >&2
  exit 1
fi

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

copy() {
  mkdir -p "$stage/$(dirname "$1")"
  rsync -a --exclude '__pycache__' --exclude '*.pyc' --exclude '.env*' "$repo_root/$1" "$stage/$1"
}

cp "$repo_root/Dockerfile.railway" "$stage/Dockerfile"
cp "$repo_root/requirements.txt" "$stage/requirements.txt"
copy app/
copy src/propensity/
copy artifacts/propensity/

echo "Staged $(du -sh "$stage" | cut -f1) for upload from $stage"
# Railway resolves the linked project from the working directory.
cd "$repo_root"
railway up "$stage" --path-as-root "$@"
