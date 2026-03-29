# Voice Chatbot — ROS 2 Integration

ROS 2 Humble nodes for the [voice-chatbot](https://pypi.org/project/voice-chatbot/) pipeline. Splits the speech-to-speech assistant into distributed STT, LLM, and TTS nodes communicating via ROS topics.

## Prerequisites

- [pixi](https://pixi.sh) package manager
- The `voice-chatbot` pip package: `pip install voice-chatbot[all]`
- CUDA-capable GPU (recommended)

## Quick Start

```bash
# Install dependencies
pixi install
pixi run install-python-deps

# Build the ROS 2 package
pixi run build

# Option A — all four tabs (STT, LLM, TTS, GUI):
pixi run ros-start

# Option B — individual nodes:
pixi run ros-stt    # STT node: mic + VAD + Whisper
pixi run ros-llm    # LLM node: LLaMA chat inference
pixi run ros-tts    # TTS node: Coqui TTS + audio playback
pixi run ros-app    # PySide6 GUI (connects to running nodes)

# Option C — launch file (3 nodes in one process group):
pixi run ros-launch
```

## Node Architecture

| Node | File | Responsibilities |
|------|------|-----------------|
| **STT** | `voice_chatbot_ros/stt_node.py` | Microphone capture, VAD, Whisper transcription |
| **LLM** | `voice_chatbot_ros/llm_node.py` | Receives text, runs LLaMA inference |
| **TTS** | `voice_chatbot_ros/tts_node.py` | Synthesizes speech, plays audio |
| **GUI** | `voice_chatbot_ros/ros_app.py` | PySide6 interface subscribing to all topics |

## Dependencies

This package depends on the [`voice-chatbot`](https://pypi.org/project/voice-chatbot/) pip package for all pipeline functionality (audio I/O, VAD, STT, LLM, TTS, config, and GUI components).

## License

MIT
