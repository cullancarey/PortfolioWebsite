"""Typed configuration models for CDK environment settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


@dataclass(frozen=True, slots=True)
class GeoRestrictionsConfig:
    """CloudFront geo-restriction settings for an environment."""

    restriction_type: Literal["none", "blacklist", "whitelist"]
    locations: tuple[str, ...]
    comment: str | None = None

    @classmethod
    def from_context(cls, value: Mapping[str, Any] | None) -> "GeoRestrictionsConfig":
        """Build geo-restriction config from CDK context data."""
        if value is None:
            return cls(restriction_type="none", locations=())

        restriction_type = value.get("restriction_type", "none")
        if restriction_type not in {"none", "blacklist", "whitelist"}:
            raise ValueError(
                "geo_restrictions.restriction_type must be one of: none, blacklist, whitelist"
            )

        locations = value.get("locations", [])
        if not isinstance(locations, list):
            raise TypeError(
                "geo_restrictions.locations must be a list of country codes"
            )

        comment = value.get("comment")
        if comment is not None and not isinstance(comment, str):
            raise TypeError("geo_restrictions.comment must be a string when provided")

        return cls(
            restriction_type=restriction_type,
            locations=tuple(str(location) for location in locations),
            comment=comment,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the config back into a plain dictionary for downstream consumers."""
        payload: dict[str, Any] = {
            "restriction_type": self.restriction_type,
            "locations": list(self.locations),
        }
        if self.comment is not None:
            payload["comment"] = self.comment
        return payload


@dataclass(frozen=True, slots=True)
class EnvironmentConfig:
    """Typed model for a single deployment environment."""

    account_id: str
    region: str
    domain_name: str
    file_path: str
    acm_ssm_params: Mapping[str, str]
    backup_website_bucket_ssm_params: Mapping[str, str]
    geo_restrictions: GeoRestrictionsConfig

    @classmethod
    def from_context(cls, value: Mapping[str, Any]) -> "EnvironmentConfig":
        """Validate and normalize a raw CDK context object."""
        required_string_fields = ("account_id", "region", "domain_name", "file_path")
        missing = [field for field in required_string_fields if field not in value]
        if missing:
            raise ValueError(
                f"Missing required environment config keys: {', '.join(missing)}"
            )

        acm_ssm_params = _require_string_mapping(value, "acm_ssm_params")
        backup_params = _require_string_mapping(
            value, "backup_website_bucket_ssm_params"
        )
        geo_restrictions = GeoRestrictionsConfig.from_context(
            value.get("geo_restrictions")
        )

        return cls(
            account_id=str(value["account_id"]),
            region=str(value["region"]),
            domain_name=str(value["domain_name"]),
            file_path=str(value["file_path"]),
            acm_ssm_params=acm_ssm_params,
            backup_website_bucket_ssm_params=backup_params,
            geo_restrictions=geo_restrictions,
        )


def _require_string_mapping(value: Mapping[str, Any], key: str) -> dict[str, str]:
    """Validate that a context key contains a string-to-string mapping."""
    raw = value.get(key)
    if not isinstance(raw, Mapping):
        raise TypeError(f"{key} must be a mapping of string keys to string values")

    result: dict[str, str] = {}
    for item_key, item_value in raw.items():
        if not isinstance(item_key, str) or not isinstance(item_value, str):
            raise TypeError(f"{key} must contain only string keys and string values")
        result[item_key] = item_value
    return result
