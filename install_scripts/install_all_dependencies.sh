#!/usr/bin/env bash
set -euo pipefail

# Install Python dependencies from requirements files at the OctoBot repo root
# and under OctoBot/packages (any subdirectory).
# Ignores requirement files under packages/<dir>/ for each name in PACKAGES_IGNORE_DIRS.
# dev_requirements.txt under packages/ is ignored; repo root dev_requirements.txt is used.
# One pip install with multiple -r flags.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OCTOBOT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PACKAGES_DIR="$OCTOBOT_ROOT/packages"

# Basenames under packages/ to skip (blacklist). Example: (binary other_pkg)
PACKAGES_IGNORE_DIRS=(binary)

packages_path_is_blacklisted() {
  local f="$1"
  local d
  for d in "${PACKAGES_IGNORE_DIRS[@]}"; do
    if [[ "$f" == *"/packages/${d}/"* ]]; then
      return 0
    fi
  done
  return 1
}

if command -v python3 >/dev/null 2>&1; then
  PIP=(python3 -m pip)
elif command -v python >/dev/null 2>&1; then
  PIP=(python -m pip)
else
  echo "error: neither python3 nor python found in PATH" >&2
  exit 1
fi

req_files=()
for name in full_requirements.txt requirements.txt dev_requirements.txt; do
  path="$OCTOBOT_ROOT/$name"
  if [[ -f "$path" ]]; then
    req_files+=("$path")
  fi
done

if [[ -d "$PACKAGES_DIR" ]]; then
  while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    if packages_path_is_blacklisted "$file"; then
      continue
    fi
    req_files+=("$file")
  done < <(
    find "$PACKAGES_DIR" -type f \( \
      -name full_requirements.txt -o \
      -name requirements.txt \
    \) -print | LC_ALL=C sort
  )
fi

if [[ ${#req_files[@]} -eq 0 ]]; then
  echo "Nothing to install (no requirements files found)."
  exit 0
fi

echo ""
echo "Requirements files used (${#req_files[@]} total), in pip order:"
i=1
for f in "${req_files[@]}"; do
  printf '  %2d. %s\n' "$i" "$f"
  i=$((i + 1))
done
echo ""
echo "Running pip install with all -r files above."
args=()
for f in "${req_files[@]}"; do
  args+=(-r "$f")
done
"${PIP[@]}" install "${args[@]}"
