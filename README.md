# mindmap-geo-v2

Co-Authors: [Gene Rhim](https://www.linkedin.com/in/generhim) (a.k.a. [pasadena.ai](https://www.github.com/pasadenaai)), & Claude Code. 

Description: An interactive 3D globe for exploring countries, natural resources and cloud regions. Type to search, and the globe turns to the country you asked for. Built with React, Vite and Three.js on the front end and FastAPI and DynamoDB on the back end, and deployed serverless on AWS (S3 static frontend + API Gateway → Lambda (FastAPI) → DynamoDB; no ECS/Fargate). Intended to integrate into mindmap-app-v3. This repo is the clean successor to `mindmap-geo` (see `CHANGELOG.md`).

<img src="./images/mindmap-geo-v2-globe.png" alt="Interactive Mindmap-Geo Globe" width="500">

## Objective
To create a visual "delimiter" by constraining information into an interactive 3D Globe. 

### Search
Start typing anywhere and a search bar opens. Country names, codes and common aliases resolve locally. Anything the local matcher can't resolve goes to an Anthropic-powered assistant (FastAPI on Lambda behind API Gateway), and its answer is validated against the country table before the globe moves. <br/>
<img src="./images/mindmap-geo-v2-searchbox.png" alt="Search Box triggered by keystrokes" width="500">

Any search that can be achieved will turn the globe. <br/>
<img src="./images/mindmap-geo-v2-china.png" alt="Search Box triggered by keystrokes" width="500">

## Top Menu
### Countries
<img src="./images/mindmap-geo-v2-topmenu-countries.png" alt="Map Top Menu - Countries" width="300">

### Natural Resources
<img src="./images/mindmap-geo-v2-topmenu-resources.png" alt="Map Settings Menu" width="300">
<img src="./images/mindmap-geo-v2-topmenu-periodic-table.png" alt="Periodic Table" width="500">


## Bottom Menu - Map Settings
<img src="./images/mindmap-geo-v2-map-settings.png" alt="Map Settings Menu" width="200">
<img src="./images/mindmap-geo-v2-bottommenu-map-settings.png" alt="Map Settings Applied" width="500">



## Quick start (local)

```bash
scripts/dev_env_init.sh   # one-time: generates a git-ignored .env.local with random secrets
docker compose --env-file .env.local -f docker-compose.local.yaml up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:4203 |
| Backend | http://localhost:8004 |
| API docs | http://localhost:8004/docs |
| DynamoDB Admin | http://localhost:8005 |

Local DynamoDB data is persisted in `./geo_localstack_data/` and survives `docker compose down`.
To wipe: `rm -rf geo_localstack_data/state/`

## Data sync (local ↔ AWS)

Requires AWS credentials in environment or `~/.aws/credentials` with the `pai-geo-seed` IAM policy.

```bash
# Push all tables from local → AWS
python scripts/sync_to_aws.py

# Push specific tables only
python scripts/sync_to_aws.py --tables geo_countries geo_elements geo_country_elements

# Pull from AWS → local (debug with prod data)
python scripts/sync_to_aws.py --direction aws-to-local

# Dry run — print item counts without writing anything
python scripts/sync_to_aws.py --dry-run
```

## AWS deployment

URLs (from the CDK stack outputs — account and API IDs are not stored in this repo):

| Resource | URL |
|---|---|
| Site | https://exploror.labs.pasadena.ai/ |
| API | https://exploror.labs.pasadena.ai/api/ (same origin) |

See `CLAUDE.md` for full deploy and update commands, and `ENV.md` for how secrets are handled.
