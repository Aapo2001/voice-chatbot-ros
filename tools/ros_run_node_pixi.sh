#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  ros_run_node_pixi.sh — Run a single ROS 2 voice chatbot node
#
#  Usage: ros_run_node_pixi.sh <node_executable_name> [config_path]
#    e.g.: ros_run_node_pixi.sh voice_stt_node
#           ros_run_node_pixi.sh voice_llm_node /absolute/path/config.json
#
#  Sources the local colcon workspace overlay (install/setup.bash)
#  then starts the node in the /voice_chatbot namespace.
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PACKAGE_ROOT/../.." && pwd)"
DEFAULT_CONFIG_PATH="$PROJECT_ROOT/config.json"

source "$SCRIPT_DIR/setup_audio_env.sh"

NODE_NAME="${1:?Usage: ros_run_node_pixi.sh <node_executable_name>}"
if [[ -f "$DEFAULT_CONFIG_PATH" ]]; then
    CONFIG_PATH="${2:-$DEFAULT_CONFIG_PATH}"
else
    CONFIG_PATH="${2:-$PACKAGE_ROOT/config.json}"
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

exec ros2 run voice_chatbot_ros "${NODE_NAME}" --ros-args -p config_path:="${CONFIG_PATH}" -r __ns:=/voice_chatbot
