#!/bin/bash

# Repository configuration
REPO_NAME="nexusctl"
REPO_DIR="/var/www/html/repo"
DISTRIBUTIONS="jammy focal"  # Ubuntu versions to support

# Create repository structure
sudo mkdir -p $REPO_DIR/conf

# Create configuration
cat > $REPO_DIR/conf/distributions << EOF
Origin: Your Repository Name
Label: Your Repository
Codename: jammy
Architectures: amd64 source
Components: main
Description: Nexus Control System Repository
SignWith: your.email@example.com

Origin: Your Repository Name
Label: Your Repository
Codename: focal
Architectures: amd64 source
Components: main
Description: Nexus Control System Repository
SignWith: your.email@example.com
EOF

# Initialize repository
for dist in $DISTRIBUTIONS; do
    reprepro --basedir $REPO_DIR includedeb $dist nexusctl_1.0.0_amd64.deb
done

# Create repository signature
gpg --armor --export your.email@example.com > $REPO_DIR/repo.key 