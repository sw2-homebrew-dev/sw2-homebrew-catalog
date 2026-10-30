"""App records: apps/<id>.json, one file per app.

Validation is deterministic and offline; `verify` (artifacts.py) is the only
part that touches the network.  Nothing here executes submitted code.
"""
import json
import pathlib
import re
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS = ROOT / "apps"

ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
SHA256 = re.compile(r"[0-9a-f]{64}")
VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]{0,31}")
KINDS = ("native", "gpubrew")
CATEGORIES = ("game", "emulator", "media", "utility", "tool", "demo", "app")
REQUIRED = ("id", "name", "kind", "version", "description", "author", "category",
            "license", "source_repo", "artifact_url", "sha256", "size")
OPTIONAL = ("icon_url", "screenshots", "homepage", "min_sdk", "notes", "added", "updated")
LIMITS = {"name": 48, "description": 160, "author": 32, "notes": 500}
MAX_ARTIFACT = 256 * 1024 * 1024


def https_url(value: str, field: str, errors: list):
    parsed = urlparse(value or "")
    if parsed.scheme != "https" or not parsed.netloc:
        errors.append(f"{field} must be an https URL")


def validate(record: dict, filename: str = "") -> list:
    errors = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    for key in REQUIRED:
        if key not in record:
            errors.append(f"missing {key}")
    for key in record:
        if key not in REQUIRED and key not in OPTIONAL:
            errors.append(f"unknown field {key}")
    if errors:
        return errors

    if not ID.fullmatch(str(record["id"])):
        errors.append("id must match [a-z0-9][a-z0-9._-]{0,63}")
    if filename and filename != f"{record['id']}.json":
        errors.append(f"file must be named {record['id']}.json")
    if record["kind"] not in KINDS:
        errors.append(f"kind must be one of {', '.join(KINDS)}")
    if record["category"] not in CATEGORIES:
        errors.append(f"category must be one of {', '.join(CATEGORIES)}")
    if not VERSION.fullmatch(str(record["version"])):
        errors.append("version must be 1-32 chars of [0-9A-Za-z.+_-]")
    for key, limit in LIMITS.items():
        value = record.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must be a non-empty string")
        elif len(value) > limit:
            errors.append(f"{key} is longer than {limit} characters")
    if not isinstance(record["license"], str) or not record["license"].strip():
        errors.append("license must name an SPDX identifier (or 'proprietary')")
    if not SHA256.fullmatch(str(record["sha256"])):
        errors.append("sha256 must be 64 lowercase hex characters")
    if not isinstance(record["size"], int) or not 0 < record["size"] <= MAX_ARTIFACT:
        errors.append(f"size must be an integer in 1..{MAX_ARTIFACT}")
    https_url(record["artifact_url"], "artifact_url", errors)
    https_url(record["source_repo"], "source_repo", errors)
    if not str(record["artifact_url"]).lower().endswith(".zip"):
        errors.append("artifact_url must point at a .zip")
    for key in ("icon_url", "homepage"):
        if record.get(key):
            https_url(record[key], key, errors)
    shots = record.get("screenshots", [])
    if not isinstance(shots, list) or len(shots) > 8:
        errors.append("screenshots must be a list of at most 8 URLs")
    else:
        for index, url in enumerate(shots):
            https_url(url, f"screenshots[{index}]", errors)
    return errors


def load_all(directory: pathlib.Path = APPS):
    """Returns (records, problems) where problems maps filename -> [errors]."""
    records, problems = [], {}
    seen = {}
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            problems[path.name] = [f"invalid JSON: {error}"]
            continue
        errors = validate(record, path.name)
        if not errors and record["id"] in seen:
            errors.append(f"duplicate id (also in {seen[record['id']]})")
        if errors:
            problems[path.name] = errors
            continue
        seen[record["id"]] = path.name
        records.append(record)
    return records, problems
