#!/bin/bash
echo "Creating virtual enviroment ..."
python3 -m venv hetz_gitea_venv 
echo "Installing dependencies ..."
pip install -q hcloud
echo "Initiating load balancer cloud deploy ..."
chmod +x a.py
python3 a.py $(cat ../token_file.txt) $(find ~ -name *.pub | tail -n 1 | xargs cat) "478874"