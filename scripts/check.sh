#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -n "${PYTHON:-}" ]]; then
    PYTHON_BIN="$PYTHON"
elif [[ -x ".venv/bin/python" ]]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

report_failure() {
    local status="$1"
    shift
    local command
    printf -v command '%q ' "$@"
    printf '\nerror: command failed (%s): %s\n' "$status" "$command" >&2
    if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
        command="${command//'%'/'%25'}"
        command="${command//$'\r'/'%0D'}"
        command="${command//$'\n'/'%0A'}"
        printf '::error title=check.sh command failed::%s (exit %s)\n' "$command" "$status" >&2
    fi
    return "$status"
}

run() {
    printf '\n==> %s\n' "$*"
    if "$@"; then
        return 0
    else
        local status=$?
        report_failure "$status" "$@"
    fi
}

run_to_file() {
    local output_path="$1"
    shift
    printf '\n==> %s > %s\n' "$*" "$output_path"
    if "$@" > "$output_path"; then
        return 0
    else
        local status=$?
        report_failure "$status" "$@"
    fi
}

run "$PYTHON_BIN" -m compileall -q app core scripts tests server.py
run "$PYTHON_BIN" -m ruff check app core scripts tests server.py
run "$PYTHON_BIN" -m ruff format --check app core scripts tests server.py
run "$PYTHON_BIN" -m coverage erase
run "$PYTHON_BIN" -m coverage run -m unittest discover -s tests
run "$PYTHON_BIN" -m coverage report

if [[ -f "package.json" ]]; then
    if ! command -v npm >/dev/null 2>&1; then
        printf '\nerror: npm is required for frontend checks\n' >&2
        exit 1
    fi
    run npm run lint:web
    run npm run test:web
fi

mkdir -p analiza
run_to_file analiza/architecture_diagnostics.md "$PYTHON_BIN" scripts/diagnose_architecture.py \
    --output-json analiza/architecture_diagnostics.json \
    --markdown \
    --strict
run "$PYTHON_BIN" scripts/diagnose_data.py --no-image-check --output-json analiza/data_diagnostics.json

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    run git diff --check
else
    printf '\n==> git diff --check\n'
    printf 'skip: git repository not available\n'
fi

printf '\nOK: local checks passed\n'
