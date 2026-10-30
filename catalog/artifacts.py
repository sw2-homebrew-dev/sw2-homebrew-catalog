"""Download and inspect a release artifact without executing anything.

Checks that the zip matches its record: size, sha256, a package manifest at
the root (or in one top-level folder) whose id, version and kind agree, safe
paths, and for native packages a build/report.json whose code hash matches
build/code.bin.
"""
import hashlib
import io
import json
import posixpath
import urllib.request
import zipfile

from .records import MAX_ARTIFACT

USER_AGENT = "sw2-homebrew-catalog/1"


def download(url: str, limit: int = MAX_ARTIFACT) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"artifact is larger than {limit} bytes")
    return data


def package_root(names):
    if "manifest.json" in names or "app.json" in names:
        return ""
    tops = {name.split("/", 1)[0] for name in names}
    if len(tops) == 1:
        top = tops.pop()
        if f"{top}/manifest.json" in names or f"{top}/app.json" in names:
            return top + "/"
    raise ValueError("zip has no manifest.json or app.json at its root")


def inspect(record: dict, data: bytes) -> list:
    errors = []
    if len(data) != record["size"]:
        errors.append(f"size is {len(data)}, record says {record['size']}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != record["sha256"]:
        errors.append(f"sha256 is {digest}, record says {record['sha256']}")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return errors + ["artifact is not a zip file"]
    infos = [info for info in archive.infolist() if not info.is_dir()]
    names = {info.filename for info in infos}
    total = 0
    for info in infos:
        normal = posixpath.normpath(info.filename)
        if info.filename.startswith("/") or normal.startswith("..") or "\\" in info.filename:
            errors.append(f"unsafe path {info.filename}")
        total += info.file_size
    if total > MAX_ARTIFACT:
        errors.append("zip expands beyond the size limit")
    if errors:
        return errors
    try:
        root = package_root(names)
    except ValueError as error:
        return [str(error)]

    native = f"{root}manifest.json" in names
    if (record["kind"] == "native") != native:
        errors.append(f"record kind {record['kind']} does not match the package "
                      f"({'manifest.json' if native else 'app.json'})")
    manifest = json.loads(archive.read(f"{root}{'manifest.json' if native else 'app.json'}"))
    if manifest.get("id") != record["id"]:
        errors.append(f"package id {manifest.get('id')!r} does not match {record['id']!r}")
    if str(manifest.get("version")) != str(record["version"]):
        errors.append(f"package version {manifest.get('version')!r} does not match {record['version']!r}")
    if native:
        if manifest.get("abi") != 3:
            errors.append("native packages must target ABI 3")
        try:
            report = json.loads(archive.read(f"{root}build/report.json"))
            code = archive.read(f"{root}build/code.bin")
            if hashlib.sha256(code).hexdigest() != report.get("codeSha256"):
                errors.append("build/code.bin does not match build/report.json")
        except KeyError:
            errors.append("native packages must include build/report.json and build/code.bin")
    else:
        if manifest.get("format") != "hblauncher.gpu-app" or manifest.get("abi") != 1:
            errors.append("gpubrew packages must be hblauncher.gpu-app ABI 1")
        for stage, ref in (manifest.get("shaders") or {}).items():
            name = f"{root}{ref}"
            if name not in names:
                errors.append(f"shader {stage} ({ref}) missing from the zip")
            elif archive.read(name)[:4] != b"\x03\x02\x23\x07":
                errors.append(f"shader {stage} is not SPIR-V")
    return errors


def verify(record: dict) -> list:
    try:
        data = download(record["artifact_url"])
    except Exception as error:  # network errors vary by platform
        return [f"download failed: {error}"]
    return inspect(record, data)
