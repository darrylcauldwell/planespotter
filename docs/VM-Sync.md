How to prepare the Frontend
===========================

# Installation Steps

1. Install an Ubuntu 18.04 VM with 1GB vRAM, 1 vCPU and a 16GB vHDD

2. Apply updates to the distro

3. Install Python and Python package manager

4. Update Python package manager

5. Install virtualenv

6. Get the frontend Pyton code from repository

7. Create virtual environment

8. Install the required Python packages

9. Creating the configuration file for the adsb sync server (use FQDN appropriate to your redis server)

10. Create a Systemd Unit that starts our adsb sync server everytime the VM boots

# Installation Command Set

```shell
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get -y install python-pip python-dev
sudo pip install --upgrade pip
sudo pip install virtualenv
cd /home/ubuntu
git clone https://github.com/darrylcauldwell/planeSpotters.git
cd planeSpotters/
virtualenv adsb-sync
cd adsb-sync/
source bin/activate
pip install -r requirements.txt

cat << EOF > /home/ubuntu/planeSpotters/adsb-sync/synchronizer/config/config.ini
[main]
redis_server = planespotter-redis.darrylcauldwell.com
adsb_server_stream = pub-vrs.adsbexchange.com
adsb_port = 32030
adsb_server_poll_url = https://public-api.adsbexchange.com/VirtualRadar/AircraftList.json
adsb_poll_filter = ?fRegS=N
adsb_type = poll
EOF

sudo -H bash
cat << EOF > /etc/systemd/system/adsb-sync.service
[Unit]
Description=adsb-sync
After=network.target
[Unit]
Description=adsb-sync
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/planeSpotters/adsb-sync/synchronizer
Environment="PATH=/home/ubuntu/planeSpotters/adsb-sync/bin"
ExecStart=/home/ubuntu/planeSpotters/adsb-sync/bin/python -u adsb-sync.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl start adsb-sync
systemctl enable adsb-sync
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
        - 172.16.2.1/24
      gateway4: 172.16.2.254
      nameservers:
          search: [darrylcauldwell.com]
          addresses: [192.168.1.10]
EOF'
sudo rm /etc/netplan/50-cloud-init.yaml
sudo netplan apply
sudo hostnamectl set-hostname planespotter-sync.darrylcauldwell.com
```