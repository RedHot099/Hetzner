from hcloud import Client
from hcloud.locations.domain import Location
from hcloud.images.domain import Image
from hcloud.server_types.domain import ServerType
from hcloud.networks.domain import NetworkSubnet

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



cloud_init_server=r"""#cloud-config
packages:
  - apt-transport-https
  - ca-certificates
  - curl
  - gnupg-agent
  - software-properties-common
write_files:
  - path: /root/docker-compose.yml
    content: |
      version: "2.1"
      services:
        code-server:
          image: lscr.io/linuxserver/code-server:latest
          container_name: code-server
          environment:
            - PUID=1000
            - PGID=1000
            - TZ=Europe/London
            - SUDO_PASSWORD=123
          volumes:
            - /path/to/appdata/config:/config
          ports:
            - 8443:8443
          restart: unless-stopped
runcmd:
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
  - add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  - apt-get update -y
  - apt-get install -y docker-ce docker-ce-cli containerd.io
  - apt-get install -y python3 python3-pip
  - curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  - chmod +x /usr/local/bin/docker-compose
  - systemctl start docker
  - systemctl enable docker
  - cd /root/ && docker-compose up -d
"""

volume = client.volumes.create(
  name=volume_name,
  size=10,
  format="ext4",
  location=Location("hel1")
)

if(volume.action.complete):
    print(f"Created volume: {volume.volume.name}")

code_server = client.servers.create(
    name=server_name, 
    server_type=ServerType("cx11"), 
    image=Image(name="ubuntu-22.04"), 
    ssh_keys=[ssh_key], 
    networks=[vnet], 
    volumes= [volume.volume],
    automount=True,
    location=Location("hel1"), 
    user_data=cloud_init_server
)

code_server.action.wait_until_finished()
if(code_server.action.complete):
    print(f"Created code server: {code_server.server.name}")

print(f"Code server up -> http://{code_server.server.data_model.public_net.ipv4.ip}:8443")