#!/usr/bin/env bash
set -euo pipefail

prepend_ld_library_path() {
    local new_path="$1"
    if [[ -z "$new_path" || ! -d "$new_path" ]]; then
        return 0
    fi

    case ":${LD_LIBRARY_PATH:-}:" in
        *":$new_path:"*) ;;
        *)
            if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
                export LD_LIBRARY_PATH="$new_path:$LD_LIBRARY_PATH"
            else
                export LD_LIBRARY_PATH="$new_path"
            fi
            ;;
    esac
}

setup_python_cuda_runtime() {
    local lib_dirs
    local python_bin
    python_bin="$(command -v python || command -v python3 || true)"
    [[ -n "$python_bin" ]] || return 0

    if ! lib_dirs="$(
        "$python_bin" - <<'PY'
import importlib.util
from pathlib import Path

paths = []
for module_name in ("nvidia.cuda_runtime.lib", "nvidia.cublas.lib", "nvidia.cudnn.lib"):
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        continue
    if spec.submodule_search_locations:
        paths.append(str(Path(next(iter(spec.submodule_search_locations))).resolve()))
        continue
    if spec.origin:
        paths.append(str(Path(spec.origin).resolve().parent))

print(":".join(dict.fromkeys(paths)))
PY
    )"; then
        return 0
    fi

    local path
    local added=0
    IFS=':' read -r -a paths <<< "$lib_dirs"
    for path in "${paths[@]}"; do
        [[ -n "$path" ]] || continue
        case ":${LD_LIBRARY_PATH:-}:" in
            *":$path:"*) ;;
            *)
                prepend_ld_library_path "$path"
                added=1
                ;;
        esac
    done

    if [[ "$added" -eq 1 ]]; then
        echo "[cuda-env] Added NVIDIA runtime libs to LD_LIBRARY_PATH"
    fi
}

is_wsl() {
    [[ -n "${WSL_DISTRO_NAME:-}" ]] || uname -r | grep -qi microsoft
}

pick_wslg_pulse_server() {
    local candidate
    for candidate in \
        "unix:/run/user/$(id -u)/pulse/native" \
        "unix:/mnt/wslg/runtime-dir/pulse/native" \
        "unix:/mnt/wslg/PulseServer"
    do
        if [[ "$candidate" == unix:* && -S "${candidate#unix:}" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

if is_wsl; then
    if [[ -z "${XDG_RUNTIME_DIR:-}" && -d "/run/user/$(id -u)" ]]; then
        export XDG_RUNTIME_DIR="/run/user/$(id -u)"
    fi

    if pulse_server="$(pick_wslg_pulse_server)"; then
        if [[ "${PULSE_SERVER:-}" != "$pulse_server" ]]; then
            export PULSE_SERVER="$pulse_server"
            echo "[audio-env] Using WSLg PulseAudio at $PULSE_SERVER"
        fi
    fi
fi

setup_python_cuda_runtime
