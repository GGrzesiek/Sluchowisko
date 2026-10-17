"""Buduje stronę GitHub Pages z aplikacji na gałęziach release i development.

Użycie: python3 .github/pages/build.py <katalog_wyjściowy>

- /         aplikacja z web/ na gałęzi release (produkcja)
- /dev/     aplikacja z web/ na gałęzi development
- /status/  ostatnie commity, różnica między gałęziami i otwarte PR-y

web/ jest publikowany bez zmian. Jeśli ma package.json, najpierw uruchamiane jest
`npm ci && npm run build`, a publikowany jest web/dist. Ścieżka bazowa strony trafia
do builda w zmiennej BASE_PATH (np. /opendatahackathon42/dev/).
"""

import html
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

# (gałąź, podkatalog na stronie; "" to katalog główny)
BRANCHES = [("release", ""), ("development", "dev")]
REPO = os.environ.get("GITHUB_REPOSITORY", "")
SERVER = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
REPO_URL = f"{SERVER}/{REPO}"
BASE_PATH = os.environ.get("PAGES_BASE_PATH", "").rstrip("/")


def run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def last_commit(branch):
    fmt = "%H%x00%s%x00%an%x00%cI"
    sha, subject, author, date = run("git", "log", "-1", f"--format={fmt}", f"origin/{branch}").split("\0")
    return {"sha": sha, "subject": subject, "author": author, "date": date}


def recent_commits(branch, n=8):
    out = run("git", "log", f"-{n}", "--format=%h%x00%s%x00%an", f"origin/{branch}")
    return [line.split("\0") for line in out.splitlines() if line]


def open_prs():
    try:
        out = run("gh", "pr", "list", "--repo", REPO, "--state", "open", "--limit", "50",
                  "--json", "number,title,author,baseRefName,headRefName,isDraft,url,reviewDecision")
        return json.loads(out)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def copy_web(branch, slug, out_dir):
    """Publikuje web/ z danej gałęzi w out_dir/slug. Zwraca True, jeśli było co publikować."""
    if subprocess.run(["git", "cat-file", "-e", f"origin/{branch}:web"], capture_output=True).returncode:
        return False
    tmp = os.path.join(out_dir, f".tmp-{slug or 'root'}")
    os.makedirs(tmp)
    archive = subprocess.run(["git", "archive", f"origin/{branch}", "web"], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", tmp], input=archive, check=True)
    src = os.path.join(tmp, "web")
    if os.path.exists(os.path.join(src, "package.json")):
        env = {**os.environ, "BASE_PATH": f"{BASE_PATH}/{slug}/" if slug else f"{BASE_PATH}/"}
        subprocess.run(["npm", "ci"], cwd=src, check=True, env=env)
        subprocess.run(["npm", "run", "build"], cwd=src, check=True, env=env)
        src = os.path.join(src, "dist")
    shutil.copytree(src, os.path.join(out_dir, slug), dirs_exist_ok=True)
    shutil.rmtree(tmp)
    return True


def placeholder(branch, slug, out_dir):
    dest = os.path.join(out_dir, slug)
    os.makedirs(dest, exist_ok=True)
    status = "../status/" if slug else "status/"
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write(PLACEHOLDER.format(branch=html.escape(branch), status=status))


def ago(iso):
    delta = datetime.now(timezone.utc) - datetime.fromisoformat(iso)
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min temu"
    if minutes < 48 * 60:
        return f"{minutes // 60} h temu"
    return f"{minutes // 1440} dni temu"


def branch_card(branch, slug, has_web):
    c = last_commit(branch)
    e = html.escape
    commits = "".join(
        f'<li><a href="{REPO_URL}/commit/{e(h)}"><code>{e(h)}</code></a> {e(s)} <span class="muted">— {e(a)}</span></li>'
        for h, s, a in recent_commits(branch)
    )
    preview = (f'<a class="btn" href="../{slug + "/" if slug else ""}">Otwórz aplikację</a>' if has_web
               else '<span class="muted">Brak katalogu <code>web/</code> — aplikacja pojawi się, gdy powstanie.</span>')
    return f"""
    <section class="card">
      <h2>{e(branch)}</h2>
      <p class="head"><a href="{REPO_URL}/commit/{c['sha']}"><code>{c['sha'][:7]}</code></a> {e(c['subject'])}</p>
      <p class="muted">{e(c['author'])} · <time datetime="{c['date']}">{ago(c['date'])}</time></p>
      <p>{preview}</p>
      <h3>Ostatnie commity</h3>
      <ul class="commits">{commits}</ul>
    </section>"""


def pr_rows(prs):
    if not prs:
        return '<p class="muted">Brak otwartych PR-ów.</p>'
    e = html.escape
    rows = []
    for pr in prs:
        state = "draft" if pr["isDraft"] else {"APPROVED": "zatwierdzony", "CHANGES_REQUESTED": "poprawki"}.get(
            pr.get("reviewDecision") or "", "czeka na review")
        rows.append(
            f'<tr><td><a href="{e(pr["url"])}">#{pr["number"]}</a></td><td>{e(pr["title"])}</td>'
            f'<td><code>{e(pr["headRefName"])}</code> → <code>{e(pr["baseRefName"])}</code></td>'
            f'<td>{e(pr["author"]["login"])}</td><td>{state}</td></tr>')
    return ('<table><thead><tr><th>PR</th><th>Tytuł</th><th>Gałęzie</th><th>Autor</th><th>Stan</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


def main():
    out_dir = sys.argv[1]
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir)

    cards = ""
    for branch, slug in BRANCHES:
        has_web = copy_web(branch, slug, out_dir)
        if not has_web:
            placeholder(branch, slug, out_dir)
        cards += branch_card(branch, slug, has_web)
    ahead = int(run("git", "rev-list", "--count", "origin/release..origin/development"))
    behind = int(run("git", "rev-list", "--count", "origin/development..origin/release"))
    if ahead == 0 and behind == 0:
        diff = "release i development wskazują ten sam stan."
    else:
        diff = f"development ma <b>{ahead}</b> commitów, których nie ma w release"
        if behind:
            diff += f"; release ma <b>{behind}</b> commitów spoza development (warto zrobić rebase)"
        diff += f'. <a href="{REPO_URL}/compare/release...development">Porównaj</a>'

    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = TEMPLATE.format(repo=html.escape(REPO), repo_url=REPO_URL, diff=diff, cards=cards,
                           prs=pr_rows(open_prs()), built=built)
    os.makedirs(os.path.join(out_dir, "status"), exist_ok=True)
    with open(os.path.join(out_dir, "status", "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()


TEMPLATE = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Status gałęzi</title>
<style>
  :root {{ --bg:#f7f7f5; --card:#fff; --fg:#1a1a1a; --muted:#6b6b6b; --line:#e3e3e0; --accent:#1d5fd1; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#141414; --card:#1e1e1e; --fg:#ececec; --muted:#9a9a9a; --line:#2e2e2e; --accent:#7aa7ff; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; }}
  main {{ max-width:1100px; margin:0 auto; padding:24px 16px 48px; }}
  a {{ color:var(--accent); }}
  h1 {{ margin:0 0 4px; font-size:24px; }}
  h2 {{ margin:0 0 8px; font-size:20px; }}
  h3 {{ margin:16px 0 6px; font-size:14px; color:var(--muted); font-weight:600; }}
  .muted {{ color:var(--muted); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:16px; margin:20px 0; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px; min-width:0; }}
  .head {{ margin:0; font-weight:600; overflow-wrap:anywhere; }}
  .btn {{ display:inline-block; padding:6px 12px; border:1px solid var(--accent); border-radius:6px; text-decoration:none; }}
  .commits {{ margin:0; padding-left:18px; }}
  .commits li {{ overflow-wrap:anywhere; }}
  .table-wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:10px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ font-size:13px; color:var(--muted); }}
</style>
</head>
<body>
<main>
  <h1>Status gałęzi</h1>
  <p class="muted"><a href="{repo_url}">{repo}</a> · zbudowano {built} · <a href="../">produkcja</a> · <a href="../dev/">dev</a></p>
  <p>{diff}</p>
  <div class="grid">{cards}</div>
  <h2>Otwarte pull requesty</h2>
  <div class="table-wrap">{prs}</div>
</main>
</body>
</html>
"""

PLACEHOLDER = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Muzeum w autobusie</title>
<style>
  :root {{ --bg:#f7f7f5; --fg:#1a1a1a; --muted:#6b6b6b; --accent:#1d5fd1; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#ececec; --muted:#9a9a9a; --accent:#7aa7ff; }} }}
  body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:var(--bg); color:var(--fg);
         font:16px/1.5 system-ui, sans-serif; padding:16px; text-align:center; }}
  a {{ color:var(--accent); }} .muted {{ color:var(--muted); }}
</style>
</head>
<body>
<div>
  <h1>Muzeum w autobusie</h1>
  <p class="muted">Gałąź <code>{branch}</code> nie ma jeszcze katalogu <code>web/</code>.</p>
  <p><a href="{status}">Status gałęzi</a></p>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
