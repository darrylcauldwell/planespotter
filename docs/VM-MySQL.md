How to prepare the MySQL Database
=================================

# Installation Steps

1. Install an Ubuntu 18.04 VM with 1GB vRAM, 1 vCPU and a 16GB vHDD

2. Apply updates to the distro

3. Install mysql-server

4. Test if MySQL is running

5. Update MySQL binding from localhost only

6. Restart mysql with

7. Install unzip and git with 

8. Clone this repository to get database setup scripts

9. Change the two DB shell scripts to be executable

10. Set the evinronment variable for the MySQL root password you used earlier in step 3.

11. Execute the DB creation script

# Installation Command Set

``` bash
sudo apt-get update && sudo apt-get upgrade -y
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password password VMware1!'
sudo debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password VMware1!'
sudo apt-get -y install mysql-server
sudo systemctl status mysql.service
sudo sed -i "s/.*bind-address.*/bind-address = 0.0.0.0/" /etc/mysql/mysql.conf.d/mysqld.cnf
sudo systemctl restart mysql.service
sudo apt-get -y install unzip git
git clone https://github.com/darrylcauldwell/planeSpotters.git
chmod +x ~/planeSpotters/mysql/*.sh
export MYSQL_ROOT_PASSWORD=VMware1!
~/planeSpotters/mysql/create-planespotter-db.sh
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
        - 172.16.4.1/24
      gateway4: 172.16.4.254
      nameservers:
          search: [darrylcauldwell.com]
          addresses: [192.168.1.10]
EOF'
sudo rm /etc/netplan/50-cloud-init.yaml
sudo netplan apply
sudo hostnamectl set-hostname planespotter-mysql.darrylcauldwell.com
```