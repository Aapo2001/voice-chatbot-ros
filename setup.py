"""
``setup.py`` for the ``voice_chatbot_ros`` ROS 2 package.

Used by ``colcon build`` (via ``ament_python``) to install the ROS 2
nodes into the local workspace overlay.

The core pipeline functionality is provided by the ``voice-chatbot``
pip package (https://pypi.org/project/voice-chatbot/).
"""

from glob import glob

from setuptools import find_packages, setup

package_name = "voice_chatbot_ros"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(include=[package_name, f"{package_name}.*"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            [f"resource/{package_name}"],
        ),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.py")),
    ],
    install_requires=[
        "setuptools",
        "voice-chatbot",
    ],
    zip_safe=True,
    maintainer="Aapo Pihlajaniemi",
    maintainer_email="aapoto1201@gmail.com",
    description="ROS 2 Humble integration for the voice-chatbot pipeline.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "voice_chatbot_ros_app = voice_chatbot_ros.ros_app:main",
            "unified_app = voice_chatbot_ros.unified_app:main",
            "voice_chatbot_node = voice_chatbot_ros.node:main",
            "voice_stt_node = voice_chatbot_ros.stt_node:main",
            "voice_llm_node = voice_chatbot_ros.llm_node:main",
            "voice_tts_node = voice_chatbot_ros.tts_node:main",
        ],
    },
)
