#!/usr/bin/env python3
from hcloud import Client
from hcloud.images.domain import Image
from hcloud.networks.domain import NetworkSubnet
from hcloud.locations.domain import Location
from hcloud.server_types.domain import ServerType
import sys

if(len(sys.argv) > 1):
    index = sys.argv[1]
else:
    index = "478874"

client = Client(
    token="KccUEiddxtzGoLWSNC3V8tylq7MYHCjdnShtgasQ8jSbHqCjGoaa6Rq7yoz4uS23"
)

servers = client.servers.get_all()
print(f"Deleting servers")
for s in servers:
    if s.data_model.name.startswith(index):
        action = client.servers.delete(s)
        action.wait_until_finished()
        print(f"\tDeleting servers {s.data_model.name} ({s.data_model.public_net.ipv4.ip}): {action.data_model.status}")

ssh_keys = client.ssh_keys.get_all()
print(f"Deleting SSH keys")
for s in ssh_keys:
    if s.data_model.name.startswith(index):
        action = client.ssh_keys.delete(s)
        print(f"\tDeleting keys {s.name}: {action}")

vnets = client.networks.get_all()
print(f"Deleting sub-networks")
for s in vnets:
    if s.data_model.name.startswith(index):
        action = client.networks.delete(s)
        print(f"\tDeleting networks {s.name}: {action}")

volumes = client.volumes.get_all()
print(f"Deleting volumes")
for v in volumes:
    if v.data_model.name.startswith(index):
        action = client.volumes.delete(v)
        print(f"\tDeleting volumes {v.name}: {action}")
