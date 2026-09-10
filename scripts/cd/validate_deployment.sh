#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 EXPECTED_CONFIRMATION REQUIRED_ENV_VAR..." >&2
  exit 2
fi

expected_confirmation="$1"
shift

case "${DEPLOY_OPERATION:-}" in
  plan)
    ;;
  apply)
    if [[ "${DEPLOY_CONFIRMATION:-}" != "$expected_confirmation" ]]; then
      echo "apply requires confirmation: $expected_confirmation" >&2
      exit 1
    fi
    ;;
  *)
    echo "DEPLOY_OPERATION must be plan or apply" >&2
    exit 1
    ;;
esac

missing=()
for variable_name in "$@"; do
  if [[ -z "${!variable_name:-}" ]]; then
    missing+=("$variable_name")
  fi
done

if (( ${#missing[@]} > 0 )); then
  printf 'missing deployment variable: %s\n' "${missing[@]}" >&2
  exit 1
fi
