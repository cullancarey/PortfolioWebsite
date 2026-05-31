"""Helpers for building SSM parameter replication configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class SsmReplicationConfig:
    """Derived SSM replication settings for a parameter group."""

    param_path_prefix: str
    parameters: list[dict[str, str]]


def build_ssm_replication_config(
    parameter_names: Sequence[str],
) -> SsmReplicationConfig:
    """Build a consistent replication config from a list of parameter names.

    The returned mapping replicates each parameter to the same name in the
    target region and derives the least-privilege IAM path prefix from the
    first parameter in the group.
    """
    if not parameter_names:
        raise ValueError("At least one parameter name is required for replication")

    normalized_names = [name for name in parameter_names]
    prefix = _derive_parameter_path_prefix(normalized_names[0])
    parameters = [
        {"source": parameter_name, "target": parameter_name}
        for parameter_name in normalized_names
    ]

    return SsmReplicationConfig(param_path_prefix=prefix, parameters=parameters)


def _derive_parameter_path_prefix(parameter_name: str) -> str:
    """Extract the top-level SSM path prefix used for IAM scoping."""
    stripped = parameter_name.lstrip("/")
    parts = stripped.split("/")
    if not parts or not parts[0]:
        raise ValueError(f"Invalid SSM parameter name: {parameter_name!r}")
    return f"/{parts[0]}"
