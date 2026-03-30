"""Helpers for verifying llama.cpp GPU offload support."""

from __future__ import annotations


def describe_llm_gpu_offload(config) -> tuple[bool, str]:
    """Report whether the current llama.cpp backend can honor GPU offload."""
    requested_layers = int(getattr(config, "llm_n_gpu_layers", 0))
    if requested_layers == 0:
        return False, "LLM GPU offload is disabled by config (`llm_n_gpu_layers = 0`)."

    try:
        import llama_cpp.llama_cpp as llama_cpp_backend
    except Exception as exc:
        return False, f"Could not import llama-cpp-python: {exc}"

    if not llama_cpp_backend.llama_supports_gpu_offload():
        return (
            False,
            "llama-cpp-python was built without CUDA GPU offload support.",
        )

    if requested_layers < 0:
        return True, "LLM GPU offload enabled: all supported layers will run on CUDA."

    return (
        True,
        f"LLM GPU offload enabled: {requested_layers} layers requested on CUDA.",
    )
