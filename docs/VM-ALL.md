Deployment as VMs
=================
Follow the bellow instructions if you want to deploy all Planespotter components on VMs. Make sure that the VMs are resolvable through DNS, in this documentation I refer to the fqdn I use, exchange these with your domain and desired hostnames.

# Create the MySQL Database Server
Install MySQL and create the Planespotter Database using the instruction in [VM-MySQL.md](VM-MySQL.md)

# Create the API App Server
Install the Planespotter App Server using the instructions in [VM-API.md](VM-API.md)

# Create the Frontend Server
Install the Planespotter Frontend Server using the instructions in [VM-FE.md](VM-FE.md)

# Create the Redis Server
Install the Redis Server using the instructions in [VM-Redis.md](VM-Redis.md)

# Create the ADSB Sync Server
Install the ASDB Sync Service using the instruction in [VM-Sync.md](VM-Sync.md)