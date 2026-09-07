#!/usr/bin/env bash
set -euo pipefail

readonly image_ref="${1:?Usage: smoke_test.sh IMAGE_REFERENCE}"

readonly image_user="$(docker image inspect "${image_ref}" --format '{{.Config.User}}')"
readonly image_architecture="$(
  docker image inspect "${image_ref}" --format '{{.Architecture}}'
)"

[[ "${image_user}" == "10001:10001" ]]
[[ "${image_architecture}" == "amd64" ]]

docker run --rm "${image_ref}" python -c '
import os
import shutil
import subprocess

assert os.getuid() == 10001
assert os.getgid() == 10001
assert subprocess.check_output(["opengrep", "--version"], text=True).strip() == "1.23.0"
assert subprocess.check_output(["trivy", "--version"], text=True).strip() == "Version: 0.71.2"
assert shutil.which("uv") is None
'

container_id="$(docker run --detach "${image_ref}")"
cleanup() {
  docker rm --force "${container_id}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in {1..30}; do
  if docker exec "${container_id}" python -c '
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
    assert response.status == 200
' >/dev/null 2>&1; then
    echo "Container health check passed"
    exit 0
  fi

  if [[ "$(docker inspect --format '{{.State.Running}}' "${container_id}")" != "true" ]]; then
    docker logs "${container_id}"
    exit 1
  fi
  sleep 2
done

docker logs "${container_id}"
echo "Container did not become healthy within 60 seconds" >&2
exit 1
