# sw2-homebrew-catalog

The app catalog for Switch 2 homebrew built with [sw2-sdk](https://github.com/sw2-homebrew-dev/sw2-sdk). It
lists native (HBLauncher ABI 3) apps and GPUBrew shader apps.

- **People** can browse the site on GitHub Pages.
- **Clients** (the on-console store, `sw2 store`) read
  `https://sw2-homebrew-dev.github.io/sw2-homebrew-catalog/index.json`.
- **Developers**: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Layout

| Path | |
| --- | --- |
| `apps/<id>.json` | one record per app, submitted by pull request |
| `catalog/` | stdlib-only tooling: `check`, `verify`, `build`, `pr-scope` |
| `schema.json` | editor hints for records |
| `.github/workflows/ci.yml` | PR verification and the Pages deploy |

## index.json (`sw2-catalog/1`)

```json
{
  "format": "sw2-catalog/1",
  "generated": "2026-10-30T00:00:00Z",
  "count": 1,
  "apps": [{"id": "...", "name": "...", "kind": "native|gpubrew", "version": "...",
            "artifact_url": "https://...zip", "sha256": "...", "size": 12345, "...": "..."}]
}
```

Clients must check `sha256` before they install anything. Fields can be
added within `sw2-catalog/1`. Any breaking change will use a new `format`.

## Hosting

To enable GitHub Pages, go to Settings → Pages → Source: **GitHub Actions**.
Every merge to `main` re-verifies all artifacts and publishes `_site/`. A
nightly run re-verifies too, so a deleted or replaced release is caught.

## License

MIT for the tooling. Each listed app keeps its own license, shown in its record.
