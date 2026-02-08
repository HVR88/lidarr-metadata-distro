#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../upstream/lidarr-metadata"
git remote -v
git status
