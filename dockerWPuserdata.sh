#!/bin/bash
set -x

sudo yum -y update
sudo yum -y install docker
sudo systemctl start docker
sudo systemctl enable docker
#sudo systemctl status docker
sudo usermod -aG docker ec2-user
sudo docker network create nfdockernetwork
sudo docker run --name nfwordpress --network nfdockernetwork -d -p 80:80 wordpress