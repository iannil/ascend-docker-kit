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

# Parse NPU information
# Format: "| 0    910B   OK      75W   |"
NPU_LIST=""
NPU_COUNT=0

while IFS= read -r line; do
    # Match lines with NPU info pattern: | <id> <type> <health> <power> |
    if echo "$line" | grep -qP '^\|\s+\d+\s+\d{3}[A-Z0-9]*\s+'; then
        NPU_ID=$(echo "$line" | grep -oP '^\|\s+\K\d+')
        NPU_TYPE=$(echo "$line" | grep -oP '^\|\s+\d+\s+\K\d{3}[A-Z0-9]*')

        if [ -n "$NPU_ID" ] && [ -n "$NPU_TYPE" ]; then
            if [ $NPU_COUNT -gt 0 ]; then
                NPU_LIST="$NPU_LIST,"
            fi
            NPU_LIST="$NPU_LIST{\"id\": $NPU_ID, \"type\": \"$NPU_TYPE\"}"
            NPU_COUNT=$((NPU_COUNT + 1))
        fi
    fi
done <<< "$NPU_INFO"

# Check if any NPUs were found
if [ $NPU_COUNT -eq 0 ]; then
    output_error "No NPU devices detected" "Check if NPU hardware is properly installed"
    exit 1
fi

# Try to get firmware version from npu-smi info -t board
FIRMWARE_VERSION=""
BOARD_INFO=$(npu-smi info -t board 2>/dev/null)
if [ $? -eq 0 ]; then
    # Try to extract firmware version
    FIRMWARE_VERSION=$(echo "$BOARD_INFO" | grep -iP 'firmware|version' | grep -oP '[\d.]+' | head -1)
fi

# Build the NPU list with firmware if available
NPU_DETAILED_LIST=""
NPU_COUNT=0

while IFS= read -r line; do
    if echo "$line" | grep -qP '^\|\s+\d+\s+\d{3}[A-Z0-9]*\s+'; then
        NPU_ID=$(echo "$line" | grep -oP '^\|\s+\K\d+')
        NPU_TYPE=$(echo "$line" | grep -oP '^\|\s+\d+\s+\K\d{3}[A-Z0-9]*')

        if [ -n "$NPU_ID" ] && [ -n "$NPU_TYPE" ]; then
            if [ $NPU_COUNT -gt 0 ]; then
                NPU_DETAILED_LIST="$NPU_DETAILED_LIST,"
            fi

            if [ -n "$FIRMWARE_VERSION" ]; then
                NPU_DETAILED_LIST="$NPU_DETAILED_LIST{\"id\": $NPU_ID, \"type\": \"$NPU_TYPE\", \"firmware\": \"$FIRMWARE_VERSION\"}"
            else
                NPU_DETAILED_LIST="$NPU_DETAILED_LIST{\"id\": $NPU_ID, \"type\": \"$NPU_TYPE\"}"
            fi
            NPU_COUNT=$((NPU_COUNT + 1))
        fi
    fi
done <<< "$NPU_INFO"

# Output success result
echo "{"
echo "  \"status\": \"ok\","
echo "  \"driver_version\": \"$DRIVER_VERSION\","
echo "  \"npu_count\": $NPU_COUNT,"
echo "  \"npus\": [$NPU_DETAILED_LIST]"
echo "}"
