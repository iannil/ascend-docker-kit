# MindSpore 2.3 on Atlas 910B Example

This example demonstrates how to run MindSpore 2.3 on Huawei Atlas 910B NPU.

## Environment

| Component | Version |
|-----------|---------|
| CANN | 8.0.0 |
| MindSpore | 2.3.0 |
| Python | 3.10 |
| OS | Ubuntu 22.04 |

## Prerequisites

1. Huawei Atlas 910B NPU hardware
2. NPU driver version >= 24.1.rc1
3. Docker installed
4. CANN toolkit package downloaded to `packages/` directory

## Quick Start

```bash
# 1. Build the image
docker build -t mindspore-910b:2.3 .

# 2. Run container with NPU access
./run.sh

# 3. Inside container, verify NPU
python test_npu.py
```

## Files

| File | Description |
|------|-------------|
| `Dockerfile` | Multi-stage build for MindSpore + CANN |
| `docker-compose.yml` | Compose file with NPU device mapping |
| `run.sh` | Quick start script |
| `test_npu.py` | NPU verification script |

## MindSpore Features

- Native Ascend NPU support
- Graph mode for optimal performance
- PyNative mode for debugging
- Automatic mixed precision training

## Troubleshooting

### "No Ascend device found"
- Verify driver: `npu-smi info`
- Check CANN environment: `echo $ASCEND_HOME`

### "Operator compilation failed"
- Ensure CANN kernels are installed
- Check NPU model matches kernel package (910b)

## References

- [MindSpore Official](https://www.mindspore.cn/)
- [CANN 8.0.0 Documentation](https://www.hiascend.com/document)
