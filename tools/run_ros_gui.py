"""Launch the ROS 2 GUI with PySide6 DLL path fix for Windows.

In conda environments, Python's default DLL search
(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS) cannot resolve PySide6's bundled
Qt library dependencies.  Pre-loading them with the legacy search
mode (winmode=0) before any PySide6 submodule import fixes this.
"""

import os
import sys

if sys.platform == "win32":
    import ctypes
    import site

    for sp in site.getsitepackages():
        pyside_dir = os.path.join(sp, "PySide6")
        if os.path.isdir(pyside_dir):
            os.add_dll_directory(pyside_dir)
            for dll in ("Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll"):
                dll_path = os.path.join(pyside_dir, dll)
                if os.path.isfile(dll_path):
                    ctypes.CDLL(dll_path, winmode=0)
            break

from voice_chatbot_ros.ros_app import main  # noqa: E402

main()
