#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-}"

declare -A TARGET_REPOS=(
    # FuzzAgent
    [cjson]=https://github.com/DaveGamble/cJSON.git
    [libmagic]=https://github.com/file/file.git
    [re2]=https://github.com/google/re2.git
    [pugixml]=https://github.com/zeux/pugixml.git
    [zlib]=https://github.com/madler/zlib.git
    [c-ares]=https://github.com/c-ares/c-ares.git
    [liblouis]=https://github.com/liblouis/liblouis.git
    [libpng]=https://github.com/pnggroup/libpng.git
    [libpcap]=https://github.com/the-tcpdump-group/libpcap.git
    [libtiff]=https://github.com/libsdl-org/libtiff.git
    [lcms]=https://github.com/mm2/Little-CMS.git
    [tinygltf]=https://github.com/syoyo/tinygltf.git
    [libjpeg-turbo]=https://github.com/libjpeg-turbo/libjpeg-turbo.git
    [curl]=https://github.com/curl/curl.git
    [libvpx]=https://chromium.googlesource.com/webm/libvpx
    [sqlite]=https://github.com/sqlite/sqlite.git
    [libaom]=https://aomedia.googlesource.com/aom
    [openssl]=https://github.com/openssl/openssl.git
    [protobuf]=https://github.com/protocolbuffers/protobuf.git
    [opencv]=https://github.com/opencv/opencv.git

    # Agentic fuzzing
    [simdjson]=https://github.com/simdjson/simdjson.git
    [bzip3]=https://github.com/kspalaiologos/bzip3.git
    [mpack]=https://github.com/ludocode/mpack.git
    [libucl]=https://github.com/vstakhov/libucl.git
    [libmobi]=https://github.com/bfabiszewski/libmobi.git
    [libxls]=https://github.com/libxls/libxls.git
    [djvulibre]=https://git.code.sf.net/p/djvu/djvulibre-git
)

if [[ -t 1 && -z "${NO_COLOR+x}" && "${TERM:-}" != "dumb" ]]; then
    BLUE=$'\033[38;5;117m'
    RED=$'\033[38;5;210m'
    RESET=$'\033[0m'
else
    BLUE=''
    RED=''
    RESET=''
fi

color_path() {
    printf '%s%s%s' "$BLUE" "$1" "$RESET"
}

color_command() {
    printf '%s%s%s' "$RED" "$1" "$RESET"
}

print_usage() {
    printf 'Usage: %s <target>\n       %s --help\n\n' "$(color_command "$0")" "$(color_command "$0")"
    cat <<'EOF'

Start one of the 20 paper benchmark targets in a detached Docker container.
The default fuzzing duration is 24h; override it with FUZZING_DURATION, e.g.:
EOF
    printf '  %s\n\nAvailable targets:\n' "$(color_command "FUZZING_DURATION=10m $0 cjson")"
    printf '  %s\n' "${!TARGET_REPOS[@]}" | sort
}

if [[ "$TARGET" == "--help" || "$TARGET" == "-h" ]]; then
    print_usage
    exit 0
fi

if [[ -z "$TARGET" || -z "${TARGET_REPOS[$TARGET]:-}" || "$#" -ne 1 ]]; then
    print_usage >&2
    exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
    printf 'Docker was not found. Install docker engine and docker compose, then retry.\n' >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    printf 'Docker is not available. Start docker and make sure your user can access it, then retry.\n' >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    printf 'Docker compose v2 is required. Install the docker compose plugin, then retry.\n' >&2
    exit 1
fi
if ! docker image inspect agentic-fuzzing >/dev/null 2>&1; then
    printf 'The local agentic-fuzzing image was not found. Build it first with:\n  %sdocker buildx build -t agentic-fuzzing -f %s%s %s\n' \
        "$RED" "$(color_path "$ROOT_DIR/docker/Dockerfile")" "$RED" "$(color_path "$ROOT_DIR")" >&2
    exit 1
fi

ENV_FILE="$ROOT_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    printf 'Missing %s. Create it from %s and configure the LLM endpoint:\n' \
        "$(color_path "$ENV_FILE")" "$(color_path "$ROOT_DIR/.env.example")" >&2
    printf '  %scp %s%s %s\n' "$RED" "$(color_path "$ROOT_DIR/.env.example")" "$RED" "$(color_path "$ENV_FILE")" >&2
    exit 1
fi

set -a
source "$ENV_FILE"
set +a
missing_config=()
for name in OPENAI_BASE_URL OPENAI_API_KEY OPENAI_MODEL; do
    if [[ -z "${!name:-}" ]]; then
        missing_config+=("$name")
    fi
done
if (( ${#missing_config[@]} > 0 )); then
    printf 'Configure the following required values in %s: %s\n' "$(color_path "$ENV_FILE")" "${missing_config[*]}" >&2
    exit 1
fi

TARGET_DIR="$ROOT_DIR/.cache/targets/$TARGET"
mkdir -p "$(dirname "$TARGET_DIR")" "$ROOT_DIR/output"
if [[ -d "$TARGET_DIR/.git" ]]; then
    if ! git -C "$TARGET_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        printf 'The cached checkout for %s is incomplete: %s\nRemove that directory and rerun this command.\n' \
            "$TARGET" "$(color_path "$TARGET_DIR")" >&2
        exit 1
    fi
    printf 'Using cached source checkout: %s\n' "$(color_path "$TARGET_DIR")"
else
    if [[ -e "$TARGET_DIR" ]]; then
        printf 'Target path exists but is not a Git checkout: %s\nRemove or rename it, then retry.\n' \
            "$(color_path "$TARGET_DIR")" >&2
        exit 1
    fi
    printf 'Cloning %s source into the local cache, this may take a while...\n' "$TARGET"
    CLONE_TMP_DIR="$(mktemp -d "${TARGET_DIR}.clone.XXXXXX")"
    cleanup_clone() {
        if [[ -n "${CLONE_TMP_DIR:-}" && -d "$CLONE_TMP_DIR" ]]; then
            rm -rf -- "$CLONE_TMP_DIR"
        fi
    }
    trap cleanup_clone EXIT
    if ! git clone --depth 1 --recurse-submodules --shallow-submodules --progress "${TARGET_REPOS[$TARGET]}" "$CLONE_TMP_DIR"; then
        printf 'Could not clone %s. Check network access and retry; incomplete clone data will be cleaned up.\n' "$TARGET" >&2
        exit 1
    fi
    mv "$CLONE_TMP_DIR" "$TARGET_DIR"
    CLONE_TMP_DIR=""
    trap - EXIT
    printf 'Source checkout ready: %s\n' "$(color_path "$TARGET_DIR")"
fi

export CONTAINER_NAME="agentic-fuzzing-$TARGET"
export FUZZING_DURATION="${FUZZING_DURATION:-24h}"

# The container runs main.py for this duration, then exports full code coverage.
export COMMAND='bash /root/agentic-fuzzing/benchmark/run-benchmark.sh'
export WRITE_MODE=rw
export FUZZING_ENGINE=afl++
export AGENTIC_FUZZING_AUTO_CLEAN="${AGENTIC_FUZZING_AUTO_CLEAN:-1}"
export AGENTIC_FUZZING_DIR="$ROOT_DIR"
export SRC_DIR="$TARGET_DIR"
export REPO_BASE_NAME="$TARGET"
export RAW_OUTPUT_DIR="$ROOT_DIR/output/$TARGET"

printf '\nStarting agentic fuzzing benchmark\n'
printf '  Target:   %s\n' "$TARGET"
printf '  Duration: %s\n' "$FUZZING_DURATION"
printf '  Source:   %s\n' "$(color_path "$TARGET_DIR")"
printf '  Results:  %s\n' "$(color_path "$RAW_OUTPUT_DIR")"
printf '  Container: %s\n\n' "$CONTAINER_NAME"

if ! docker compose -p "$CONTAINER_NAME" -f "$ROOT_DIR/docker/docker-compose.yml" up -d; then
    printf '\nCould not start the benchmark container. Check the docker output above.\n' >&2
    exit 1
fi

CONTAINER_STATUS="$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"
if [[ "$CONTAINER_STATUS" != "running" ]]; then
    printf '\nThe container did not stay running (status: %s). Recent logs:\n' "${CONTAINER_STATUS:-unknown}" >&2
    docker logs --tail 40 "$CONTAINER_NAME" 2>&1 || true
    printf 'For more details, run: %s\n' "$(color_command "docker logs $CONTAINER_NAME")" >&2
    exit 1
fi

cat <<EOF

Agentic fuzzing is running in the background. This command can now be closed safely.

Execution logs are continuously saved to: $(color_path "$RAW_OUTPUT_DIR/.cache/logs")

Stop the benchmark early:
  $(color_command "docker rm -f $CONTAINER_NAME")

The full coverage export runs after the fuzzing duration ends.
EOF