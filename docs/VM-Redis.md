
How to prepare the Frontend
===========================

# Installation Steps

1. Install an Ubuntu 18.04 VM with 1GB vRAM, 1 vCPU and a 16GB vHDD

2. Apply updates to the distro

3. Install Redis from source

4. Configure Redis

5. Create a Systemd Unit that starts our App Server everytime the VM boots

# Installation Command Set

```shell
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get -y install build-essential tcl
cd /tmp
curl -O http://download.redis.io/redis-stable.tar.gz
tar xzvf redis-stable.tar.gz
cd redis-stable
make
make test
sudo make install
sudo mkdir /etc/redis
sudo cp /tmp/redis-stable/redis.conf /etc/redis
sudo sed -i 's/^supervised no/supervised systemd/' /etc/redis/redis.conf
sudo sed -i 's,^dir ./,dir /var/lib/redis,' /etc/redis/redis.conf
sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf
sudo sed -i 's/^bind 127.0.0.1/#bind 127.0.0.1/' /etc/redis/redis.conf
sudo -H bash

cat << EOF > /etc/systemd/system/redis.service
[Unit]
Description=Redis In-Memory Data Store
After=network.target

[Service]
User=redis
Group=redis
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf
ExecStop=/usr/local/bin/redis-cli shutdown
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

adduser --system --group --no-create-home redis
mkdir /var/lib/redis
chown redis:redis /var/lib/redis
chmod 770 /var/lib/redis

sudo systemctl start redis
sudo systemctl enable redis
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
        - 172.16.3.1/24
      gateway4: 172.16.3.254
      nameservers:
          search: [darrylcauldwell.com]
          addresses: [192.168.1.10]
EOF'
sudo rm /etc/netplan/50-cloud-init.yaml
sudo netplan apply
sudo hostnamectl set-hostname planespotter-redis.darrylcauldwell.com
```

## Test Connectivity

Now test if redis is ready using the CLI and enter `ping`

```shell
redis-cli
127.0.0.1:6379> ping
```