How to prepare the Frontend
===========================

# Installation Steps

1. Install an Ubuntu 18.04 VM with 1GB vRAM, 1 vCPU and a 16GB vHDD

2. Apply updates to the distro

3. Install Python, Python package manager and NGINX

4. Update Python package manager

5. Install virtualenv

6. Get the frontend Pyton code from repository

7. Create virtual environment

8. Install the required Python packages

9. Create entrypoint for our app in the wsgi app server config

10. Creating the configuration file for the app server (use FQDN appropriate to your RESTful API deployment)

11. Create a Systemd Unit that starts our App Server everytime the VM boots

12. Configure NGINX web to call the App Server for our API Service

13. Configure Ufw (IPTables) to allow web traffic ingress

# Installation Command Set

```shell
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get -y install python-pip python-dev nginx
sudo pip install --upgrade pip
sudo pip install virtualenv
git clone https://github.com/darrylcauldwell/planespotter.git
cd planespotter/
virtualenv frontend
cd frontend/
source bin/activate
cd app
pip install -r requirements.txt
pip install uwsgi

cat << EOF > /home/ubuntu/planespotter/frontend/app/wsgi.py
from main import app

if __name__ == "__main__":
    app.run()
EOF

cat << EOF > /home/ubuntu/planespotter/frontend/app/frontend.ini
[uwsgi]
module = wsgi:app
master = true
processes = 5
socket = frontend.sock
chmod-socket = 660
vacuum = true
die-on-term = true
logto = /var/log/uwsgi/%n.log
env = PLANESPOTTER_API_ENDPOINT=planespotter-api.darrylcauldwell.com
# env = TIMEOUT_REG=5
# env = TIMEOUT_OTHER=5
EOF

sudo -H bash
mkdir -p /var/log/uwsgi
chown -R ubuntu:ubuntu /var/log/uwsgi

cat << EOF > /etc/systemd/system/frontend.service
[Unit]
Description=uWSGI instance to serve frontend
After=network.target
[Unit]
Description=uWSGI instance to serve frontend
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/planespotter/frontend/app
Environment="PATH=/home/ubuntu/planespotter/frontend/bin;PLANESPOTTER_API_ENDPOINT=planespotter-api"
ExecStart=/home/ubuntu/planespotter/frontend/bin/uwsgi --ini frontend.ini
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl start frontend
systemctl enable frontend

cat << EOF > /etc/nginx/sites-enabled/default
server {
    listen 80;
    server_name default;
    location / {
        include uwsgi_params;
        uwsgi_pass unix:/home/ubuntu/planespotter/frontend/app/frontend.sock;
    }
}
EOF

systemctl restart nginx

ufw allow 'Nginx Full'
```

# NSX-T Lab Networking Setup

``` bash
sudo bash -c 'cat << EOF > /etc/netplan/99_config.yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    ens160:
      addresses:
        - 172.16.0.1/24
      gateway4: 172.16.0.254
      nameservers:
          search: [darrylcauldwell.com]
          addresses: [192.168.1.10]
EOF'
sudo rm /etc/netplan/50-cloud-init.yaml
sudo netplan apply
sudo hostnamectl set-hostname planespotter.darrylcauldwell.com
```

## Test Connectivity

You can now test if you can browse to the FE which will connect to RESTful API and retrieve data from the MySQL DB.