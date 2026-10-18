# Infrastructure (GCP)

A shared database and recordings store for the team during development, so nobody works from a stale local copy.
The app talks to the backend on Cloud Run and loads photos and recordings from the public media bucket (see
`AGENTS.md`).

| What                              | Where                                                          |
| --------------------------------- | -------------------------------------------------------------- |
| Project                           | `muzeum-w-autobusie-2026`, region `europe-central2`            |
| PostgreSQL 16 (Cloud SQL)         | instance `muzeum`, database `muzeum`, IAM login only           |
| ElevenLabs recordings             | bucket `muzeum-w-autobusie-2026-audio`, private, versioned     |
| Facts collector output            | bucket `muzeum-w-autobusie-2026-data`, private, versioned      |
| Photos and recordings for the app | bucket `muzeum-w-autobusie-2026-media`, public read, versioned |
| Terraform state                   | bucket `muzeum-w-autobusie-2026-tfstate`                       |
| Backend (Django)                  | Cloud Run service `backend`, public HTTPS                      |
| Owner and billing                 | Grzesiek (#5)                                                  |

There are no passwords or key files anywhere. People sign in with their Google account, GitHub Actions with
Workload Identity Federation.

## How changes reach GCP

| Directory         | Applied by                            | Contains                                                         |
| ----------------- | ------------------------------------- | ---------------------------------------------------------------- |
| `infra/bootstrap` | the owner, locally, rarely            | APIs, GitHub identity pool, `tf-plan` and `tf-apply`             |
| `infra`           | `.github/workflows/infra.yml` (CI/CD) | database, bucket, access, `team` and `readers` roles in Postgres |

- Pull request touching `infra/**`: CI runs `terraform plan` as `tf-plan` (read-only) and shows it in the job summary.
- Merge into `development`: CD runs `terraform apply` as `tf-apply`, then `database.sql` and the writer grants.
  Only pushes to `development` can act as `tf-apply`, and `development` accepts reviewed PRs only.

## Backend on Cloud Run

`infra/backend.tf`: Cloud Run service `backend` running the Django image with a `cloud-sql-proxy` sidecar, so the app
logs in to Postgres as the service account `backend-api` (role `team`) without a password. The image lives in
Artifact Registry `backend`; `.github/workflows/backend.yml` builds and deploys it on every push to `development` that
touches the backend, then checks `/api/health/`. Terraform creates the service with a placeholder image and ignores
later image changes.

Each deploy starts a new revision without traffic, checks its `/api/health/` (database), and only then
moves traffic to it. A red deploy leaves the previous revision serving.

Secrets are created by the owner, never in Terraform or in the repo. Create each one **before** the apply that first
uses it in `infra/backend.tf`, or the apply stops halfway (rerun it after creating it). If the apply fails with
"Permission denied on secret", IAM has not propagated yet: rerun the Infra job once.

| Secret                | Env var in Cloud Run  | Used for                                                       |
| --------------------- | --------------------- | -------------------------------------------------------------- |
| `django-secret-key`   | `SECRET_KEY`          | Django                                                         |
| `stories-write-token` | `STORIES_WRITE_TOKEN` | writes to `/api/stories/` and `?draft=1`, by the stories agent |

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50), end='')" | gcloud secrets create django-secret-key --project muzeum-w-autobusie-2026 --data-file=-
python3 -c "import secrets; print(secrets.token_urlsafe(32), end='')" | gcloud secrets create stories-write-token --project muzeum-w-autobusie-2026 --data-file=-
```

The owner passes the stories token to whoever runs the stories agent privately, never through the repo or chat logs.

Each deploy runs `python manage.py migrate` in the new image, through the Cloud SQL proxy as `tf-apply` (role `team`),
before the new revision gets any traffic. Migrations must therefore also work with the previous revision still
serving for a minute: add columns and tables first, drop old ones in a later deploy. A failed migration stops the deploy
and the previous revision keeps serving.

The city servers (`dane.um.warszawa.pl`, `api.um.warszawa.pl`, `wms.um.warszawa.pl`) answer only from Polish IP
addresses: from Cloud Shell (Netherlands) and GitHub Actions (USA) they time out, from Cloud Run in `europe-central2`
(Warsaw) they answer in under 0.5 s (checked 2026-10-17). The backend therefore runs in `europe-central2` with
`CITY_API_LIVE=1` and the ZTM key from Secret Manager (`ztm-api-key`): each ride request fetches positions itself,
cached for 10 s. Keep the service in a Polish region.

`python manage.py poll_vehicles --demo` still works from a laptop, for local development or as a fallback.

## Who can do what

| Who                                                              | Database                       | `audio` and `data` buckets | `media` bucket                              |
| ---------------------------------------------------------------- | ------------------------------ | -------------------------- | ------------------------------------------- |
| Writers: emails in the repo variable `INFRA_MEMBERS`             | read and write, as role `team` | read and write             | read and write                              |
| Team: members of the Google Group `sluchowisko@googlegroups.com` | read only, as role `readers`   | read only                  | read a file by its URL                      |
| Anyone, including the app in a browser                           | none                           | none                       | read a file by its URL, not list the bucket |

Data reaches GCP only through the writers. Everyone else reads the same copy.

The `media` bucket holds only what the app shows: `photos/<groupId>/<imageId>.jpg` and `audio/<groupId>.mp3`, copied
unmodified from the `data` and `audio` buckets. A story's `photos[].src` and audio URL point there, as
`https://storage.googleapis.com/muzeum-w-autobusie-2026-media/<path>`.

## Getting read access (teammates)

1. Ask Grzesiek to add you to `sluchowisko@googlegroups.com`. Access works about 15 minutes after joining.
2. Sign in:
   ```
   gcloud auth login
   gcloud auth application-default login
   gcloud auth application-default set-quota-project muzeum-w-autobusie-2026
   ```
3. Copy the GCP lines from `.env.example` to `.env` and set `DB_USER` to your email.

### Connecting

Python, with the Cloud SQL Python Connector (`cloud-sql-python-connector[pg8000]`):

```python
import os

from google.cloud.sql.connector import Connector

connector = Connector()
conn = connector.connect(
    os.environ["CLOUDSQL_INSTANCE"],
    "pg8000",
    user=os.environ["DB_USER"],
    db=os.environ["DB_NAME"],
    enable_iam_auth=True,
)
```

Terminal or Django: run `cloud-sql-proxy --auto-iam-authn muzeum-w-autobusie-2026:europe-central2:muzeum`, then connect
to `127.0.0.1:5432`, database `muzeum`, user = your email, no password. For Django, set
`DATABASE_URL=postgres://you%40gmail.com@127.0.0.1:5432/muzeum` in `.env` (the `@` in the email becomes `%40`). With
`DATABASE_URL` empty, Django uses a local SQLite file.

### Downloading recordings and collected facts

```
gcloud storage cp -r gs://muzeum-w-autobusie-2026-audio .
gcloud storage rsync -r gs://muzeum-w-autobusie-2026-data/out out
gcloud storage rsync -r gs://muzeum-w-autobusie-2026-data/cache cache
```

## Writing data (writers)

- Create tables as the role `team`: run `SET ROLE team` right after connecting. Tables owned by `team` are readable by
  `readers` automatically; tables created under your own name are not.
- `gcloud storage cp clip.mp3 gs://muzeum-w-autobusie-2026-audio/<path>` uploads a recording. Overwriting an object
  keeps the old version; `gcloud storage ls -a gs://...` lists them.
- After a facts collector run, `gcloud storage rsync -r out gs://muzeum-w-autobusie-2026-data/out` and the same for
  `cache` publish the files the stories agent reads (see `collector/README.md`).
- `python manage.py publish_photos [--download] [--group 4001] [--dry-run]` puts the photos of every draft and verified
  story into the media bucket. For each photo it finds the collector file whose `url` equals the photo's `source_url`
  (`out/collected/<groupId>.json`), uploads it unmodified to `photos/<groupId>/<imageId>.jpg` and sets `src` to its
  public URL. `--download` first fetches `out/` from the data bucket. A story can be verified only after its photos
  are in the media bucket.

## Adding or removing people (owner)

- Readers: add or remove them in the Google Group. Nothing to run.
- Writers: edit `INFRA_MEMBERS` (Settings → Secrets and variables → Actions → Variables), then re-run the latest Infra
  workflow on `development`.

## One-time setup (already done)

```
gcloud projects create muzeum-w-autobusie-2026 --name="Słuchowisko"
gcloud billing projects link muzeum-w-autobusie-2026 --billing-account=<billing account>
gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com --project=muzeum-w-autobusie-2026
gcloud storage buckets create gs://muzeum-w-autobusie-2026-tfstate --project=muzeum-w-autobusie-2026 \
  --location=europe-central2 --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://muzeum-w-autobusie-2026-tfstate --versioning
terraform -chdir=infra/bootstrap init
terraform -chdir=infra/bootstrap apply
gh variable set INFRA_MEMBERS --body '["owner@example.com"]'
```

After that, the first merge touching `infra/` creates everything else.

## Cost and shutdown

Cloud SQL `db-f1-micro` costs about US$10 a month; storage is cents. After the hackathon:
`gcloud projects delete muzeum-w-autobusie-2026` removes everything.
