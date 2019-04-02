How to prepare the API Server
============================= Installation Steps

# Installation Steps

1. Install an Ubuntu 18.04 LTS VM with 1GB vRAM, 1 vCPU and a 16GB vHDD

2. Apply updates to the distro

3. Install Python, Python package manager and NGINX

4. Update Python package manager

5. Install virtualenv

6. Get the RESTful api Pyton code from repository

7. Create virtual environment

8. Install the required Python packages

9. Create entrypoint for our app in the wsgi app server config

10. Creating the configuration file for the app server

11. Create the configuration file which points to Redis and MySQL (use FQDN and passwords appropriate to your deployment)

12. Create a Systemd Unit that starts our App Server everytime the VM boots

13. Configure NGINX web to call the App Server for our API Service

14. Configure Ufw (IPTables) to allow web traffic ingress

# Installation Command Set

```shell
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get -y install python-pip python-dev nginx
sudo pip install --upgrade pip
sudo pip install virtualenv
git clone https://github.com/darrylcauldwell/planeSpotters.git
cd planeSpotters/
virtualenv api-server
cd api-server/
source bin/activate
cd app
pip install uwsgi Flask-Restless PyMySQL Flask-SQLAlchemy requests redis

cat << EOF > ~/planeSpotters/api-server/app/wsgi.py
from main import app

if __name__ == "__main__":
    app.run()
EOF

cat << EOF > ~/planeSpotters/api-server/app/app-server.ini
[uwsgi]
module = wsgi:app
master = true
processes = 5
socket = app-server.sock
chmod-socket = 660
vacuum = true
die-on-term = true
logto = /var/log/uwsgi/%n.log
EOF

cat << EOF > ~/planeSpotters/api-server/app/config/config.cfg
DATABASE_URL = 'planespotter-mysql.darrylcauldwell.com'
DATABASE_USER = 'planespotter'
DATABASE_PWD = 'VMware1!'
DATABASE = 'planespotter'
REDIS_HOST = 'planespotter-redis.darrylcauldwell.com'
REDIS_PORT = '6379'
LISTEN_PORT = '80'
EOF

sudo -H bash
mkdir -p /var/log/uwsgi
chown -R ubuntu:ubuntu /var/log/uwsgi

cat << EOF > /etc/systemd/system/app-server.service
[Unit]
Description=uWSGI instance to serve app-server
After=network.target
[Unit]
Description=uWSGI instance to serve app-server
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/planeSpotters/api-server/app
Environment="PATH=/home/ubuntu/planeSpotters/api-server/bin"
ExecStart=/home/ubuntu/planeSpotters/api-server/bin/uwsgi --ini app-server.ini
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl start app-server
systemctl enable app-server

cat << EOF > /etc/nginx/sites-enabled/default
server {
    listen 80;
    server_name default;
    location / {
        include uwsgi_params;
        uwsgi_pass unix:/home/ubuntu/planeSpotters/api-server/app/app-server.sock;
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
        - 172.16.1.1/24
      gateway4: 172.16.1.254
      nameservers:
          search: [darrylcauldwell.com]
          addresses: [192.168.1.10]
EOF'
sudo rm /etc/netplan/50-cloud-init.yaml
sudo netplan apply
sudo hostnamectl set-hostname planespotter-api.darrylcauldwell.com
```

## Test Connectivity

You can now test if you can retrieve data from the MySQL DB through the API Server:

```
curl http://planespotter-api.darrylcauldwell.com/api/healthcheck
curl http://planespotter-api.darrylcauldwell.com/api/planes
```