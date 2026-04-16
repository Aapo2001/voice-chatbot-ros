"""Ensure llama-cpp-python is built with CUDA support."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
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


def _stamp_path() -> Path:
    return Path(sys.prefix) / ".llama_cpp_cuda_stamp.json"


def _llama_package_artifact_mtimes() -> list[float]:
    mtimes: list[float] = []

    spec = importlib.util.find_spec("llama_cpp")
    if spec and spec.origin:
        package_dir = Path(spec.origin).resolve().parent
        for pattern in ("*.py", "*.so", "*.pyd", "*.dll", "*.dylib"):
            for path in package_dir.rglob(pattern):
                try:
                    mtimes.append(path.stat().st_mtime)
                except FileNotFoundError:
                    pass

    try:
        distribution = importlib.metadata.distribution("llama-cpp-python")
    except importlib.metadata.PackageNotFoundError:
        return mtimes

    for file in distribution.files or []:
        path = distribution.locate_file(file)
        if ".dist-info" not in path.parts:
            continue
        try:
            mtimes.append(path.stat().st_mtime)
        except FileNotFoundError:
            pass

    return mtimes


def _build_env(cuda_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    cmake_args = ["-DGGML_CUDA=on"]
    cuda_arch = env.get("CMAKE_CUDA_ARCHITECTURES") or env.get(
        "LLAMA_CMAKE_CUDA_ARCHITECTURES"
    )
    if cuda_arch:
        cmake_args.append(f"-DCMAKE_CUDA_ARCHITECTURES={cuda_arch}")

    env.update(
        {
            "CMAKE_ARGS": " ".join(cmake_args),
            "FORCE_CMAKE": "1",
            "CUDA_PATH": str(cuda_root),
            "CUDA_HOME": str(cuda_root),
            "CUDAToolkit_ROOT": str(cuda_root),
            "CUDACXX": str(cuda_root / "bin" / _nvcc_name()),
        }
    )
    return env


def _stamp_payload(version: str, cuda_root: Path) -> dict[str, str]:
    return {
        "python_executable": sys.executable,
        "python_prefix": sys.prefix,
        "llama_cpp_python_version": version,
        "cuda_root": str(cuda_root),
        "cmake_args": _build_env(cuda_root)["CMAKE_ARGS"],
    }


def _has_current_cuda_rebuild_stamp(version: str, cuda_root: Path) -> bool:
    stamp_path = _stamp_path()
    if not stamp_path.is_file():
        return False

    try:
        stamp_data = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    if stamp_data != _stamp_payload(version, cuda_root):
        return False

    try:
        stamp_mtime = stamp_path.stat().st_mtime
    except FileNotFoundError:
        return False

    artifact_mtimes = _llama_package_artifact_mtimes()
    return not artifact_mtimes or stamp_mtime >= max(artifact_mtimes)


def _write_cuda_rebuild_stamp(version: str, cuda_root: Path) -> None:
    stamp_path = _stamp_path()
    stamp_path.write_text(
        json.dumps(_stamp_payload(version, cuda_root), indent=2, sort_keys=True),
        encoding="utf-8",
    )


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


def _nvcc_name() -> str:
    return "nvcc.exe" if os.name == "nt" else "nvcc"


def _has_nvcc(cuda_root: Path) -> bool:
    return (cuda_root / "bin" / _nvcc_name()).is_file()


def _find_cuda_root() -> Path:
    for env_name in ("CUDA_PATH", "CUDA_HOME", "CUDAToolkit_ROOT"):
        cuda_path = os.environ.get(env_name)
        if not cuda_path:
            continue
        cuda_root = Path(cuda_path)
        if _has_nvcc(cuda_root):
            return cuda_root

    nvcc_path = shutil.which("nvcc")
    if nvcc_path:
        return Path(nvcc_path).resolve().parent.parent

    if os.name != "nt":
        for candidate in sorted(Path("/usr/local").glob("cuda*"), reverse=True):
            if _has_nvcc(candidate):
                return candidate
        for candidate in sorted(Path("/opt").glob("cuda*"), reverse=True):
            if _has_nvcc(candidate):
                return candidate

    raise RuntimeError(
        "Could not locate nvcc. CUDA toolkit is required for GGML_CUDA builds."
    )


def _reinstall_llama_with_cuda_on_windows(version: str, cuda_root: Path) -> None:
    vcvars64 = _find_vcvars64()
    build_env = _build_env(cuda_root)

    print(f"[llm-cuda] Using vcvars64: {vcvars64}")
    print(f"[llm-cuda] Using CUDA toolkit: {cuda_root}")

    script_contents = "\n".join(
        [
            "@echo off",
            f'call "{vcvars64}"',
            'set "CMAKE_GENERATOR=NMake Makefiles"',
            f'set "CMAKE_ARGS={build_env["CMAKE_ARGS"]}"',
            'set "FORCE_CMAKE=1"',
            f'set "CUDA_PATH={cuda_root}"',
            f'set "CUDA_HOME={cuda_root}"',
            f'set "CUDAToolkit_ROOT={cuda_root}"',
            f'set "CUDACXX={cuda_root}\\bin\\{_nvcc_name()}"',
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


def _reinstall_llama_with_cuda_on_posix(version: str, cuda_root: Path) -> None:
    build_env = _build_env(cuda_root)

    print(f"[llm-cuda] Using CUDA toolkit: {cuda_root}")
    print(f"[llm-cuda] Using CMAKE_ARGS: {build_env['CMAKE_ARGS']}")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-cache-dir",
            "--no-deps",
            f"llama-cpp-python=={version}",
        ],
        check=True,
        env=build_env,
    )


def main() -> int:
    version = "0.3.19"
    cuda_root = _find_cuda_root()
    supports_gpu_offload = _llama_supports_gpu_offload()

    if _has_current_cuda_rebuild_stamp(version, cuda_root) and supports_gpu_offload:
        print("[llm-cuda] Existing CUDA rebuild stamp is current; skipping rebuild.")
        return 0

    if supports_gpu_offload:
        print("[llm-cuda] llama-cpp-python already supports GPU offload.")
        _write_cuda_rebuild_stamp(version, cuda_root)
        return 0

    if _has_current_cuda_rebuild_stamp(version, cuda_root):
        print(
            "[llm-cuda] CUDA rebuild stamp is present, but GPU offload is unavailable. Rebuilding..."
        )

    print(f"[llm-cuda] Rebuilding llama-cpp-python {version} with GGML_CUDA=on...")
    if os.name == "nt":
        _reinstall_llama_with_cuda_on_windows(version, cuda_root)
    else:
        _reinstall_llama_with_cuda_on_posix(version, cuda_root)

    if not _llama_supports_gpu_offload():
        raise RuntimeError(
            "llama-cpp-python rebuild completed, but GPU offload is still unavailable."
        )

    _write_cuda_rebuild_stamp(version, cuda_root)
    print("[llm-cuda] llama-cpp-python now supports GPU offload.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
