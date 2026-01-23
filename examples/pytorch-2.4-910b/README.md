# PyTorch 2.4 on Atlas 910B Example

This example demonstrates how to run PyTorch 2.4 with torch_npu on Huawei Atlas 910B NPU.

## Environment

| Component | Version |
|-----------|---------|
| CANN | 8.0.0 |
| PyTorch | 2.4.0 |
| torch_npu | 2.4.0.post2 |
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
docker build -t pytorch-910b:2.4 .

# 2. Run container with NPU access
./run.sh

# 3. Inside container, verify NPU
python test_npu.py
```

## Files

| File | Description |
|------|-------------|
| `Dockerfile` | Multi-stage build for PyTorch + CANN |
| `docker-compose.yml` | Compose file with NPU device mapping |
| `run.sh` | Quick start script |
| `test_npu.py` | NPU verification script |

## NPU Device Mapping

The container requires access to:
- `/dev/davinci*` - NPU compute devices
- `/dev/davinci_manager` - Device manager
- `/dev/devmm_svm` - Shared virtual memory
- `/dev/hisi_hdc` - HDC communication

## Troubleshooting

### "No NPU device found"
- Verify driver is installed: `npu-smi info`
- Check device permissions: `ls -la /dev/davinci*`

### "CANN initialization failed"
- Ensure ASCEND_HOME is set correctly
- Verify CANN version matches driver version

## References

- [CANN 8.0.0 Documentation](https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/800/overview/index.html)
- [torch_npu GitHub](https://gitee.com/ascend/pytorch)
