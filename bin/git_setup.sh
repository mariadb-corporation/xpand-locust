#!/bin/bash


sudo yum -y remove git-*
sudo yum -y install https://packages.endpoint.com/rhel/7/os/x86_64/endpoint-repo-1.9-1.x86_64.rpm

sudo yum -y install git

echo "Done with git"
