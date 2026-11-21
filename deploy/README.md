# Deploying SchemeSaathi

Pipeline: `.github/workflows/ci-cd.yml`

| Trigger | What runs |
|---|---|
| Pull request | backend tests + frontend build |
| Push to `main` | the above, then build Docker image → push to `ghcr.io/<owner>/schemesaathi:<sha>` → SSH to the instance → `docker compose up -d` → wait for health check |

## One-time: the instance (EC2 / Lightsail, Ubuntu, region ap-south-1)

1. Security group / firewall: allow inbound **22** (your IP only), **80**, **443** (TCP + UDP).
2. Install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER   # log out and back in
   ```
3. Create a deploy key and authorise it:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/schemesaathi_deploy -N ""
   cat ~/.ssh/schemesaathi_deploy.pub >> ~/.ssh/authorized_keys
   cat ~/.ssh/schemesaathi_deploy      # copy this private key into the DEPLOY_SSH_KEY secret, then delete the file
   ```
4. (Optional) app secrets, e.g. the database URL later: create `~/schemesaathi/.env`
   ```
   DATABASE_URL=...
   ```
5. For HTTPS: point your domain's DNS **A record** at the instance's public IP (use an Elastic IP so it doesn't change).

## One-time: GitHub repo settings

Settings → Environments → **New environment `production`**, then add:

| Kind | Name | Value |
|---|---|---|
| Secret | `DEPLOY_HOST` | instance public IP or hostname |
| Secret | `DEPLOY_USER` | `ubuntu` (or your login user) |
| Secret | `DEPLOY_SSH_KEY` | private key from step 3 |
| Variable | `DOMAIN` | e.g. `schemesaathi.in` — leave unset to serve plain HTTP on port 80 |

Tip: in the `production` environment you can add *Required reviewers* so every deploy waits for a click.

## Rollback

Every build is tagged with its commit SHA. On the server:
```bash
cd ~/schemesaathi
IMAGE=ghcr.io/<owner>/schemesaathi:<old-sha> docker compose up -d
```
Or re-run an older successful workflow run's **deploy** job from the Actions tab.

## Run the production image locally
```bash
docker build -t schemesaathi .
docker run --rm -p 8000:8000 schemesaathi     # http://localhost:8000
```
