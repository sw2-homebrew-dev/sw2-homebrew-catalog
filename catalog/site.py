"""Build the GitHub Pages site: index.json for clients, index.html for people."""
import datetime
import html
import json
import pathlib
import shutil

FORMAT = "sw2-catalog/1"
PUBLIC_FIELDS = ("id", "name", "kind", "version", "description", "author", "category",
                 "license", "source_repo", "homepage", "artifact_url", "sha256", "size",
                 "icon_url", "screenshots", "min_sdk", "added", "updated")


def index_document(records, generated=None):
    apps = [{k: r[k] for k in PUBLIC_FIELDS if k in r}
            for r in sorted(records, key=lambda r: r["name"].lower())]
    return {"format": FORMAT,
            "generated": generated or datetime.datetime.now(datetime.timezone.utc)
                                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count": len(apps), "apps": apps}


def human_size(size: int) -> str:
    for unit in ("B", "KiB", "MiB"):
        if size < 1024 or unit == "MiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return str(size)


CARD = """<article class="app" data-kind="{kind}" data-search="{search}">
  <div class="icon">{icon}</div>
  <div class="body">
    <h2>{name} <span class="version">{version}</span></h2>
    <p class="meta">{author} · {category} · <span class="kind">{kind}</span> · {size} · {license}</p>
    <p>{description}</p>
    <p class="actions"><code>sw2 store install {id}</code>
      <a href="{artifact}">zip</a> <a href="{source}">source</a></p>
  </div>
</article>"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Switch 2 Homebrew Catalog</title>
<style>
:root {{ --bg:#f6f7f9; --card:#fff; --ink:#1b2430; --muted:#5b6675; --line:#dde2e8; --accent:#d8432f; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#11151b; --card:#1a2028; --ink:#e7ebf0; --muted:#97a2b0; --line:#2a323d; --accent:#ff6b55; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 system-ui,sans-serif; }}
main {{ max-width:960px; margin:0 auto; padding:24px 16px 64px; }}
header h1 {{ margin:0 0 4px; font-size:28px; }}
header p {{ margin:0 0 16px; color:var(--muted); }}
.controls {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; }}
input, select {{ font:inherit; padding:8px 10px; border:1px solid var(--line); border-radius:8px;
  background:var(--card); color:var(--ink); }}
input {{ flex:1; min-width:200px; }}
.app {{ display:flex; gap:16px; background:var(--card); border:1px solid var(--line);
  border-radius:12px; padding:16px; margin-bottom:12px; }}
.icon img, .icon span {{ width:72px; height:72px; border-radius:14px; display:grid; place-items:center;
  background:var(--line); font-size:32px; font-weight:700; object-fit:cover; }}
.body {{ min-width:0; flex:1; }}
h2 {{ margin:0; font-size:19px; }}
.version {{ color:var(--muted); font-weight:400; font-size:15px; }}
.meta {{ margin:2px 0 6px; color:var(--muted); font-size:14px; }}
.kind {{ color:var(--accent); }}
.body p {{ margin:4px 0; overflow-wrap:anywhere; }}
.actions code {{ background:var(--bg); padding:2px 6px; border-radius:6px; margin-right:8px; }}
a {{ color:var(--accent); }}
.empty {{ color:var(--muted); text-align:center; padding:48px 0; }}
footer {{ color:var(--muted); font-size:14px; margin-top:32px; }}
</style>
</head>
<body>
<main>
<header>
  <h1>Switch 2 Homebrew Catalog</h1>
  <p>{count} apps for <a href="https://github.com/sw2-homebrew-dev/sw2-sdk">sw2-sdk</a> launchers · machine-readable index:
    <a href="index.json">index.json</a></p>
</header>
<div class="controls">
  <input id="q" type="search" placeholder="Search apps" aria-label="Search apps">
  <select id="kind" aria-label="Package kind">
    <option value="">All kinds</option><option value="native">Native</option><option value="gpubrew">GPUBrew</option>
  </select>
</div>
<section id="apps">
{cards}
</section>
<p class="empty" id="none" {empty_hidden}>No apps listed yet. See CONTRIBUTING.md to submit one.</p>
<footer>Generated {generated}. Listing an app is not an endorsement; check the source before running it.</footer>
</main>
<script>
const q=document.getElementById('q'),k=document.getElementById('kind'),cards=[...document.querySelectorAll('.app')],none=document.getElementById('none');
function filter(){{const t=q.value.toLowerCase().trim(),kind=k.value;let shown=0;
for(const c of cards){{const ok=(!kind||c.dataset.kind===kind)&&(!t||c.dataset.search.includes(t));c.hidden=!ok;shown+=ok;}}
none.hidden=shown>0;}}
q.addEventListener('input',filter);k.addEventListener('change',filter);
</script>
</body>
</html>
"""


def render_html(document) -> str:
    cards = []
    for app in document["apps"]:
        e = {k: html.escape(str(app.get(k, "")), quote=True) for k in PUBLIC_FIELDS}
        icon = (f'<img src="{e["icon_url"]}" alt="" loading="lazy">' if app.get("icon_url")
                else f'<span>{html.escape(app["name"][:1].upper())}</span>')
        search = html.escape(" ".join(str(app.get(k, "")) for k in
                                      ("id", "name", "author", "category", "description")).lower())
        cards.append(CARD.format(kind=e["kind"], search=search, icon=icon, name=e["name"],
                                 version=e["version"], author=e["author"], category=e["category"],
                                 size=human_size(app["size"]), license=e["license"],
                                 description=e["description"], id=e["id"],
                                 artifact=e["artifact_url"], source=e["source_repo"]))
    return PAGE.format(count=document["count"], cards="\n".join(cards),
                       empty_hidden="hidden" if cards else "",
                       generated=html.escape(document["generated"]))


def build(records, out: pathlib.Path, generated=None) -> dict:
    if out.exists():
        shutil.rmtree(out)
    (out / "apps").mkdir(parents=True)
    document = index_document(records, generated)
    (out / "index.json").write_text(json.dumps(document, separators=(",", ":")) + "\n")
    (out / "index.html").write_text(render_html(document), encoding="utf-8")
    for app in document["apps"]:
        (out / "apps" / f"{app['id']}.json").write_text(json.dumps(app, indent=2) + "\n")
    (out / ".nojekyll").write_text("")
    return document
