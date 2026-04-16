#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  ros_start_all.sh — Launch all ROS 2 voice chatbot processes
#
#  Opens four tabs in a single GNOME Terminal window:
#    Tab 1: STT node   (mic + VAD + Whisper)
#    Tab 2: LLM node   (LLaMA/GGUF chat inference)
#    Tab 3: TTS node   (Coqui TTS + speaker playback)
#    Tab 4: Unified UI (RViz + image viewer + voice chatbot, delayed 2 s)
#
#  Requires gnome-terminal.  Falls back to manual instructions.
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PACKAGE_ROOT/../.." && pwd)"
MANIFEST_PATH="$PACKAGE_ROOT/pixi.toml"
DEFAULT_CONFIG_PATH="$PROJECT_ROOT/config.json"

echo "Starting ROS 2 voice chatbot..."

env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path "$MANIFEST_PATH" ensure-llm-cuda
env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path "$MANIFEST_PATH" build

if [[ -f "$DEFAULT_CONFIG_PATH" ]]; then
    CONFIG_PATH="$DEFAULT_CONFIG_PATH"
else
    CONFIG_PATH="$PACKAGE_ROOT/config.json"
fi

if ! command -v gnome-terminal &>/dev/null; then
    echo "gnome-terminal not found. Run each manually in separate terminals:"
    echo "  env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path \"$MANIFEST_PATH\" bash tools/ros_run_node_pixi.sh voice_stt_node \"$CONFIG_PATH\""
    echo "  env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path \"$MANIFEST_PATH\" bash tools/ros_run_node_pixi.sh voice_llm_node \"$CONFIG_PATH\""
    echo "  env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path \"$MANIFEST_PATH\" bash tools/ros_run_node_pixi.sh voice_tts_node \"$CONFIG_PATH\""
    echo "  env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path \"$MANIFEST_PATH\" bash tools/ros_run_node_pixi.sh voice_chatbot_ros_app \"$CONFIG_PATH\""
    exit 1
fi

TAB_STT="cd '$PACKAGE_ROOT' && env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path '$MANIFEST_PATH' bash tools/ros_run_node_pixi.sh voice_stt_node '$CONFIG_PATH'; exec bash"
TAB_LLM="cd '$PACKAGE_ROOT' && env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path '$MANIFEST_PATH' bash tools/ros_run_node_pixi.sh voice_llm_node '$CONFIG_PATH'; exec bash"
TAB_TTS="cd '$PACKAGE_ROOT' && env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path '$MANIFEST_PATH' bash tools/ros_run_node_pixi.sh voice_tts_node '$CONFIG_PATH'; exec bash"
TAB_GUI="cd '$PACKAGE_ROOT' && sleep 2 && env -u PIXI_PROJECT_MANIFEST pixi run --manifest-path '$MANIFEST_PATH' bash tools/ros_run_node_pixi.sh voice_chatbot_ros_app '$CONFIG_PATH'; exec bash"

gnome-terminal --window --title="STT" -- bash -lc "$TAB_STT"
gnome-terminal --tab --title="LLM" -- bash -lc "$TAB_LLM"
gnome-terminal --tab --title="TTS" -- bash -lc "$TAB_TTS"
gnome-terminal --tab --title="GUI" -- bash -lc "$TAB_GUI"

echo "All tabs launched."
