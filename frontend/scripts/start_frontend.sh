#!/usr/bin/env bash

set -euo pipefail

PORT="${PORT:-8080}"

exec npx serve -s dist -l "${PORT}"
