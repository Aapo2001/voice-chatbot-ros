"""Helpers for guarding PyTorch CUDA usage against unsupported GPUs."""

from __future__ import annotations


def describe_torch_cuda_support() -> tuple[bool, str]:
    """Report whether the current Torch build supports the active CUDA GPU."""
    try:
        import torch
    except Exception as exc:
        return False, f"PyTorch import failed: {exc}"

    if not torch.cuda.is_available():
        return False, "CUDA is not available in the current PyTorch runtime."

    try:
        device_name = torch.cuda.get_device_name(0)
        capability = torch.cuda.get_device_capability(0)
        supported_arches = [
            arch for arch in torch.cuda.get_arch_list() if arch.startswith("sm_")
        ]
    except Exception as exc:
        return (
            True,
            f"CUDA is available, but GPU compatibility could not be checked: {exc}",
        )

    current_arch = f"sm_{capability[0]}{capability[1]}"
    if supported_arches and current_arch not in supported_arches:
        supported = " ".join(supported_arches)
        return (
            False,
            f"GPU '{device_name}' reports {current_arch}, but this PyTorch build "
            f"only supports {supported}.",
        )

    return (
        True,
        f"GPU '{device_name}' ({current_arch}) is supported by this PyTorch build.",
    )


def disable_tts_gpu_if_unsupported(config) -> str | None:
    """Turn off TTS CUDA when Torch can see a GPU but cannot execute kernels on it."""
    if not getattr(config, "tts_gpu", False):
        return None

    supported, reason = describe_torch_cuda_support()
    if supported:
        return None

    config.tts_gpu = False
    return f"TTS GPU disabled. Falling back to CPU. {reason}"
