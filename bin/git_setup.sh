#!/bin/bash

# TODO
# Check this page for other distributions: https://git-scm.com/download/linux

OS_NAME=$(grep ^NAME /etc/os-release | awk -F= '{ print $2 } ' | tr -d \")
VERSION_ID=$(grep VERSION_ID /etc/os-release | awk -F= '{ print $2 }' | tr -d \")

if [[ ${OS_NAME} == "CentOS Linux" ]]; then
    package_manager="sudo yum -y install"
    epel="sudo yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-${VERSION_ID}.noarch.rpm"
elif [[ ${OS_NAME} == "Amazon Linux" ]]; then
    epel="sudo amazon-linux-extras install epel"
    package_manager="sudo yum -y install"
else
    echo "Unsupported OS"
    exit 1
fi

package="git"
${epel_manager}
${package_manager} ${package}

echo "Done with git"
