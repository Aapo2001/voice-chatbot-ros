"""Ensure llama-cpp-python is built with CUDA support on Windows."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _llama_supports_gpu_offload() -> bool:
    code = (
        "import llama_cpp.llama_cpp as ll; "
        "print('1' if ll.llama_supports_gpu_offload() else '0')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() == "1"


def _find_vswhere() -> Path | None:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", ""))
        / "Microsoft Visual Studio/Installer/vswhere.exe",
        Path(os.environ.get("ProgramFiles", ""))
        / "Microsoft Visual Studio/Installer/vswhere.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _find_vcvars64() -> Path:
    preferred = [
        Path(
            r"C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
        ),
        Path(
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
        ),
    ]
    for candidate in preferred:
        if candidate.is_file():
            return candidate

    vswhere = _find_vswhere()
    if vswhere is not None:
        result = subprocess.run(
            [
                str(vswhere),
                "-latest",
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        install_path = result.stdout.strip()
        if install_path:
            vcvars = Path(install_path) / "VC/Auxiliary/Build/vcvars64.bat"
            if vcvars.is_file():
                return vcvars

    fallbacks = [
        Path(
            r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
        ),
    ]
    for candidate in fallbacks:
        if candidate.is_file():
            return candidate

    raise RuntimeError("Could not locate Visual Studio vcvars64.bat.")


def _find_cuda_root() -> Path:
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        cuda_root = Path(cuda_path)
        if (cuda_root / "bin/nvcc.exe").is_file():
            return cuda_root

    nvcc_path = shutil.which("nvcc")
    if nvcc_path:
        return Path(nvcc_path).resolve().parent.parent

    raise RuntimeError(
        "Could not locate nvcc. CUDA toolkit is required for GGML_CUDA builds."
    )


def main() -> int:
    if _llama_supports_gpu_offload():
        print("[llm-cuda] llama-cpp-python already supports GPU offload.")
        return 0

    if os.name != "nt":
        raise RuntimeError(
            "Automatic llama-cpp-python CUDA rebuild is only implemented for Windows."
        )

    version = "0.3.19"
    vcvars64 = _find_vcvars64()
    cuda_root = _find_cuda_root()

    print(f"[llm-cuda] Rebuilding llama-cpp-python {version} with GGML_CUDA=on...")
    print(f"[llm-cuda] Using vcvars64: {vcvars64}")
    print(f"[llm-cuda] Using CUDA toolkit: {cuda_root}")

    script_contents = "\n".join(
        [
            "@echo off",
            f'call "{vcvars64}"',
            'set "CMAKE_GENERATOR=NMake Makefiles"',
            'set "CMAKE_ARGS=-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=120"',
            'set "FORCE_CMAKE=1"',
            f'set "CUDA_PATH={cuda_root}"',
            f'set "CUDAToolkit_ROOT={cuda_root}"',
            f'set "CUDACXX={cuda_root}\\bin\\nvcc.exe"',
            f'"{sys.executable}" -m pip install --force-reinstall --no-cache-dir --no-deps "llama-cpp-python=={version}"',
        ]
    )

    with tempfile.NamedTemporaryFile(
        "w", suffix=".bat", delete=False, encoding="utf-8"
    ) as script_file:
        script_file.write(script_contents)
        script_path = Path(script_file.name)

    try:
        subprocess.run(["cmd.exe", "/d", "/c", str(script_path)], check=True)
    finally:
        script_path.unlink(missing_ok=True)

    if not _llama_supports_gpu_offload():
        raise RuntimeError(
            "llama-cpp-python rebuild completed, but GPU offload is still unavailable."
        )

    print("[llm-cuda] llama-cpp-python now supports GPU offload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
