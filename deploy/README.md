# SautiYetu — VPS Deployment Guide

Assumes **Ubuntu 22.04 / 24.04**, **Nginx**, and a **single domain** serving both the
frontend and the API (`/api`). Replace the placeholders below.

Requirements: **Python 3.10+**, **~10 GB free disk** (the embedding model downloads
on first startup). 4 GB RAM is sufficient.

---

## 1. SSH in and install system packages

```bash
ssh root@<VPS_IP>

apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx git build-essential tesseract-ocr

# Node.js 22 (required to build the frontend — Vite 8 needs Node 20.19+/22)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
node -v
```

`tesseract-ocr` is required for OCR of scanned participation PDFs.

## 1b. Add swap (optional — cheap insurance against memory spikes)

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
```

## 2. Create a deploy user and project directory

```bash
adduser --disabled-password --gecos "" deploy
mkdir -p /home/deploy/sautiyetu/data
chown -R deploy:deploy /home/deploy/sautiyetu
```

## 3. Get the code onto the VPS

Either clone your repo, or copy the project up:

```bash
cd /home/deploy/sautiyetu
git clone <YOUR_REPO_URL> .
# OR from your local machine:
#   scp -r SautiYetu-Nancy_Stephen/* deploy@<VPS_IP>:/home/deploy/sautiyetu/
```

## 4. Backend setup

```bash
cd /home/deploy/sautiyetu/src/backend
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# create env from the template and edit it
cp ../../deploy/env.backend .env
nano .env     # set DEEPSEEK_API_KEY and your domain
```

The `.env` template already has correct Linux paths for SQLite and Qdrant.

## 5. Frontend build

```bash
cd /home/deploy/sautiyetu/src/frontend
npm install
npm run build        # reads src/frontend/.env.production (empty VITE_API_URL → relative /api)

mkdir -p /var/www/sautiyetu
cp -r dist/* /var/www/sautiyetu/
```

> Alternative: build locally (`npm run build`) and copy the `dist/` folder up with
> `scp -r dist deploy@<VPS_IP>:/var/www/sautiyetu/` — no Node needed on the VPS.

## 6. Nginx

```bash
cp /home/deploy/sautiyetu/deploy/nginx.conf /etc/nginx/sites-available/sautiyetu
nano /etc/nginx/sites-available/sautiyetu    # set your domain
ln -s /etc/nginx/sites-available/sautiyetu /etc/nginx/sites-enabled/sautiyetu
nginx -t
systemctl reload nginx
```

## 7. systemd service

```bash
cp /home/deploy/sautiyetu/deploy/sautiyetu.service /etc/systemd/system/sautiyetu.service
systemctl daemon-reload
systemctl enable --now sautiyetu
systemctl status sautiyetu
```

## 8. Verify

```bash
curl http://127.0.0.1:8000/api/health        # should return {"status":"ok",...}
curl http://<VPS_IP>/api/health              # via nginx
```

Then open `http://<VPS_IP>/` in a browser.

## 9. HTTPS (recommended)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d sautiyetu.example.com
```

## 10. First-run notes

- On first startup the backend **downloads the embedding model** (~500 MB) from
  Hugging Face — allow a few minutes and verify it stays running.
- Upload the **enacted budget** PDF first, wait for ingestion to show "complete",
  then upload participation data and match.
- The backend runs as a **single worker** (SQLite + local Qdrant lock + in-memory
  model). That is intentional — do not run multiple uvicorn workers.
