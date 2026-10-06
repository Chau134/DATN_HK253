#!/usr/bin/env bash
set -euo pipefail

archive=/tmp/datn-release-d2e04d7.tar.gz
release_dir="$(mktemp -d /tmp/datn-release.XXXXXX)"
trap 'rm -rf "$release_dir"' EXIT

tar -xzf "$archive" -C "$release_dir"
sudo rsync -a --delete --exclude=.env.production "$release_dir"/ /opt/dATN/
printf '%s\n' 'd2e04d74f97f149b2da54cf5e3810d6c7625e8ba' | sudo tee /opt/dATN/.release-commit >/dev/null
rm -f "$archive"

cd /opt/dATN
test -f database/1000_final.sql
sha256sum database/1000_final.sql
du -sh /opt/dATN
