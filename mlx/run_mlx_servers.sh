#!/usr/bin/env bash
set -euo pipefail

TEXT_PORT="${VLLM_TEXT_PORT:-11435}"
VISION_PORT="${VLLM_VISION_PORT:-11436}"

TEXT_MODEL="${VLLM_TEXT_MODEL:-mlx-community/Llama-3.2-3B-Instruct-4bit}"
VISION_MODEL="${VLLM_VISION_MODEL:-mlx-community/Qwen3-VL-4B-Instruct-3bit}"

export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"

if ! command -v vllm-mlx >/dev/null 2>&1; then
  echo "vllm-mlx not found."
  echo "Install: uv tool install vllm-mlx"
  exit 1
fi

declare -a COMMON_ARGS=()
if [[ "${VLLM_CONTINUOUS_BATCHING:-0}" == "1" ]]; then
  COMMON_ARGS+=(--continuous-batching)
fi
if [[ -n "${VLLM_API_KEY:-}" ]]; then
  COMMON_ARGS+=(--api-key "${VLLM_API_KEY}")
fi

echo "Starting vllm-mlx text server on port ${TEXT_PORT}..."
if [[ ${#COMMON_ARGS[@]} -gt 0 ]]; then
  vllm-mlx serve "${TEXT_MODEL}" --port "${TEXT_PORT}" "${COMMON_ARGS[@]}" &
else
  vllm-mlx serve "${TEXT_MODEL}" --port "${TEXT_PORT}" &
fi
TEXT_PID=$!

echo "Starting vllm-mlx vision server on port ${VISION_PORT}..."
if [[ ${#COMMON_ARGS[@]} -gt 0 ]]; then
  vllm-mlx serve "${VISION_MODEL}" --port "${VISION_PORT}" "${COMMON_ARGS[@]}" &
else
  vllm-mlx serve "${VISION_MODEL}" --port "${VISION_PORT}" &
fi
VISION_PID=$!

trap 'kill "${TEXT_PID}" "${VISION_PID}" 2>/dev/null || true' SIGINT SIGTERM
wait "${TEXT_PID}" "${VISION_PID}"
