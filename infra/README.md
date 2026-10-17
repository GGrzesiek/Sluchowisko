# Infrastructure (GCP)

A shared database and recordings store for the team during development, so nobody works from a stale local copy.
The app never talks to GCP. It still reads only static files (see `AGENTS.md`).

| What                      | Where                                                      |
| ------------------------- | ---------------------------------------------------------- |
| Project                   | `muzeum-w-autobusie-2026`, region `europe-central2`        |
| PostgreSQL 16 (Cloud SQL) | instance `muzeum`, database `muzeum`, IAM login only       |
| ElevenLabs recordings     | bucket `muzeum-w-autobusie-2026-audio`, private, versioned |
| Terraform state           | bucket `muzeum-w-autobusie-2026-tfstate`                   |
| Owner and billing         | Grzesiek (#5)                                              |

There are no passwords or key files anywhere. People sign in with their Google account, GitHub Actions with
Workload Identity Federation.

## How changes reach GCP

| Directory         | Applied by                            | Contains                                                   |
| ----------------- | ------------------------------------- | ---------------------------------------------------------- |
| `infra/bootstrap` | the owner, locally, rarely            | APIs, GitHub identity pool, `tf-plan` and `tf-apply`       |
| `infra`           | `.github/workflows/infra.yml` (CI/CD) | database, bucket, members' access, `team` role in Postgres |

- Pull request touching `infra/**`: CI runs `terraform plan` as `tf-plan` (read-only) and shows it in the job summary.
- Merge into `development`: CD runs `terraform apply` as `tf-apply`, then `database.sql` and the member grants.
  Only pushes to `development` can act as `tf-apply`, and `development` accepts reviewed PRs only.

Team emails live in the GitHub repository variable `INFRA_MEMBERS` (a JSON list), not in the repo.

## Getting access (teammates)

1. Send Grzesiek the Google account email you want to use.
2. Once it is in `INFRA_MEMBERS` and CD has run, sign in:
   ```
   gcloud auth login
   gcloud auth application-default login
   gcloud auth application-default set-quota-project muzeum-w-autobusie-2026
   ```
3. Copy the GCP lines from `.env.example` to `.env` and set `DB_USER` to your email.

### Connecting

Create tables as the shared role `team`, so everyone can read and change them. Add `-c role=team` to the connection
options.

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
conn.cursor().execute("SET ROLE team")
```

Terminal or Django: run `cloud-sql-proxy --auto-iam-authn muzeum-w-autobusie-2026:europe-central2:muzeum`, then connect
to `127.0.0.1:5432`, database `muzeum`, user = your email, no password, `options=-c role=team`. For Django, set
`DATABASE_URL=postgres://you%40gmail.com@127.0.0.1:5432/muzeum` in `.env` (the `@` in the email becomes `%40`). With
`DATABASE_URL` empty, Django uses a local SQLite file.

### Uploading recordings

```
gcloud storage cp clip.mp3 gs://muzeum-w-autobusie-2026-audio/<path>
```

Overwriting an object keeps the old version. `gcloud storage ls -a gs://...` lists them.

## Adding or removing a member (owner)

Edit `INFRA_MEMBERS` (Settings → Secrets and variables → Actions → Variables), then re-run the latest Infra workflow
on `development`, or merge any PR touching `infra/`. Removing an email removes that person's GCP access and Cloud SQL
user.

## One-time setup (already done)

```
gcloud projects create muzeum-w-autobusie-2026 --name="Muzeum w autobusie"
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
