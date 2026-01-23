#!/bin/bash
# run.sh - Quick start script for PyTorch 910B container
# Usage: ./run.sh [num_npus]

set -e

IMAGE_NAME="pytorch-910b:2.4"
CONTAINER_NAME="pytorch-910b"
NUM_NPUS=${1:-1}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if NPU devices exist
if [ ! -e /dev/davinci0 ]; then
    log_error "NPU device /dev/davinci0 not found"
    log_warn "Please ensure NPU driver is installed and devices are available"
    exit 1
fi

# Build image if not exists
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    log_info "Building Docker image..."
    docker build -t "$IMAGE_NAME" .
fi

# Generate device list
DEVICES=""
for i in $(seq 0 $((NUM_NPUS - 1))); do
    if [ -e "/dev/davinci$i" ]; then
        DEVICES="$DEVICES --device=/dev/davinci$i"
    else
        log_warn "Device /dev/davinci$i not found, skipping"
    fi
done

# Add required system devices
DEVICES="$DEVICES --device=/dev/davinci_manager"
DEVICES="$DEVICES --device=/dev/devmm_svm"
DEVICES="$DEVICES --device=/dev/hisi_hdc"

log_info "Starting container with $NUM_NPUS NPU(s)..."

# Run container
docker run -it --rm \
    --name "$CONTAINER_NAME" \
    $DEVICES \
    --shm-size=16g \
    -v "$(pwd)/workspace:/workspace" \
    -v "/usr/local/Ascend/driver:/usr/local/Ascend/driver:ro" \
    -e "ASCEND_VISIBLE_DEVICES=$(seq -s, 0 $((NUM_NPUS - 1)))" \
    "$IMAGE_NAME" \
    /bin/bash
