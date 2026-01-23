#!/usr/bin/env python3
"""
test_npu.py - NPU verification script for MindSpore

This script verifies that the NPU is properly configured and accessible.
Run this after starting the container to confirm the environment is working.
"""

import sys


def check_mindspore():
    """Check MindSpore installation."""
    print("=" * 60)
    print("Checking MindSpore installation...")
    print("=" * 60)

    try:
        import mindspore as ms

        print(f"MindSpore version: {ms.__version__}")
        return True
    except ImportError as e:
        print(f"ERROR: MindSpore not installed: {e}")
        return False


def check_ascend_device():
    """Check Ascend device availability."""
    print("\n" + "=" * 60)
    print("Checking Ascend device...")
    print("=" * 60)

    try:
        import mindspore as ms
        from mindspore import context

        # Set device target to Ascend
        context.set_context(device_target="Ascend")
        target = context.get_context("device_target")
        print(f"Device target: {target}")

        if target == "Ascend":
            device_id = context.get_context("device_id")
            print(f"Device ID: {device_id}")
            print("Ascend device: Available")
            return True
        else:
            print("WARNING: Ascend device not available, using CPU")
            return False

    except Exception as e:
        print(f"ERROR: Failed to check Ascend device: {e}")
        return False


def check_tensor_operations():
    """Test basic tensor operations on Ascend."""
    print("\n" + "=" * 60)
    print("Testing tensor operations on Ascend...")
    print("=" * 60)

    try:
        import mindspore as ms
        from mindspore import Tensor, ops
        import numpy as np

        # Create tensors
        x = Tensor(np.random.randn(1000, 1000).astype(np.float32))
        y = Tensor(np.random.randn(1000, 1000).astype(np.float32))

        # Matrix multiplication
        matmul = ops.MatMul()
        z = matmul(x, y)

        print(f"Created tensor: shape={x.shape}, dtype={x.dtype}")
        print(f"Matrix multiplication result: shape={z.shape}")
        print(f"Result sum: {z.sum().asnumpy():.4f}")

        print("\nTensor operations: PASSED")
        return True

    except Exception as e:
        print(f"ERROR: Tensor operations failed: {e}")
        return False


def check_simple_model():
    """Test a simple neural network on Ascend."""
    print("\n" + "=" * 60)
    print("Testing simple model training on Ascend...")
    print("=" * 60)

    try:
        import mindspore as ms
        from mindspore import nn, Tensor
        from mindspore.train import Model
        import numpy as np

        # Simple model
        class SimpleNet(nn.Cell):
            def __init__(self):
                super(SimpleNet, self).__init__()
                self.fc1 = nn.Dense(784, 256)
                self.relu = nn.ReLU()
                self.fc2 = nn.Dense(256, 10)

            def construct(self, x):
                x = self.fc1(x)
                x = self.relu(x)
                x = self.fc2(x)
                return x

        net = SimpleNet()

        # Dummy data
        x = Tensor(np.random.randn(32, 784).astype(np.float32))
        y = Tensor(np.random.randint(0, 10, (32,)).astype(np.int32))

        # Loss and optimizer
        loss_fn = nn.SoftmaxCrossEntropyWithLogits(sparse=True, reduction="mean")
        optimizer = nn.Adam(net.trainable_params(), learning_rate=0.001)

        # Training step
        def forward_fn(data, label):
            logits = net(data)
            loss = loss_fn(logits, label)
            return loss

        grad_fn = ms.value_and_grad(forward_fn, None, optimizer.parameters)

        for step in range(5):
            loss, grads = grad_fn(x, y)
            optimizer(grads)
            print(f"Step {step + 1}: loss = {loss.asnumpy():.4f}")

        print("\nSimple model training: PASSED")
        return True

    except Exception as e:
        print(f"ERROR: Model training failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_graph_mode():
    """Test MindSpore graph mode."""
    print("\n" + "=" * 60)
    print("Testing MindSpore graph mode...")
    print("=" * 60)

    try:
        import mindspore as ms
        from mindspore import context, Tensor, ops
        import numpy as np

        # Set graph mode
        context.set_context(mode=context.GRAPH_MODE)
        mode = context.get_context("mode")
        print(f"Execution mode: {'GRAPH_MODE' if mode == 0 else 'PYNATIVE_MODE'}")

        # Simple computation in graph mode
        @ms.jit
        def compute(x, y):
            return ops.MatMul()(x, y)

        x = Tensor(np.random.randn(100, 100).astype(np.float32))
        y = Tensor(np.random.randn(100, 100).astype(np.float32))
        z = compute(x, y)

        print(f"Graph mode computation result: shape={z.shape}")
        print("\nGraph mode: PASSED")
        return True

    except Exception as e:
        print(f"ERROR: Graph mode test failed: {e}")
        return False
    finally:
        # Reset to PyNative mode
        from mindspore import context

        context.set_context(mode=context.PYNATIVE_MODE)


def main():
    """Run all checks."""
    print("\n" + "#" * 60)
    print("# MindSpore Ascend NPU Environment Verification")
    print("#" * 60)

    results = {
        "MindSpore": check_mindspore(),
        "Ascend Device": check_ascend_device(),
        "Tensor Operations": check_tensor_operations(),
        "Model Training": check_simple_model(),
        "Graph Mode": check_graph_mode(),
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
        print("All checks PASSED! MindSpore Ascend environment is ready.")
        return 0
    else:
        print("Some checks FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
