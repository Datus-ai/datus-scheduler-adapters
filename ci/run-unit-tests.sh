#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'USAGE'
Usage: ci/run-unit-tests.sh [--list] [--dry-run] [package]

Runs deterministic unit tests for the Airflow scheduler adapter.

Options:
  --list      List configured package targets.
  --dry-run   Print selected package target without running pytest.
  -h, --help  Show this help.
USAGE
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: $command_name" >&2
    exit 127
  fi
}

dry_run=0
requested_package=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --list)
      printf '%s\t%s\n' "datus-scheduler-airflow" "datus-scheduler-airflow/tests/test_unit.py"
      exit 0
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [ -n "$requested_package" ]; then
        echo "Only one package can be selected" >&2
        usage >&2
        exit 2
      fi
      requested_package="$1"
      shift
      ;;
  esac
done

require_command uv

if [ -n "$requested_package" ] && [ "$requested_package" != "datus-scheduler-airflow" ]; then
  echo "Unknown package: $requested_package" >&2
  usage >&2
  exit 2
fi

if [ "$dry_run" -eq 1 ]; then
  echo "=== Unit tests: datus-scheduler-airflow ==="
  echo "pytest target: datus-scheduler-airflow/tests/test_unit.py"
  exit 0
fi

uv run --with pytest --with pytest-asyncio --package datus-scheduler-airflow pytest \
  datus-scheduler-airflow/tests/test_unit.py \
  -m "not integration" \
  --tb=short \
  --verbose
