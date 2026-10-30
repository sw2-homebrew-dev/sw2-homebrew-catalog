# Submitting an app

1. Build and package it with [sw2-sdk](https://github.com/sw2-homebrew-dev/sw2-sdk):

   ```sh
   sw2 build apps/my-app
   sw2 package apps/my-app \
     --url-base https://github.com/<you>/<repo>/releases/download/v1.0.0 \
     --author "<you>" --category game --license MIT \
     --source-repo https://github.com/<you>/<repo>
   ```

   The [sw2-app-boilerplate](https://github.com/sw2-homebrew-dev/sw2-app-boilerplate) release workflow does
   this for you on every tag.

2. Upload `dist/<id>-<version>.zip` to that GitHub release. Never replace
   a release asset in place. Publish a new version instead, because the
   catalog pins the sha256.

3. Copy `dist/<id>.catalog.json` to `apps/<id>.json` in this repository and
   open a pull request. Change only that file.

CI checks the record offline. It then downloads the zip and checks that the
size, sha256, package id, version and kind all match, that paths are safe,
that native packages include a `build/report.json` matching
`build/code.bin`, and that GPUBrew shaders are SPIR-V. **Nothing you submit
is ever executed by CI.**

## Record fields

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | `[a-z0-9][a-z0-9._-]{0,63}`; same as the package id and the file name |
| `name` | yes | up to 48 chars |
| `kind` | yes | `native` (manifest.json) or `gpubrew` (app.json) |
| `version` | yes | must equal the package's version |
| `description` | yes | up to 160 chars, shown on the console |
| `author` | yes | up to 32 chars |
| `category` | yes | game, emulator, media, utility, tool, demo, app |
| `license` | yes | SPDX id, or `proprietary` |
| `source_repo` | yes | https |
| `artifact_url` | yes | https, `.zip` |
| `sha256`, `size` | yes | of the zip |
| `icon_url`, `homepage`, `screenshots`, `notes`, `min_sdk` | no | |

`schema.json` gives editors hints. `catalog/records.py` is the authoritative check.

## Updating

Bump the version, release a new zip, and change the record's `version`,
`artifact_url`, `sha256` and `size` in one pull request.

## Tooling changes

Discuss them in an issue first. Run the checks before you open a pull request:

```sh
python3 -m unittest discover -s tests
python3 -m catalog check
python3 -m catalog build --out _site
```
