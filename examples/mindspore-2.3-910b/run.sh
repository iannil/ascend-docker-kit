#!/bin/bash
# run.sh - Quick start script for MindSpore 910B container
# Usage: ./run.sh [device_id]

set -e

IMAGE_NAME="mindspore-910b:2.3"
CONTAINER_NAME="mindspore-910b"
DEVICE_ID=${1:-0}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if NPU devices exist
if [ ! -e "/dev/davinci${DEVICE_ID}" ]; then
    log_error "NPU device /dev/davinci${DEVICE_ID} not found"
    log_warn "Please ensure NPU driver is installed and devices are available"
    exit 1
fi

# Build image if not exists
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    log_info "Building Docker image..."
    docker build -t "$IMAGE_NAME" .
fi

log_info "Starting container with NPU device ${DEVICE_ID}..."

# Run container
docker run -it --rm \
    --name "$CONTAINER_NAME" \
    --device="/dev/davinci${DEVICE_ID}" \
    --device=/dev/davinci_manager \
    --device=/dev/devmm_svm \
    --device=/dev/hisi_hdc \
    --shm-size=16g \
    -v "$(pwd)/workspace:/workspace" \
    -v "/usr/local/Ascend/driver:/usr/local/Ascend/driver:ro" \
    -e "DEVICE_ID=${DEVICE_ID}" \
    -e "GLOG_v=2" \
    "$IMAGE_NAME" \
    /bin/bash
