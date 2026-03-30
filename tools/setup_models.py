"""ROS 2 wrapper for voice_chatbot.setup_models.

Calls the same setup functions but prints the correct launch command
for this ROS 2 project instead of the standalone chatbot.
"""

from voice_chatbot.config import Config
from voice_chatbot.setup_models import (
    check_cuda,
    setup_llm,
    setup_tts,
    setup_vad,
    setup_whisper,
)


def main() -> None:
    config = Config.load()
    print("=" * 50)
    print("  Voice Chatbot ROS 2 — Model Setup")
    print("=" * 50)

    check_cuda()
    setup_vad()
    setup_whisper(config)
    setup_llm(config)
    setup_tts(config)

    print("\n" + "=" * 50)
    print("  Setup complete!")
    print("=" * 50)
    print("\nAll models are downloaded and ready.")
    print("Run 'pixi run ros-start' to launch all ROS 2 nodes.")


if __name__ == "__main__":
    main()
