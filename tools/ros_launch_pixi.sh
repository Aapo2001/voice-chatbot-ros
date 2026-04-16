#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PACKAGE_ROOT/../.." && pwd)"
DEFAULT_CONFIG_PATH="$PROJECT_ROOT/config.json"
MANIFEST_PATH="$PACKAGE_ROOT/pixi.toml"

source "$SCRIPT_DIR/setup_audio_env.sh"

env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path "$MANIFEST_PATH" ensure-llm-cuda

if [[ -f "$DEFAULT_CONFIG_PATH" ]]; then
    CONFIG_PATH="${1:-$DEFAULT_CONFIG_PATH}"
else
    CONFIG_PATH="${1:-$PACKAGE_ROOT/config.json}"
fi

if [[ ! -f "$PACKAGE_ROOT/install/setup.bash" ]]; then
    echo "ERROR: install/setup.bash not found. Run \`pixi run build\` first." >&2
    exit 1
fi

# Colcon-generated setup scripts access optional variables like COLCON_TRACE
# directly, which breaks under `set -u`.
set +u
source "$PACKAGE_ROOT/install/setup.bash"
set -u

cd "$PROJECT_ROOT"

exec ros2 launch voice_chatbot_ros voice_chatbot.launch.py \
    config_path:="${CONFIG_PATH}"
