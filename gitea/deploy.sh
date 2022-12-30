#!/bin/bash
echo "Initiating gitea cloud deploy ..."
python3 a.py $(cat token_file.txt) $(find ~ -name *.pub | tail -n 1 | xargs cat) "478874"