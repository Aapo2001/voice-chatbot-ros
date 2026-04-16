#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PACKAGE_ROOT/../.." && pwd)"
ROOT_MANIFEST_PATH="$PROJECT_ROOT/pixi.toml"
PACKAGE_MANIFEST_PATH="$PACKAGE_ROOT/pixi.toml"
WORKSPACE_SETUP_PATH="$PROJECT_ROOT/install/setup.bash"

usage() {
    echo "Usage: ros_exec_pixi.sh <run|launch> <package> <executable-or-launch-file> [args...]" >&2
    exit 2
}

MODE="${1:-}"
PACKAGE_NAME="${2:-}"
TARGET_NAME="${3:-}"

if [[ -z "$MODE" || -z "$PACKAGE_NAME" || -z "$TARGET_NAME" ]]; then
    usage
fi

if [[ "${SOP_ROS_EXEC_PIXI:-0}" != "1" ]]; then
    if [[ ! -f "$ROOT_MANIFEST_PATH" ]]; then
        echo "ERROR: pixi manifest not found at '$ROOT_MANIFEST_PATH'." >&2
        exit 1
    fi

    exec env -u PIXI_PROJECT_MANIFEST \
        pixi run --manifest-path "$ROOT_MANIFEST_PATH" \
        env SOP_ROS_EXEC_PIXI=1 \
        bash "$0" "$@"
fi

source "$SCRIPT_DIR/setup_audio_env.sh"

if [[ ! -f "$WORKSPACE_SETUP_PATH" ]]; then
    if [[ -f "$PACKAGE_ROOT/install/setup.bash" ]]; then
        WORKSPACE_SETUP_PATH="$PACKAGE_ROOT/install/setup.bash"
    else
        echo "ERROR: install/setup.bash not found. Run \`pixi run build\` first." >&2
        exit 1
    fi
fi

# Colcon-generated setup scripts access optional variables like COLCON_TRACE
# directly, which breaks under `set -u`.
set +u
source "$WORKSPACE_SETUP_PATH"
set -u

cd "$PROJECT_ROOT"

shift 3

case "$MODE" in
    run)
        exec ros2 run "$PACKAGE_NAME" "$TARGET_NAME" "$@"
        ;;
    launch)
        exec ros2 launch "$PACKAGE_NAME" "$TARGET_NAME" "$@"
        ;;
    *)
        usage
        ;;
esac
