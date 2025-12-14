#!/bin/bash
#
# Planespotter - Digital Ocean Droplet Setup Script
# Run as root or with sudo on a fresh Ubuntu 22.04/24.04 Droplet
#
set -e

REPO_URL="https://raw.githubusercontent.com/darrylcauldwell/planespotter/master"
INSTALL_DIR="/opt/planespotter"

echo "=== Planespotter Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./setup-droplet.sh)"
    exit 1
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker installed."
else
    echo "Docker already installed."
fi

# Create install directory
echo "Creating install directory..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download docker-compose file
echo "Downloading docker-compose configuration..."
curl -fsSL -o docker-compose.yaml "$REPO_URL/docker-compose.ghcr.yaml"

# Create .env file for any customizations
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# Planespotter Configuration
# Uncomment and modify as needed

# POSTGRES_PASSWORD=your-secure-password
# LOG_LEVEL=INFO
EOF
    echo "Created .env file for configuration."
fi

# Pull images
echo "Pulling container images (this may take a few minutes)..."
docker compose pull

# Start services
echo "Starting services..."
docker compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check status
echo ""
echo "=== Service Status ==="
docker compose ps

# Get droplet IP
DROPLET_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Planespotter is now running!"
echo ""
echo "Access the application at: http://${DROPLET_IP}:8080"
echo "API documentation at:      http://${DROPLET_IP}:8000/docs"
echo ""
echo "Useful commands:"
echo "  cd $INSTALL_DIR"
echo "  docker compose logs -f      # View logs"
echo "  docker compose ps           # Check status"
echo "  docker compose down         # Stop services"
echo "  docker compose pull && docker compose up -d  # Update to latest"
echo ""
