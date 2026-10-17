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

| Directory         | Applied by                            | Contains                                                         |
| ----------------- | ------------------------------------- | ---------------------------------------------------------------- |
| `infra/bootstrap` | the owner, locally, rarely            | APIs, GitHub identity pool, `tf-plan` and `tf-apply`             |
| `infra`           | `.github/workflows/infra.yml` (CI/CD) | database, bucket, access, `team` and `readers` roles in Postgres |

- Pull request touching `infra/**`: CI runs `terraform plan` as `tf-plan` (read-only) and shows it in the job summary.
- Merge into `development`: CD runs `terraform apply` as `tf-apply`, then `database.sql` and the writer grants.
  Only pushes to `development` can act as `tf-apply`, and `development` accepts reviewed PRs only.

## Who can do what

| Who                                                              | Database                       | Recordings bucket |
| ---------------------------------------------------------------- | ------------------------------ | ----------------- |
| Writers: emails in the repo variable `INFRA_MEMBERS`             | read and write, as role `team` | read and write    |
| Team: members of the Google Group `sluchowisko@googlegroups.com` | read only, as role `readers`   | read only         |

Data reaches GCP only through the writers. Everyone else reads the same copy.

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

### Downloading recordings

```
gcloud storage cp -r gs://muzeum-w-autobusie-2026-audio .
```

## Writing data (writers)

- Create tables as the role `team`: run `SET ROLE team` right after connecting. Tables owned by `team` are readable by
  `readers` automatically; tables created under your own name are not.
- `gcloud storage cp clip.mp3 gs://muzeum-w-autobusie-2026-audio/<path>` uploads a recording. Overwriting an object
  keeps the old version; `gcloud storage ls -a gs://...` lists them.

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
