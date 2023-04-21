#!/bin/bash

sudo yum -y update 
sudo yum -y install docker 

docker run --name nfwordpress --network nfdockernetwork -d wordpress


