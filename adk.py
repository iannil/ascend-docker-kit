#!/usr/bin/env python3
"""
Ascend Docker Kit (ADK) - CLI Entry Point

DevOps toolkit for Huawei Ascend NPU environments.
Automates Docker environment configuration and resolves CANN/driver/framework
version compatibility issues.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from adk_core import (
    CompatibilityResolver,
    EnvironmentAnalyzer,
    EnvironmentInfo,
    __version__,
)
from adk_core.exceptions import (
    ADKError,
    DriverNotInstalledError,
    EnvironmentDetectionError,
    NPUNotDetectedError,
)
from adk_core.generator import (
    BuildContext,
    BuildTarget,
    DockerfileGenerator,
)
from adk_core.models import FrameworkType


# Default paths
DEFAULT_MATRIX_PATH = Path(__file__).parent / "data" / "compatibility.yaml"


def get_resolver(matrix_path: Optional[Path] = None) -> CompatibilityResolver:
    """
    Load compatibility resolver from YAML.

    Args:
        matrix_path: Optional path to compatibility.yaml

    Returns:
        CompatibilityResolver instance
    """
    path = matrix_path or DEFAULT_MATRIX_PATH
    return CompatibilityResolver.from_yaml(path)


def print_json(data: dict, pretty: bool = True) -> None:
    """
    Print data as JSON.

    Args:
        data: Data to print
        pretty: Whether to pretty-print with indentation
    """
    if pretty:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(json.dumps(data, ensure_ascii=False))


def print_error(error: ADKError) -> None:
    """
    Print error with suggestions.

    Args:
        error: ADKError instance to print
    """
    click.secho(f"Error: {error.message}", fg="red", err=True)
    if error.suggestions:
        click.echo("\nSuggestions:", err=True)
        for suggestion in error.suggestions:
            click.echo(f"  - {suggestion}", err=True)


# =============================================================================
# CLI Group
# =============================================================================


@click.group()
@click.version_option(version=__version__, prog_name="adk")
@click.option(
    "--matrix",
    type=click.Path(exists=True, path_type=Path),
    help="Path to compatibility.yaml",
)
@click.pass_context
def cli(ctx: click.Context, matrix: Optional[Path]) -> None:
    """
    Ascend Docker Kit (ADK) - DevOps toolkit for Huawei Ascend NPU environments.

    Automates Docker environment configuration and resolves CANN/driver/framework
    version compatibility issues.

    \b
    Examples:
      adk query cann --all           # List all CANN versions
      adk query cann 8.0.0           # Show CANN 8.0.0 requirements
      adk diagnose --validate        # Diagnose environment
      adk build init --cann 8.0.0 --framework pytorch
    """
    ctx.ensure_object(dict)
    ctx.obj["matrix_path"] = matrix


# =============================================================================
# Query Commands
# =============================================================================


@cli.group()
def query() -> None:
    """Query compatibility matrix information."""
    pass


@query.command("cann")
@click.argument("version", required=False)
@click.option(
    "--all", "-a", "show_all", is_flag=True, help="Include deprecated versions"
)
@click.option("--json", "-j", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def query_cann(
    ctx: click.Context,
    version: Optional[str],
    show_all: bool,
    as_json: bool,
) -> None:
    """
    Query CANN version information.

    If VERSION is provided, show details for that version.
    Otherwise, list all available versions.

    \b
    Examples:
      adk query cann              # List available versions
      adk query cann 8.0.0        # Show details for 8.0.0
      adk query cann --all -j     # List all versions as JSON
    """
    try:
        resolver = get_resolver(ctx.obj.get("matrix_path"))

        if version:
            # Query specific version
            result = resolver.get_cann_requirements(version)
            if not result.success:
                click.secho(f"Error: {result.error}", fg="red", err=True)
                if result.suggestions:
                    for s in result.suggestions:
                        click.echo(f"  - {s}", err=True)
                sys.exit(1)

            if as_json:
                print_json(result.data)
            else:
                data = result.data
                click.echo(f"CANN Version: {data['cann_version']}")
                click.echo(f"Min Driver:   {data['min_driver_version']}")
                if data.get("max_driver_version"):
                    click.echo(f"Max Driver:   {data['max_driver_version']}")
                click.echo(f"Supported OS: {', '.join(data['supported_os'])}")
                click.echo(f"Supported NPU: {', '.join(data['supported_npu'])}")
                click.echo(f"Architectures: {', '.join(data['supported_arch'])}")
                click.echo(f"Frameworks:   {', '.join(data['frameworks'])}")
                if data.get("deprecated"):
                    click.secho("Status:       DEPRECATED", fg="yellow")
        else:
            # List all versions
            versions = resolver.list_cann_versions(include_deprecated=show_all)
            if as_json:
                print_json({"versions": versions})
            else:
                click.echo("Available CANN Versions:")
                for v in versions:
                    click.echo(f"  - {v}")
                if not show_all:
                    click.echo("\n(Use --all to include deprecated versions)")

    except ADKError as e:
        print_error(e)
        sys.exit(1)


@query.command("framework")
@click.argument("cann_version")
@click.argument("framework", type=click.Choice(["pytorch", "mindspore"]))
@click.option("--json", "-j", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def query_framework(
    ctx: click.Context,
    cann_version: str,
    framework: str,
    as_json: bool,
) -> None:
    """
    Query framework configuration for a CANN version.

    \b
    Examples:
      adk query framework 8.0.0 pytorch
      adk query framework 7.0.0 mindspore --json
    """
    try:
        resolver = get_resolver(ctx.obj.get("matrix_path"))
        result = resolver.find_framework_config(cann_version, framework)

        if not result.success:
            click.secho(f"Error: {result.error}", fg="red", err=True)
            if result.suggestions:
                for s in result.suggestions:
                    click.echo(f"  - {s}", err=True)
            sys.exit(1)

        if as_json:
            print_json(result.data)
        else:
            data = result.data
            click.echo(f"Framework:        {data['framework']}")
            click.echo(f"Version:          {data['version']}")
            if data.get("torch_npu_version"):
                click.echo(f"torch_npu:        {data['torch_npu_version']}")
            click.echo(f"Python Versions:  {', '.join(data['python_versions'])}")
            if data.get("whl_url"):
                click.echo(f"Wheel URL:        {data['whl_url']}")
            if data.get("install_command"):
                click.echo(f"Install Command:  {data['install_command']}")

    except ADKError as e:
        print_error(e)
        sys.exit(1)


# =============================================================================
# Diagnose Command
# =============================================================================


@cli.command()
@click.option("--json", "-j", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "--validate", "-v", is_flag=True, help="Validate against compatibility matrix"
)
@click.pass_context
def diagnose(ctx: click.Context, as_json: bool, validate: bool) -> None:
    """
    Diagnose current host environment.

    Detects OS, architecture, NPU model, and driver version.

    \b
    Examples:
      adk diagnose                # Basic diagnosis
      adk diagnose --validate     # With compatibility check
      adk diagnose -j             # Output as JSON
    """
    try:
        env_info, errors = EnvironmentAnalyzer.analyze_safe()

        if env_info is None:
            if as_json:
                print_json({"status": "error", "errors": errors})
            else:
                click.secho("Environment detection failed:", fg="red", err=True)
                for error in errors:
                    click.echo(f"  - {error}", err=True)
            sys.exit(1)

        result_data = {
            "status": "ok",
            "os_name": env_info.os_name,
            "arch": env_info.arch,
            "npu_type": env_info.npu_type,
            "npu_count": env_info.npu_count,
            "driver_version": env_info.driver_version,
            "firmware_version": env_info.firmware_version,
        }

        if errors:
            result_data["warnings"] = errors

        # Validate if requested
        if validate:
            resolver = get_resolver(ctx.obj.get("matrix_path"))
            validation = resolver.validate_environment(env_info)
            result_data["validation"] = {
                "valid": validation.valid,
                "compatible_cann_versions": validation.compatible_cann_versions,
                "errors": validation.errors,
                "warnings": validation.warnings,
            }

        if as_json:
            print_json(result_data)
        else:
            click.echo("Environment Diagnosis:")
            click.echo(f"  OS:              {result_data['os_name']}")
            click.echo(f"  Architecture:    {result_data['arch']}")
            click.echo(f"  NPU Type:        {result_data['npu_type']}")
            click.echo(f"  NPU Count:       {result_data['npu_count']}")
            click.echo(f"  Driver Version:  {result_data['driver_version']}")
            if result_data.get("firmware_version"):
                click.echo(f"  Firmware:        {result_data['firmware_version']}")

            if errors:
                click.secho("\nWarnings:", fg="yellow")
                for w in errors:
                    click.echo(f"  - {w}")

            if validate and "validation" in result_data:
                v = result_data["validation"]
                click.echo("\nCompatibility Validation:")
                if v["valid"]:
                    click.secho("  Status: COMPATIBLE", fg="green")
                    click.echo(
                        f"  Compatible CANN versions: {', '.join(v['compatible_cann_versions'])}"
                    )
                else:
                    click.secho("  Status: INCOMPATIBLE", fg="red")
                    for e in v["errors"]:
                        click.echo(f"  - {e}")

    except ADKError as e:
        print_error(e)
        sys.exit(1)


# =============================================================================
# Build Command
# =============================================================================


@cli.group()
def build() -> None:
    """Build Docker images for Ascend environments."""
    pass


@build.command("init")
@click.option(
    "--cann",
    "cann_version",
    required=True,
    help="Target CANN version (e.g., 8.0.0)",
)
@click.option(
    "--framework",
    type=click.Choice(["pytorch", "mindspore"]),
    required=True,
    help="Deep learning framework",
)
@click.option(
    "--target",
    type=click.Choice(["train", "inference"]),
    default="train",
    help="Build target (default: train)",
)
@click.option(
    "--python",
    "python_version",
    default=None,
    help="Python version (default: auto-detect from matrix)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Output directory (default: current directory)",
)
@click.option(
    "--auto-detect/--no-auto-detect",
    default=False,
    help="Auto-detect environment for configuration",
)
@click.option(
    "--no-china-mirror",
    is_flag=True,
    help="Disable China mirror configuration",
)
@click.pass_context
def build_init(
    ctx: click.Context,
    cann_version: str,
    framework: str,
    target: str,
    python_version: Optional[str],
    output: Path,
    auto_detect: bool,
    no_china_mirror: bool,
) -> None:
    """
    Initialize build directory with Dockerfile and scripts.

    Generates Dockerfile, build.sh, and run.sh for the specified configuration.

    \b
    Examples:
      adk build init --cann 8.0.0 --framework pytorch
      adk build init --cann 8.0.0 --framework pytorch --target inference -o ./build
      adk build init --cann 7.0.0 --framework mindspore --auto-detect
    """
    try:
        resolver = get_resolver(ctx.obj.get("matrix_path"))
        generator = DockerfileGenerator(resolver)

        # Detect environment if requested
        env_info: Optional[EnvironmentInfo] = None
        if auto_detect:
            env_info, errors = EnvironmentAnalyzer.analyze_safe()
            if env_info:
                click.echo(
                    f"Detected environment: {env_info.os_name} / "
                    f"{env_info.npu_type} / Driver {env_info.driver_version}"
                )
            else:
                click.secho("Warning: Could not auto-detect environment", fg="yellow")
                for e in errors:
                    click.echo(f"  - {e}")

        # Create build context
        context = generator.create_context(
            cann_version=cann_version,
            framework=FrameworkType(framework),
            target=BuildTarget(target),
            env_info=env_info,
            python_version=python_version,
            use_china_mirror=not no_china_mirror,
        )

        click.echo(f"\nConfiguration:")
        click.echo(f"  CANN Version:     {context.cann_version}")
        click.echo(
            f"  Framework:        {context.framework.value} {context.framework_version}"
        )
        if context.torch_npu_version:
            click.echo(f"  torch_npu:        {context.torch_npu_version}")
        click.echo(f"  Python:           {context.python_version}")
        click.echo(f"  Target:           {context.target.value}")
        click.echo(f"  Base Image:       {context.base_image}")
        click.echo(f"  NPU Type:         {context.npu_type}")

        # Generate files
        gen_output = generator.generate(context)
        written_files = generator.write_output(gen_output, output)

        click.secho(f"\nGenerated files in {output}:", fg="green")
        for f in written_files:
            click.echo(f"  - {f.name}")

        click.echo(
            "\nRequired CANN packages (download from https://www.hiascend.com):"
        )
        for f in gen_output.required_files:
            if f.endswith(".run"):
                click.echo(f"  - {f}")

        click.echo("\nNext steps:")
        click.echo(f"  1. Download CANN packages to {output}/")
        click.echo(
            f"  2. Copy scripts/install_cann.sh and scripts/check_npu.sh to {output}/scripts/"
        )
        click.echo(f"  3. Run: cd {output} && ./build.sh")

    except ADKError as e:
        print_error(e)
        sys.exit(1)


# =============================================================================
# Validate Command
# =============================================================================


@cli.command()
@click.argument("cann_version")
@click.option("--json", "-j", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def validate(ctx: click.Context, cann_version: str, as_json: bool) -> None:
    """
    Validate current environment against a CANN version.

    \b
    Examples:
      adk validate 8.0.0
      adk validate 7.0.0 --json
    """
    try:
        resolver = get_resolver(ctx.obj.get("matrix_path"))
        env_info = EnvironmentAnalyzer.analyze()

        # Check each compatibility requirement
        checks = {
            "driver": {"status": "ok", "message": ""},
            "os": {"status": "ok", "message": ""},
            "npu": {"status": "ok", "message": ""},
        }

        try:
            resolver.check_driver_compatibility(env_info.driver_version, cann_version)
        except ADKError as e:
            checks["driver"] = {"status": "fail", "message": e.message}

        try:
            resolver.check_os_compatibility(env_info.os_name, cann_version)
        except ADKError as e:
            checks["os"] = {"status": "fail", "message": e.message}

        try:
            resolver.check_npu_compatibility(env_info.npu_type, cann_version)
        except ADKError as e:
            checks["npu"] = {"status": "fail", "message": e.message}

        all_ok = all(c["status"] == "ok" for c in checks.values())

        if as_json:
            print_json(
                {
                    "cann_version": cann_version,
                    "environment": {
                        "driver_version": env_info.driver_version,
                        "os_name": env_info.os_name,
                        "npu_type": env_info.npu_type,
                    },
                    "checks": checks,
                    "compatible": all_ok,
                }
            )
        else:
            click.echo(f"Validating environment for CANN {cann_version}:\n")
            click.echo("Environment:")
            click.echo(f"  Driver: {env_info.driver_version}")
            click.echo(f"  OS:     {env_info.os_name}")
            click.echo(f"  NPU:    {env_info.npu_type}")
            click.echo()

            for check_name, check_result in checks.items():
                if check_result["status"] == "ok":
                    click.secho(f"  [{check_name.upper()}] PASS", fg="green")
                else:
                    click.secho(
                        f"  [{check_name.upper()}] FAIL: {check_result['message']}",
                        fg="red",
                    )

            click.echo()
            if all_ok:
                click.secho("Result: COMPATIBLE", fg="green", bold=True)
            else:
                click.secho("Result: INCOMPATIBLE", fg="red", bold=True)
                sys.exit(1)

    except (DriverNotInstalledError, NPUNotDetectedError) as e:
        if as_json:
            print_json(
                {
                    "cann_version": cann_version,
                    "error": e.message,
                    "compatible": False,
                }
            )
        else:
            click.secho(f"Cannot validate: {e.message}", fg="red", err=True)
            click.echo(
                "This command requires running on a host with NPU hardware.", err=True
            )
        sys.exit(1)
    except ADKError as e:
        print_error(e)
        sys.exit(1)


# =============================================================================
# Entry Point
# =============================================================================


if __name__ == "__main__":
    cli()
