"""
ADK Dockerfile Generator

Generates Dockerfiles for Ascend NPU environments using Jinja2 templates.
Supports multi-stage builds for both training and inference workloads.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from .exceptions import ADKError, ConfigurationError, FrameworkNotFoundError
from .matrix import CompatibilityResolver
from .models import EnvironmentInfo, FrameworkConfig, FrameworkType


class BuildTarget(str, Enum):
    """Docker image build target type."""

    TRAIN = "train"
    INFERENCE = "inference"


class DockerfileGeneratorError(ADKError):
    """Raised when Dockerfile generation fails."""

    pass


@dataclass
class BuildContext:
    """
    Build context for Dockerfile generation.

    Contains all information needed to render Dockerfile templates.
    """

    # Required fields
    cann_version: str
    framework: FrameworkType
    target: BuildTarget

    # Environment info (auto-detected or provided)
    os_name: str = "ubuntu22.04"
    arch: str = "x86_64"
    npu_type: str = "910B"

    # Python configuration
    python_version: str = "3.10"

    # Framework versions (auto-resolved from matrix)
    framework_version: Optional[str] = None
    torch_npu_version: Optional[str] = None
    torch_npu_whl_url: Optional[str] = None

    # CANN package filenames (user must provide)
    cann_toolkit_filename: Optional[str] = None
    cann_kernels_filename: Optional[str] = None

    # Base image
    base_image: str = "ubuntu:22.04"

    # Optional configurations
    use_china_mirror: bool = True
    adk_version: str = "0.2.0"

    # Additional template variables
    extra_vars: Dict[str, Any] = field(default_factory=dict)

    def to_template_vars(self) -> Dict[str, Any]:
        """
        Convert build context to template variables dict.

        Returns:
            Dictionary of all template variables
        """
        vars_dict = {
            "cann_version": self.cann_version,
            "framework": self.framework.value,
            "target": self.target.value,
            "os_name": self.os_name,
            "arch": self.arch,
            "npu_type": self.npu_type,
            "python_version": self.python_version,
            "framework_version": self.framework_version,
            "pytorch_version": self.framework_version,  # Alias for PyTorch template
            "torch_npu_version": self.torch_npu_version,
            "torch_npu_whl_url": self.torch_npu_whl_url,
            "cann_toolkit_filename": self.cann_toolkit_filename,
            "cann_kernels_filename": self.cann_kernels_filename,
            "base_image": self.base_image,
            "use_china_mirror": self.use_china_mirror,
            "adk_version": self.adk_version,
        }
        vars_dict.update(self.extra_vars)
        return vars_dict


@dataclass
class GeneratorOutput:
    """
    Output of Dockerfile generation.

    Contains the generated Dockerfile content and related files.
    """

    dockerfile_content: str
    build_script_content: str
    run_script_content: str
    context: BuildContext

    # List of required files (user must provide)
    required_files: List[str] = field(default_factory=list)

    # Warnings or notes for the user
    notes: List[str] = field(default_factory=list)


class DockerfileGenerator:
    """
    Generator for Ascend NPU Docker images.

    Uses Jinja2 templates to render multi-stage Dockerfiles with
    CANN toolkit and deep learning framework installations.

    Example:
        >>> resolver = CompatibilityResolver.from_yaml("data/compatibility.yaml")
        >>> generator = DockerfileGenerator(resolver)
        >>> context = generator.create_context(
        ...     cann_version="8.0.0",
        ...     framework="pytorch",
        ...     target="train"
        ... )
        >>> output = generator.generate(context)
        >>> generator.write_output(output, "./build")
    """

    DEFAULT_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

    def __init__(
        self,
        resolver: CompatibilityResolver,
        template_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        """
        Initialize the Dockerfile generator.

        Args:
            resolver: Compatibility resolver for version lookups
            template_dir: Path to Jinja2 template directory (optional)

        Raises:
            ConfigurationError: If template directory does not exist
        """
        self._resolver = resolver
        self._template_dir = (
            Path(template_dir) if template_dir else self.DEFAULT_TEMPLATE_DIR
        )
        self._jinja_env = self._setup_jinja_environment()

    def _setup_jinja_environment(self) -> Environment:
        """
        Configure Jinja2 environment with custom settings.

        Returns:
            Configured Jinja2 Environment instance

        Raises:
            ConfigurationError: If template directory does not exist
        """
        if not self._template_dir.exists():
            raise ConfigurationError(
                f"Template directory not found: {self._template_dir}",
                suggestions=[
                    "Ensure templates/ directory exists in ADK installation",
                    "Check ADK installation integrity",
                    f"Expected path: {self._template_dir}",
                ],
            )

        env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Add custom filters
        env.filters["arch_to_whl"] = self._arch_to_whl_format

        return env

    @staticmethod
    def _arch_to_whl_format(arch: str) -> str:
        """
        Convert architecture string to wheel filename format.

        Args:
            arch: Architecture string (e.g., "x86_64", "aarch64")

        Returns:
            Wheel-compatible architecture string
        """
        mapping = {
            "x86_64": "x86_64",
            "aarch64": "aarch64",
        }
        return mapping.get(arch, arch)

    def create_context(
        self,
        cann_version: str,
        framework: Union[str, FrameworkType],
        target: Union[str, BuildTarget] = BuildTarget.TRAIN,
        env_info: Optional[EnvironmentInfo] = None,
        python_version: Optional[str] = None,
        **kwargs: Any,
    ) -> BuildContext:
        """
        Create a build context with auto-resolved versions.

        Args:
            cann_version: Target CANN version (e.g., "8.0.0")
            framework: Framework type ("pytorch" or "mindspore")
            target: Build target ("train" or "inference")
            env_info: Environment info for auto-detection (optional)
            python_version: Python version override (optional)
            **kwargs: Additional context variables

        Returns:
            BuildContext with resolved framework versions

        Raises:
            VersionNotFoundError: If CANN version not found
            FrameworkNotFoundError: If framework not available for CANN version
            ConfigurationError: If Python version not supported
        """
        # Normalize enums
        if isinstance(framework, str):
            framework = FrameworkType(framework.lower())
        if isinstance(target, str):
            target = BuildTarget(target.lower())

        # Get framework config from matrix
        framework_config = self._resolver.get_framework(cann_version, framework.value)

        # Determine Python version
        if python_version is None:
            # Use latest supported Python version
            python_version = framework_config.python_versions[-1]
        elif python_version not in framework_config.python_versions:
            raise ConfigurationError(
                f"Python {python_version} not supported for {framework.value} "
                f"with CANN {cann_version}",
                suggestions=[
                    f"Supported Python versions: {', '.join(framework_config.python_versions)}",
                    "Use --python option to specify a supported version",
                ],
            )

        # Resolve whl URL with placeholders
        whl_url = None
        if framework_config.whl_url:
            py_version_short = python_version.replace(".", "")
            arch = kwargs.get("arch", env_info.arch if env_info else "x86_64")
            whl_url = framework_config.whl_url.replace(
                "{py_version}", py_version_short
            ).replace("{arch}", arch)

        # Build initial context
        context = BuildContext(
            cann_version=cann_version,
            framework=framework,
            target=target,
            python_version=python_version,
            framework_version=framework_config.version,
            torch_npu_version=framework_config.torch_npu_version,
            torch_npu_whl_url=whl_url,
        )

        # Apply environment info if provided
        if env_info:
            context.os_name = env_info.os_name
            context.arch = env_info.arch
            context.npu_type = env_info.npu_type

        # Apply any additional kwargs
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.extra_vars[key] = value

        # Set default CANN package filenames
        if context.cann_toolkit_filename is None:
            context.cann_toolkit_filename = self._default_toolkit_filename(
                cann_version, context.arch
            )

        if context.cann_kernels_filename is None:
            context.cann_kernels_filename = self._default_kernels_filename(
                cann_version, context.npu_type
            )

        # Set base image based on OS
        context.base_image = self._resolve_base_image(context.os_name)

        return context

    def _default_toolkit_filename(self, version: str, arch: str) -> str:
        """
        Generate default CANN toolkit filename.

        Args:
            version: CANN version
            arch: Architecture

        Returns:
            Default toolkit filename
        """
        return f"Ascend-cann-toolkit_{version}_linux-{arch}.run"

    def _default_kernels_filename(self, version: str, npu_type: str) -> str:
        """
        Generate default CANN kernels filename.

        Args:
            version: CANN version
            npu_type: NPU type

        Returns:
            Default kernels filename
        """
        npu_lower = npu_type.lower()
        return f"Ascend-cann-kernels-{npu_lower}_{version}_linux.run"

    def _resolve_base_image(self, os_name: str) -> str:
        """
        Resolve base Docker image from OS name.

        Args:
            os_name: OS name (e.g., "ubuntu22.04")

        Returns:
            Docker image reference
        """
        os_to_image = {
            "ubuntu20.04": "ubuntu:20.04",
            "ubuntu22.04": "ubuntu:22.04",
            "ubuntu24.04": "ubuntu:24.04",
            "openEuler22.03": "openeuler/openeuler:22.03",
            "openEuler24.03": "openeuler/openeuler:24.03",
            "kylinV10": "kylin:v10",
        }
        return os_to_image.get(os_name, "ubuntu:22.04")

    def render_dockerfile(self, context: BuildContext) -> str:
        """
        Render complete Dockerfile from templates.

        Args:
            context: Build context with all configuration

        Returns:
            Complete Dockerfile content as string

        Raises:
            DockerfileGeneratorError: If template rendering fails
        """
        template_vars = context.to_template_vars()
        sections = []

        # Render base template
        base_content = self._render_template("Dockerfile.base.j2", template_vars)
        sections.append(base_content)

        # Render CANN template
        cann_content = self._render_template("Dockerfile.cann.j2", template_vars)
        sections.append(cann_content)

        # Render framework template
        framework_template = f"Dockerfile.{context.framework.value}.j2"
        try:
            framework_content = self._render_template(framework_template, template_vars)
            sections.append(framework_content)
        except TemplateNotFound:
            raise DockerfileGeneratorError(
                f"Template not found: {framework_template}",
                suggestions=[
                    f"Ensure templates/{framework_template} exists",
                    f"Framework '{context.framework.value}' may not be fully supported yet",
                    "Check ADK installation or use a different framework",
                ],
            )

        return "\n".join(sections)

    def _render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        Render a single template with variables.

        Args:
            template_name: Name of template file
            variables: Template variables

        Returns:
            Rendered template content

        Raises:
            DockerfileGeneratorError: If template not found or render fails
        """
        try:
            template = self._jinja_env.get_template(template_name)
            return template.render(**variables)
        except TemplateNotFound:
            raise DockerfileGeneratorError(
                f"Template not found: {template_name}",
                suggestions=[
                    f"Check templates/ directory contains {template_name}",
                    "Verify ADK installation integrity",
                ],
            )

    def render_build_script(self, context: BuildContext) -> str:
        """
        Generate docker build script.

        Args:
            context: Build context

        Returns:
            Shell script content for building the image
        """
        image_tag = self._generate_image_tag(context)
        kernels_check = ""
        if context.cann_kernels_filename:
            kernels_check = f'    "{context.cann_kernels_filename}"'

        script = f'''#!/bin/bash
# =============================================================================
# Build script generated by Ascend Docker Kit (ADK)
# =============================================================================
# CANN Version: {context.cann_version}
# Framework: {context.framework.value} {context.framework_version}
# Target: {context.target.value}
# =============================================================================

set -e

IMAGE_NAME="${{1:-{image_tag}}}"
DOCKERFILE="Dockerfile"

echo "============================================"
echo "Ascend Docker Kit - Image Builder"
echo "============================================"
echo "Image: $IMAGE_NAME"
echo "Target: {context.target.value}"
echo "CANN: {context.cann_version}"
echo "Framework: {context.framework.value} {context.framework_version}"
echo "============================================"

# Check required files
echo "Checking required files..."
REQUIRED_FILES=(
    "{context.cann_toolkit_filename}"
{kernels_check}
    "scripts/install_cann.sh"
    "scripts/check_npu.sh"
)

MISSING_FILES=()
for file in "${{REQUIRED_FILES[@]}}"; do
    if [ -n "$file" ] && [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${{#MISSING_FILES[@]}} -gt 0 ]; then
    echo "ERROR: Missing required files:"
    for file in "${{MISSING_FILES[@]}}"; do
        echo "  - $file"
    done
    echo ""
    echo "Please download CANN packages from https://www.hiascend.com/"
    echo "and copy scripts from the ADK installation."
    exit 1
fi

echo "All required files found."
echo ""

# Build the image
echo "Building Docker image..."
docker build \\
    --target {context.target.value} \\
    -t "$IMAGE_NAME" \\
    -f "$DOCKERFILE" \\
    .

echo ""
echo "============================================"
echo "Build completed successfully!"
echo "============================================"
echo "Image: $IMAGE_NAME"
echo ""
echo "To run the container:"
echo "  ./run.sh $IMAGE_NAME"
echo ""
echo "Or manually:"
echo "  docker run --device /dev/davinci0 --device /dev/davinci_manager $IMAGE_NAME"
echo "============================================"
'''
        return script

    def render_run_script(self, context: BuildContext) -> str:
        """
        Generate docker run script with NPU device mapping.

        Args:
            context: Build context

        Returns:
            Shell script content for running the container
        """
        image_tag = self._generate_image_tag(context)

        script = f'''#!/bin/bash
# =============================================================================
# Run script generated by Ascend Docker Kit (ADK)
# =============================================================================
# Image: {image_tag}
# Target: {context.target.value}
# =============================================================================

set -e

IMAGE_NAME="${{1:-{image_tag}}}"
shift 2>/dev/null || true

echo "============================================"
echo "Ascend Docker Kit - Container Runner"
echo "============================================"
echo "Image: $IMAGE_NAME"
echo "============================================"

# Collect NPU device arguments
DEVICE_ARGS=""

# Map all available davinci devices
for dev in /dev/davinci[0-9]*; do
    if [ -e "$dev" ]; then
        DEVICE_ARGS="$DEVICE_ARGS --device $dev"
        echo "Found NPU device: $dev"
    fi
done

# Required Ascend device files
REQUIRED_DEVICES=(
    "/dev/davinci_manager"
    "/dev/devmm_svm"
    "/dev/hisi_hdc"
)

for dev in "${{REQUIRED_DEVICES[@]}}"; do
    if [ -e "$dev" ]; then
        DEVICE_ARGS="$DEVICE_ARGS --device $dev"
    fi
done

if [ -z "$DEVICE_ARGS" ]; then
    echo "WARNING: No NPU devices found. Container will run without NPU access."
    echo "This is normal if running on a host without Ascend hardware."
fi

echo ""

# Volume mounts for driver access
VOLUME_ARGS=""
if [ -d "/usr/local/Ascend/driver" ]; then
    VOLUME_ARGS="$VOLUME_ARGS -v /usr/local/Ascend/driver:/usr/local/Ascend/driver:ro"
fi
if [ -f "/usr/local/sbin/npu-smi" ]; then
    VOLUME_ARGS="$VOLUME_ARGS -v /usr/local/sbin/npu-smi:/usr/local/sbin/npu-smi:ro"
fi

# Run container
echo "Starting container..."
docker run -it \\
    $DEVICE_ARGS \\
    $VOLUME_ARGS \\
    --shm-size=32g \\
    --ulimit memlock=-1 \\
    --ulimit stack=67108864 \\
    --network host \\
    -e CHECK_NPU=1 \\
    "$IMAGE_NAME" \\
    "$@"
'''
        return script

    def _generate_image_tag(self, context: BuildContext) -> str:
        """
        Generate Docker image tag from context.

        Args:
            context: Build context

        Returns:
            Docker image tag string
        """
        return (
            f"adk/{context.framework.value}:"
            f"{context.framework_version}-cann{context.cann_version}-"
            f"{context.target.value}"
        )

    def generate(self, context: BuildContext) -> GeneratorOutput:
        """
        Generate complete build artifacts.

        Args:
            context: Build context

        Returns:
            GeneratorOutput with all generated content
        """
        dockerfile = self.render_dockerfile(context)
        build_script = self.render_build_script(context)
        run_script = self.render_run_script(context)

        # List required files
        required_files = [
            context.cann_toolkit_filename,
            "scripts/install_cann.sh",
            "scripts/check_npu.sh",
        ]
        if context.cann_kernels_filename:
            required_files.append(context.cann_kernels_filename)

        # Generate notes
        notes = [
            f"Download CANN packages from https://www.hiascend.com/",
            f"Required toolkit: {context.cann_toolkit_filename}",
            f"Required kernels: {context.cann_kernels_filename}",
            "Copy scripts/install_cann.sh and scripts/check_npu.sh to build directory",
        ]

        return GeneratorOutput(
            dockerfile_content=dockerfile,
            build_script_content=build_script,
            run_script_content=run_script,
            context=context,
            required_files=[f for f in required_files if f],
            notes=notes,
        )

    def write_output(
        self,
        output: GeneratorOutput,
        output_dir: Union[str, Path],
    ) -> List[Path]:
        """
        Write generated files to output directory.

        Args:
            output: Generator output
            output_dir: Target directory

        Returns:
            List of written file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files: List[Path] = []

        # Write Dockerfile
        dockerfile_path = output_dir / "Dockerfile"
        dockerfile_path.write_text(output.dockerfile_content)
        written_files.append(dockerfile_path)

        # Write build script
        build_script_path = output_dir / "build.sh"
        build_script_path.write_text(output.build_script_content)
        build_script_path.chmod(0o755)
        written_files.append(build_script_path)

        # Write run script
        run_script_path = output_dir / "run.sh"
        run_script_path.write_text(output.run_script_content)
        run_script_path.chmod(0o755)
        written_files.append(run_script_path)

        return written_files
