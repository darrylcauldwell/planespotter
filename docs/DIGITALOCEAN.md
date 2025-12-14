# Deploying Planespotter on Digital Ocean

This guide covers deploying Planespotter on a Digital Ocean Droplet using Docker Compose.

## Prerequisites

- Digital Ocean account
- SSH key added to your DO account
- Domain name (optional, for HTTPS)

## Droplet Specification

### Recommended Sizes

| Use Case | Droplet | RAM | vCPU | Disk | Cost |
|----------|---------|-----|------|------|------|
| Demo/Testing | Basic | 1GB | 1 | 25GB | ~$6/mo |
| **Personal Use** | **Basic** | **2GB** | **1** | **50GB** | **~$12/mo** |
| Production | Basic | 4GB | 2 | 80GB | ~$24/mo |

**Recommendation:** Start with the 2GB droplet ($12/mo) for reliable operation.

### Configuration

- **Image:** Ubuntu 24.04 LTS
- **Region:** Choose closest to your users
- **VPC:** Default
- **Authentication:** SSH Key (recommended) or Password
- **Hostname:** `planespotter` (or your preference)

## Quick Setup

### Option 1: One-Command Setup

SSH into your droplet and run:

```bash
curl -fsSL https://raw.githubusercontent.com/darrylcauldwell/planespotter/master/scripts/setup-droplet.sh | sudo bash
```

This will:
- Install Docker
- Download the docker-compose configuration
- Pull and start all containers
- Display access URLs

### Option 2: Manual Setup

#### 1. Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add your user to docker group (optional, avoids using sudo)
sudo usermod -aG docker $USER

# Start Docker on boot
sudo systemctl enable docker
```

#### 2. Create Application Directory

```bash
sudo mkdir -p /opt/planespotter
cd /opt/planespotter
```

#### 3. Download Docker Compose File

```bash
sudo curl -fsSL -o docker-compose.yaml \
  https://raw.githubusercontent.com/darrylcauldwell/planespotter/master/docker-compose.ghcr.yaml
```

#### 4. Configure Environment (Optional)

Create a `.env` file for custom settings:

```bash
sudo tee .env << 'EOF'
POSTGRES_PASSWORD=your-secure-password-here
LOG_LEVEL=INFO
EOF
```

#### 5. Start the Application

```bash
sudo docker compose pull
sudo docker compose up -d
```

#### 6. Verify Deployment

```bash
# Check container status
sudo docker compose ps

# Check logs
sudo docker compose logs -f

# Test endpoints
curl http://localhost:8080/healthz
curl http://localhost:8000/health
```

## Firewall Configuration

Digital Ocean Droplets have no firewall by default. Configure UFW:

```bash
# Enable UFW
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Verify
sudo ufw status
```

**Note:** Only ports 80 and 443 are exposed. The API (8000), database (5432), and cache (6379) remain internal.

## Exposing to the Public

### Option 1: Direct IP Access (Quick Start)

Access via your Droplet's public IP:
- Frontend: `http://YOUR_DROPLET_IP:8080`
- API Docs: `http://YOUR_DROPLET_IP:8000/docs`

To allow port 8080:
```bash
sudo ufw allow 8080/tcp
```

### Option 2: Nginx Reverse Proxy (Recommended)

Install Nginx to proxy port 80 to the frontend:

```bash
# Install Nginx
sudo apt install -y nginx

# Create configuration
sudo tee /etc/nginx/sites-available/planespotter << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/planespotter /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

Access via: `http://YOUR_DROPLET_IP`

### Option 3: HTTPS with Let's Encrypt (Production)

Requires a domain name pointed to your Droplet IP.

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Update Nginx config with your domain
sudo sed -i 's/server_name _;/server_name yourdomain.com;/' /etc/nginx/sites-available/planespotter
sudo systemctl reload nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

## Management Commands

```bash
cd /opt/planespotter

# View status
sudo docker compose ps

# View logs
sudo docker compose logs -f              # All services
sudo docker compose logs -f frontend     # Specific service

# Restart services
sudo docker compose restart

# Stop services
sudo docker compose down

# Update to latest images
sudo docker compose pull
sudo docker compose up -d

# View resource usage
sudo docker stats
```

## Updating the Application

When new versions are released:

```bash
cd /opt/planespotter

# Pull latest images
sudo docker compose pull

# Restart with new images
sudo docker compose up -d

# Verify
sudo docker compose ps
```

## Backup & Restore

### Backup Database

```bash
cd /opt/planespotter

# Create backup
sudo docker compose exec postgres pg_dump -U postgres postgres > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Restore from backup
cat backup_20241215.sql | sudo docker compose exec -T postgres psql -U postgres postgres
```

## Monitoring

### Basic Health Checks

```bash
# Check if services are responding
curl -s http://localhost:8080/healthz | jq .
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/health/ready | jq .
```

### Resource Monitoring

```bash
# Real-time container stats
sudo docker stats

# Disk usage
df -h
sudo docker system df
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs
sudo docker compose logs postgres
sudo docker compose logs api-server

# Check container status
sudo docker compose ps -a
```

### Out of Memory

If containers are being killed:

```bash
# Check memory usage
free -h

# Consider upgrading droplet or adding swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Database Connection Issues

```bash
# Check if postgres is healthy
sudo docker compose exec postgres pg_isready

# Check postgres logs
sudo docker compose logs postgres
```

### Clean Up Disk Space

```bash
# Remove unused Docker data
sudo docker system prune -a

# Remove old logs
sudo truncate -s 0 /var/log/*.log
```

## Security Recommendations

1. **Change default password:** Set `POSTGRES_PASSWORD` in `.env`
2. **Enable firewall:** Only expose necessary ports (80, 443, 22)
3. **Keep updated:** Regularly update OS and Docker images
4. **Use SSH keys:** Disable password authentication
5. **Enable backups:** Use DO's backup feature or manual backups

## Cost Summary

| Component | Cost |
|-----------|------|
| Droplet (2GB) | $12/mo |
| Backups (optional) | +$2.40/mo |
| Reserved IP (optional) | Free while attached |
| **Total** | **~$12-15/mo** |

## Architecture on Digital Ocean

```
┌─────────────────────────────────────────────────────────┐
│                    Digital Ocean                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Droplet (Ubuntu 24.04)               │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │              Docker Compose                 │  │  │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │  │  │
│  │  │  │Frontend │ │   API   │ │  ADSB   │       │  │  │
│  │  │  │  :8080  │ │  :8000  │ │  Sync   │       │  │  │
│  │  │  └────┬────┘ └────┬────┘ └────┬────┘       │  │  │
│  │  │       │           │           │            │  │  │
│  │  │  ┌────┴───────────┴───────────┴────┐       │  │  │
│  │  │  │           Internal Network       │       │  │  │
│  │  │  └────┬───────────────────────┬────┘       │  │  │
│  │  │  ┌────┴────┐           ┌──────┴─────┐      │  │  │
│  │  │  │Postgres │           │   Valkey   │      │  │  │
│  │  │  │  :5432  │           │   :6379    │      │  │  │
│  │  │  └─────────┘           └────────────┘      │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                      │                            │  │
│  │               ┌──────┴──────┐                     │  │
│  │               │    Nginx    │ (optional)          │  │
│  │               │    :80/:443 │                     │  │
│  │               └──────┬──────┘                     │  │
│  └──────────────────────┼────────────────────────────┘  │
│                         │                               │
│  ┌──────────────────────┼────────────────────────────┐  │
│  │     DO Firewall      │                            │  │
│  │     (22, 80, 443)    │                            │  │
│  └──────────────────────┼────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────┘
                          │
                      Internet
```
