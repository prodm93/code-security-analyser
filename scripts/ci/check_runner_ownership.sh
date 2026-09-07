#!/usr/bin/env bash
set -euo pipefail

# Fail closed if a hosted-runner image makes system directories writable by its
# unprivileged job account.
for protected_path in /etc /usr; do
  owner="$(stat --format='%U:%G' -- "${protected_path}")"
  if [[ "${owner}" != "root:root" ]]; then
    echo "::error::${protected_path} has unexpected owner ${owner}; expected root:root"
    exit 1
  fi
done
