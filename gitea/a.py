from hcloud import Client
from hcloud.locations.domain import Location
from hcloud.images.domain import Image
from hcloud.server_types.domain import ServerType

import sys

if(len(sys.argv) > 1):
    hetz_token = sys.argv[1]
else:
    print("Hetzner token missing!")

if(len(sys.argv) > 2):
    ssh_public_key = " ".join([str(e) for e in sys.argv[2:5]])
else:
    print("SSH public key missing!")

if(len(sys.argv) > 5):
    index = sys.argv[5]
else:
    index = "478874"

client = Client(
    token=hetz_token
)

ssh_key_name = index+"-ssh-key"
network_name = index+"-subnet"
volume_name = index+"-vol"
db_name = index+"-db"
server_name = index+"-server"

try:
    ssh_key = client.ssh_keys.create(name=ssh_key_name, public_key=ssh_public_key)
except:
    ssh_key = client.ssh_keys.get_by_name(name=ssh_key_name)
print(f"SSH key {ssh_key.data_model.name} added: {ssh_key.data_model.public_key}")


from hcloud.networks.domain import NetworkSubnet

try:
    vnet = client.networks.create(
        name=network_name, 
        ip_range="10.10.10.0/24", 
        subnets=[
            NetworkSubnet(ip_range="10.10.10.0/24", network_zone="eu-central", type="cloud")
        ]
    )
    print(f"Created network: {vnet.data_model.name} ({vnet.data_model.ip_range})")
except:
    vnet = client.networks.get_by_name(
        network_name, 
    )
    print(f"Network in use: {vnet.data_model.name} ({vnet.data_model.ip_range})")




cloud_init_postgres=r'''#cloud-config
packages:
  - apt-transport-https
  - ca-certificates
  - curl
  - gnupg-agent
  - software-properties-common

write_files:
  - path: /root/docker-compose.yml
    content: |
        version: '3.9'

        services:
          db:
            image: postgres:14
            restart: always
            environment:
              POSTGRES_DATABASE: gitea
              POSTGRES_USER: gitea
              POSTGRES_PASSWORD: gitea
              POSTGRES_ROOT_PASSWORD: gitea
            ports:
              - "10.10.10.2:5432:5432"
            volumes:
              - my-db:/var/lib/postgres
        volumes:
          my-db: {}

runcmd:
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
  - add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  - apt-get update -y
  - apt-get install -y docker-ce docker-ce-cli containerd.io
  - curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  - chmod +x /usr/local/bin/docker-compose
  - systemctl start docker
  - systemctl enable docker
  - cd /root/ && docker-compose up -d
  '''

postgres_server = client.servers.create(
    name=db_name, 
    server_type=ServerType("cx11"), 
    image=Image(name="ubuntu-20.04"), 
    ssh_keys=[ssh_key], 
    networks=[vnet], 
    location=Location("hel1"), 
    user_data=cloud_init_postgres
)

postgres_server.action.wait_until_finished()
if(postgres_server.action.complete):
    print(f"Created db server: {postgres_server.server.name}")



cloud_init_gitea=r'''#cloud-config
packages:
  - apt-transport-https
  - ca-certificates
  - curl
  - gnupg-agent
  - software-properties-common

write_files:
  - path: /root/docker-compose.yml
    content: |
        version: "3"

        networks:
          gitea:
            external: false

        services:
          server:
            image: gitea/gitea:1.17.4
            container_name: gitea
            environment:
              - USER_UID=1000
              - USER_GID=1000
              - GITEA__server__DOMAIN=${DOMAIN}
              - GITEA__database__DB_TYPE=postgres
              - GITEA__database__HOST=10.10.10.2:5432
              - GITEA__database__NAME=gitea
              - GITEA__database__USER=gitea
              - GITEA__database__PASSWD=gitea
            restart: always
            networks:
              - gitea
            volumes:
              - ./data:/root/gitea
              - ./config:/root/gitea/config
              - /etc/timezone:/etc/timezone:ro
              - /etc/localtime:/etc/localtime:ro
              - /mnt/volume:/data
            ports:
              - "3000:3000"
              - "222:22"
'''
runcmd = f'''
runcmd:
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
  - add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  - apt-get update -y
  - apt-get install -y docker-ce docker-ce-cli containerd.io
  - curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  - chmod +x /usr/local/bin/docker-compose
  - systemctl start docker
  - systemctl enable docker
  - cd /root/
  - IP=$(hostname -I | cut -d ' ' -f 1)
  - echo "DOMAIN=$IP" >> .env
  - docker-compose up -d
'''

cloud_init_gitea += runcmd

gitea_server = client.servers.create(
    name=server_name, 
    server_type=ServerType("cx11"), 
    image=Image(name="ubuntu-20.04"), 
    ssh_keys=[ssh_key], 
    networks=[vnet], 
    location=Location("hel1"), 
    user_data=cloud_init_gitea
)

gitea_server.action.wait_until_finished()
if(gitea_server.action.complete):
    print(f"Created gitea server: {gitea_server.server.name}")

print(f"Gitea up -> http://{gitea_server.server.data_model.public_net.ipv4.ip}:3000")