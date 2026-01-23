#!/usr/bin/env python3
"""
test_npu.py - NPU verification script for PyTorch + torch_npu

This script verifies that the NPU is properly configured and accessible.
Run this after starting the container to confirm the environment is working.
"""

import sys


def check_torch():
    """Check PyTorch installation."""
    print("=" * 60)
    print("Checking PyTorch installation...")
    print("=" * 60)

    try:
        import torch

        print(f"PyTorch version: {torch.__version__}")
        print(f"PyTorch built with CUDA: {torch.cuda.is_available()}")
        return True
    except ImportError as e:
        print(f"ERROR: PyTorch not installed: {e}")
        return False


def check_torch_npu():
    """Check torch_npu installation and NPU availability."""
    print("\n" + "=" * 60)
    print("Checking torch_npu installation...")
    print("=" * 60)

    try:
        import torch_npu

        print(f"torch_npu version: {torch_npu.__version__}")
        print(f"NPU available: {torch_npu.npu.is_available()}")

        if torch_npu.npu.is_available():
            npu_count = torch_npu.npu.device_count()
            print(f"NPU count: {npu_count}")

            for i in range(npu_count):
                props = torch_npu.npu.get_device_properties(i)
                print(f"\nNPU {i}:")
                print(f"  Name: {props.name}")
                print(f"  Total memory: {props.total_memory / 1024**3:.2f} GB")

            return True
        else:
            print("WARNING: NPU not available")
            return False

    except ImportError as e:
        print(f"ERROR: torch_npu not installed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to check NPU: {e}")
        return False


def check_tensor_operations():
    """Test basic tensor operations on NPU."""
    print("\n" + "=" * 60)
    print("Testing tensor operations on NPU...")
    print("=" * 60)

    try:
        import torch
        import torch_npu

        if not torch_npu.npu.is_available():
            print("SKIP: NPU not available")
            return False

        # Create tensors on NPU
        device = torch.device("npu:0")
        x = torch.randn(1000, 1000, device=device)
        y = torch.randn(1000, 1000, device=device)

        # Matrix multiplication
        z = torch.matmul(x, y)
        torch_npu.npu.synchronize()

        print(f"Created tensor on NPU: shape={x.shape}, dtype={x.dtype}")
        print(f"Matrix multiplication result: shape={z.shape}")
        print(f"Result sum: {z.sum().item():.4f}")

        # Memory info
        allocated = torch_npu.npu.memory_allocated(0) / 1024**2
        reserved = torch_npu.npu.memory_reserved(0) / 1024**2
        print(f"\nMemory allocated: {allocated:.2f} MB")
        print(f"Memory reserved: {reserved:.2f} MB")

        print("\nTensor operations: PASSED")
        return True

    except Exception as e:
        print(f"ERROR: Tensor operations failed: {e}")
        return False


def check_simple_model():
    """Test a simple neural network on NPU."""
    print("\n" + "=" * 60)
    print("Testing simple model training on NPU...")
    print("=" * 60)

    try:
        import torch
        import torch.nn as nn
        import torch_npu

        if not torch_npu.npu.is_available():
            print("SKIP: NPU not available")
            return False

        device = torch.device("npu:0")

        # Simple model
        model = nn.Sequential(
            nn.Linear(784, 256),
            nn.ReLU(),
            nn.Linear(256, 10),
        ).to(device)

        # Dummy data
        x = torch.randn(32, 784, device=device)
        y = torch.randint(0, 10, (32,), device=device)

        # Forward pass
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

        for step in range(5):
            optimizer.zero_grad()
            output = model(x)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()
            print(f"Step {step + 1}: loss = {loss.item():.4f}")

        torch_npu.npu.synchronize()
        print("\nSimple model training: PASSED")
        return True

    except Exception as e:
        print(f"ERROR: Model training failed: {e}")
        return False


def main():
    """Run all checks."""
    print("\n" + "#" * 60)
    print("# Ascend NPU Environment Verification")
    print("#" * 60)

    results = {
        "PyTorch": check_torch(),
        "torch_npu": check_torch_npu(),
        "Tensor Operations": check_tensor_operations(),
        "Model Training": check_simple_model(),
    }

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All checks PASSED! NPU environment is ready.")
        return 0
    else:
        print("Some checks FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
