#!/usr/bin/env bash
set -u

check() {
  local name="$1"
  local command="$2"

  if command -v "$command" >/dev/null 2>&1; then
    printf "ok   %-12s %s\n" "$name" "$($command --version 2>/dev/null | head -n 1)"
  else
    printf "miss %-12s install %s\n" "$name" "$command"
  fi
}

check "python" "python3"
check "node" "node"
check "npm" "npm"
check "corepack" "corepack"
check "pnpm" "pnpm"
if command -v uv >/dev/null 2>&1; then
  printf "ok   %-12s %s\n" "uv" "$(uv --version 2>/dev/null | head -n 1)"
elif [ -x "$HOME/.local/bin/uv" ]; then
  printf "ok   %-12s %s at %s\n" "uv" "$("$HOME/.local/bin/uv" --version 2>/dev/null | head -n 1)" "$HOME/.local/bin/uv"
  printf "hint %-12s add %s to PATH for direct uv usage\n" "uv" "$HOME/.local/bin"
else
  printf "miss %-12s install uv\n" "uv"
fi
if command -v make >/dev/null 2>&1; then
  printf "ok   %-12s %s\n" "make" "$(make --version 2>/dev/null | head -n 1)"
else
  printf "warn %-12s optional; use bash scripts/dev.sh instead\n" "make"
fi
check "docker" "docker"

if docker compose version >/dev/null 2>&1; then
  printf "ok   %-12s %s\n" "compose" "$(docker compose version)"
else
  printf "miss %-12s install Docker Compose v2\n" "compose"
fi

tmp_venv="$(mktemp -d)"
if python3 -m venv "$tmp_venv/.venv-check" >/dev/null 2>&1; then
  printf "ok   %-12s python venv available\n" "venv"
else
  printf "warn %-12s optional for this project because uv already manages .venv\n" "venv"
fi
rm -rf "$tmp_venv"

if docker info >/dev/null 2>&1; then
  printf "ok   %-12s docker daemon accessible\n" "docker-sock"
else
  printf "warn %-12s current user cannot access Docker daemon without elevated permission\n" "docker-sock"
fi
