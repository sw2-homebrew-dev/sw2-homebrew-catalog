import hashlib
import io
import json
import pathlib
import tempfile
import unittest
import zipfile

from catalog import artifacts, records, site

SPIRV = b"\x03\x02\x23\x07" + b"\0" * 16


def gpubrew_zip(app_id="demo", version="1.0.0"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(f"{app_id}/app.json", json.dumps({
            "format": "hblauncher.gpu-app", "abi": 1, "id": app_id, "name": "Demo",
            "version": version, "shaders": {"vertex": "v.spv", "fragment": "f.spv", "compute": "c.spv"}}))
        for name in ("v.spv", "f.spv", "c.spv"):
            zf.writestr(f"{app_id}/{name}", SPIRV)
    return buffer.getvalue()


def record_for(data, **extra):
    base = {"id": "demo", "name": "Demo", "kind": "gpubrew", "version": "1.0.0",
            "description": "A demo", "author": "someone", "category": "demo", "license": "MIT",
            "source_repo": "https://github.com/someone/demo",
            "artifact_url": "https://github.com/someone/demo/releases/download/v1.0.0/demo-1.0.0.zip",
            "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    base.update(extra)
    return base


class Records(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(records.validate(record_for(gpubrew_zip()), "demo.json"), [])

    def test_rejects(self):
        data = gpubrew_zip()
        cases = {
            "file must be named": ({}, "other.json"),
            "unknown field": ({"extra": 1}, "demo.json"),
            "https URL": ({"artifact_url": "http://x/demo.zip"}, "demo.json"),
            "kind must be": ({"kind": "nro"}, "demo.json"),
            "sha256 must be": ({"sha256": "ABC"}, "demo.json"),
            "longer than": ({"description": "x" * 161}, "demo.json"),
        }
        for message, (change, filename) in cases.items():
            errors = records.validate(record_for(data, **change), filename)
            self.assertTrue(any(message in e for e in errors), (message, errors))

    def test_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            r = record_for(gpubrew_zip())
            (folder / "demo.json").write_text(json.dumps(r))
            (folder / "zzz.json").write_text(json.dumps(r))
            loaded, problems = records.load_all(folder)
            self.assertEqual(len(loaded), 1)
            self.assertIn("zzz.json", problems)


class Artifacts(unittest.TestCase):
    def test_matching_package(self):
        data = gpubrew_zip()
        self.assertEqual(artifacts.inspect(record_for(data), data), [])

    def test_mismatches(self):
        data = gpubrew_zip(version="1.0.1")
        errors = artifacts.inspect(record_for(data, kind="native", sha256="0" * 64), data)
        joined = "\n".join(errors)
        self.assertIn("sha256", joined)

        errors = artifacts.inspect(record_for(data, kind="native"), data)
        joined = "\n".join(errors)
        self.assertIn("does not match the package", joined)
        self.assertIn("version", joined)

    def test_unsafe_path(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("../evil", b"x")
        data = buffer.getvalue()
        self.assertTrue(any("unsafe" in e for e in artifacts.inspect(record_for(data), data)))


class Site(unittest.TestCase):
    def test_build_escapes_and_indexes(self):
        data = gpubrew_zip()
        r = record_for(data, name="<script>x</script>")
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "site"
            document = site.build([r], out, generated="2026-01-01T00:00:00Z")
            self.assertEqual(document["format"], "sw2-catalog/1")
            index = json.loads((out / "index.json").read_text())
            self.assertEqual(index["apps"][0]["id"], "demo")
            page = (out / "index.html").read_text()
            self.assertNotIn("<script>x</script>", page)
            self.assertIn("&lt;script&gt;", page)
            self.assertTrue((out / "apps/demo.json").exists())


if __name__ == "__main__":
    unittest.main()
