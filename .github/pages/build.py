import html
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime

BRANCHES = [("release", ""), ("development", "dev")]
BASE_PATH = os.environ.get("PAGES_BASE_PATH", "").rstrip("/")


def copy_web(branch, slug, out_dir):
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
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write(PLACEHOLDER.format(branch=html.escape(branch)))


def write_version(branch, slug, out_dir):
    commit, subject, date = (
        subprocess.run(
            ["git", "log", "-1", "--format=%H%x00%s%x00%cI", f"origin/{branch}"],
            check=True,
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .split("\0")
    )
    version = {
        "branch": branch,
        "commit": commit,
        "subject": subject,
        "committed_at": date,
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
    }
    with open(os.path.join(out_dir, slug, "version.json"), "w", encoding="utf-8") as f:
        json.dump(version, f, indent=2)


def main():
    out_dir = sys.argv[1]
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir)
    for branch, slug in BRANCHES:
        if not copy_web(branch, slug, out_dir):
            placeholder(branch, slug, out_dir)
        write_version(branch, slug, out_dir)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()


PLACEHOLDER = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Muzeum w autobusie</title>
<style>
  :root {{ --bg:#f7f7f5; --fg:#1a1a1a; --muted:#6b6b6b; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#ececec; --muted:#9a9a9a; }} }}
  body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:var(--bg); color:var(--fg);
         font:16px/1.5 system-ui, sans-serif; padding:16px; text-align:center; }}
  .muted {{ color:var(--muted); }}
</style>
</head>
<body>
<div>
  <h1>Muzeum w autobusie</h1>
  <p class="muted">Gałąź <code>{branch}</code> nie ma jeszcze katalogu <code>web/</code>.</p>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
