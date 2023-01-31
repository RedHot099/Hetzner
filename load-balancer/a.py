from hcloud import Client
from hcloud.locations.domain import Location
from hcloud.images.domain import Image
from hcloud.server_types.domain import ServerType
from hcloud.networks.domain import NetworkSubnet
from hcloud.load_balancer_types.domain import LoadBalancerType
from hcloud.load_balancers.domain import (
    LoadBalancerService, 
    LoadBalancerServiceHttp, 
    LoadBalancerHealthCheck, 
    LoadBalancerHealtCheckHttp,
    LoadBalancerTarget
)

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
server1_name = index+"-lb-server1"
server2_name = index+"-lb-server2"
lb_name = index+"-lb"

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


cloud_init = r'''#cloud-config
packages:
  - apt-transport-https
  - ca-certificates
  - curl
  - gnupg-agent
  - software-properties-common
      
runcmd:
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
  - add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  - apt-get update -y
  - apt-get install -y docker-ce docker-ce-cli containerd.io
  - curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  - chmod +x /usr/local/bin/docker-compose
  - systemctl start docker
  - systemctl enable docker
  - git clone https://git.wmi.amu.edu.pl/bikol/DPZC-2022-23.git
  - cd 04_Public_cloud/zadania
  - chmod +x ./webservice
  - ./webservice
'''



server1 = client.servers.create(
    name=server1_name, 
    server_type=ServerType('cx11'), 
    image=Image(name='ubuntu-20.04'), 
    ssh_keys=[ssh_key], 
    networks=[vnet], 
    location=Location('hel1'),  
    user_data=cloud_init
)

server1.action.wait_until_finished()
if(server1.action.complete):
    print(f"Created first server: {server1.server.name}")
server1 = client.servers.get_by_name(server1_name)

server2 = client.servers.create(
    name=server2_name, 
    server_type=ServerType('cx11'), 
    image=Image(name='ubuntu-20.04'), 
    ssh_keys=[ssh_key], 
    networks=[vnet], 
    location=Location('hel1'),  
    user_data=cloud_init
)

server2.action.wait_until_finished()
if(server2.action.complete):
    print(f"Created second server: {server2.server.name}")
server2 = client.servers.get_by_name(server2_name)

load_balancer = client.load_balancers.create(
    name=lb_name,
    load_balancer_type=LoadBalancerType(name='lb11'),
    location=Location('hel1'),
    network=vnet,
    targets=[
        LoadBalancerTarget(
            type='server',
            server=server1,
            use_private_ip=True,
        ),
        LoadBalancerTarget(
            type='server',
            server=server2,
            use_private_ip=True,
        )
    ],
    services=[
        LoadBalancerService(
            protocol='http',
            listen_port=80,
            destination_port=80,
            health_check=LoadBalancerHealthCheck(
                protocol='http',
                port=80,
                interval=15,
                timeout=10,
                retries=3,
                http=LoadBalancerHealtCheckHttp(
                    path='/factors/10',
                    status_codes=['2??', '3??'],
                    tls=False,
                )
            ),
            http=LoadBalancerServiceHttp(
                cookie_name='HCLBSTICKY',
                cookie_lifetime=300,
                sticky_sessions=True,
                certificates=[],
            ),
        )
    ]
)


load_balancer.action.wait_until_finished()
if(load_balancer.action.complete):
    print(f"Load balancer completed: {load_balancer.load_balancer.name}")

print(f"Load balancer up -> http://{load_balancer.load_balancer.public_net.ipv4.ip}:80/factors/10")