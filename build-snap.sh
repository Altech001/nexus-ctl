#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Error handling
set -euo pipefail
trap 'handle_error $? $LINENO' ERR

handle_error() {
    echo -e "${RED}Error occurred in build script at line $2${NC}"
    case $1 in
        1) echo "General error" ;;
        2) echo "Missing dependency" ;;
        126) echo "Permission error" ;;
        127) echo "Command not found" ;;
        *) echo "Unknown error code: $1" ;;
    esac
    exit $1
}

# Function to check and install dependencies
check_dependency() {
    local cmd="$1"
    local install_opts="${2:-}"
    
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${YELLOW}Installing $cmd...${NC}"
        if [ -n "$install_opts" ]; then
            sudo snap install "$cmd" "$install_opts"
        else
            sudo snap install "$cmd"
        fi
        return $?
    fi
    echo -e "${GREEN}$cmd is already installed${NC}"
    return 0
}

# Function to check network connectivity
check_network() {
    echo -e "${YELLOW}Checking network connectivity...${NC}"
    if ping -c 1 8.8.8.8 &> /dev/null; then
        echo -e "${GREEN}Network is up${NC}"
        return 0
    else
        echo -e "${RED}Network is down${NC}"
        return 1
    fi
}

# Function to clean previous builds
clean_environment() {
    echo -e "${YELLOW}Cleaning previous builds...${NC}"
    rm -f nexusctl_*.snap
    snapcraft clean || true
}

# Main build function
build_snap() {
    echo -e "${YELLOW}Building snap package...${NC}"
    
    # Try different build methods in order
    build_methods=(
        "snapcraft --debug"
        "snapcraft --debug --destructive-mode"
        "snapcraft --debug --provider=multipass"
    )
    
    for method in "${build_methods[@]}"; do
        echo -e "${YELLOW}Trying build method: $method${NC}"
        if eval "$method"; then
            echo -e "${GREEN}Build successful!${NC}"
            return 0
        else
            echo -e "${RED}Build method failed: $method${NC}"
        fi
    done
    
    return 1
}

# Function to install and configure the snap
install_snap() {
    local snap_file="nexusctl_1.0_amd64.snap"
    
    if [ ! -f "$snap_file" ]; then
        echo -e "${RED}Snap package not found: $snap_file${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}Installing snap package...${NC}"
    sudo snap install "$snap_file" --dangerous
    
    echo -e "${YELLOW}Configuring service...${NC}"
    sudo systemctl enable snap.nexusctl.nexusctl.service || true
    sudo systemctl start snap.nexusctl.nexusctl.service || true
}

# Main execution
main() {
    echo -e "${GREEN}Starting Nexus Control build process...${NC}"
    
    # Check dependencies
    check_dependency "snapcraft" "--classic"
    check_dependency "multipass" "--classic"
    
    # Check network
    if ! check_network; then
        echo -e "${RED}Network checks failed. Please check your internet connection${NC}"
        exit 1
    fi
    
    # Clean environment
    clean_environment
    
    # Build snap
    if ! build_snap; then
        echo -e "${RED}Build failed${NC}"
        exit 1
    fi
    
    # Install snap
    if ! install_snap; then
        echo -e "${RED}Installation failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Installation complete!${NC}"
    echo "You can now run 'nexusctl' to start the application"
}

# Execute main function
main "$@" 