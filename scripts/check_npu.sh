#!/bin/bash
# check_npu.sh - NPU status detection script for Ascend devices
# Outputs JSON format result for programmatic consumption

set -o pipefail

# Output error in JSON format
output_error() {
    local error_msg="$1"
    local suggestion="$2"
    echo "{"
    echo "  \"status\": \"error\","
    echo "  \"error\": \"$error_msg\","
    echo "  \"suggestion\": \"$suggestion\""
    echo "}"
}

# Parse NPU entries from npu-smi output
# Args: $1 - npu-smi output, $2 - firmware version (optional)
# Output: JSON array of NPU objects, and sets NPU_COUNT
parse_npu_entries() {
    local npu_info="$1"
    local firmware_version="$2"
    local npu_list=""
    NPU_COUNT=0

    while IFS= read -r line; do
        # Match lines with NPU info pattern: | <id> <type> <health> <power> |
        if echo "$line" | grep -qP '^\|\s+\d+\s+\d{3}[A-Z0-9]{0,10}\s+'; then
            local npu_id=$(echo "$line" | grep -oP '^\|\s+\K\d+')
            local npu_type=$(echo "$line" | grep -oP '^\|\s+\d+\s+\K\d{3}[A-Z0-9]{0,10}')

            if [ -n "$npu_id" ] && [ -n "$npu_type" ]; then
                if [ $NPU_COUNT -gt 0 ]; then
                    npu_list="$npu_list,"
                fi

                if [ -n "$firmware_version" ]; then
                    npu_list="$npu_list{\"id\": $npu_id, \"type\": \"$npu_type\", \"firmware\": \"$firmware_version\"}"
                else
                    npu_list="$npu_list{\"id\": $npu_id, \"type\": \"$npu_type\"}"
                fi
                NPU_COUNT=$((NPU_COUNT + 1))
            fi
        fi
    done <<< "$npu_info"

    echo "$npu_list"
}

# Check if npu-smi exists
if ! command -v npu-smi &> /dev/null; then
    output_error "npu-smi not found" "Please install Ascend NPU driver"
    exit 1
fi

# Get npu-smi info output
NPU_INFO=$(npu-smi info 2>&1)
if [ $? -ne 0 ]; then
    output_error "npu-smi command failed" "Check if NPU driver is properly installed"
    exit 1
fi

# Extract driver version from npu-smi output
# Format: "| npu-smi 24.1.rc1          |"
DRIVER_VERSION=$(echo "$NPU_INFO" | grep -oP 'npu-smi\s+\K[\d.]+[a-zA-Z0-9.]*' | head -1)
if [ -z "$DRIVER_VERSION" ]; then
    output_error "Cannot parse driver version" "Unexpected npu-smi output format"
    exit 1
fi

# Try to get firmware version from npu-smi info -t board
FIRMWARE_VERSION=""
BOARD_INFO=$(npu-smi info -t board 2>/dev/null)
if [ $? -eq 0 ]; then
    # Try to extract firmware version
    FIRMWARE_VERSION=$(echo "$BOARD_INFO" | grep -iP 'firmware|version' | grep -oP '[\d.]+' | head -1)
fi

# Parse NPU entries (single call, no duplication)
NPU_LIST=$(parse_npu_entries "$NPU_INFO" "$FIRMWARE_VERSION")

# Check if any NPUs were found
if [ $NPU_COUNT -eq 0 ]; then
    output_error "No NPU devices detected" "Check if NPU hardware is properly installed"
    exit 1
fi

# Output success result
echo "{"
echo "  \"status\": \"ok\","
echo "  \"driver_version\": \"$DRIVER_VERSION\","
echo "  \"npu_count\": $NPU_COUNT,"
echo "  \"npus\": [$NPU_LIST]"
echo "}"
