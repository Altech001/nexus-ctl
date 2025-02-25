#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting Nexus Control .deb package creation...${NC}"

# Clean up previous builds
echo -e "${YELLOW}Cleaning up previous builds...${NC}"
rm -rf debian/
rm -f *.deb

# Create directory structure
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p debian/DEBIAN
mkdir -p debian/usr/bin
mkdir -p debian/usr/lib/nexusctl
mkdir -p debian/etc/systemd/system
mkdir -p debian/usr/share/applications
mkdir -p debian/usr/share/icons/hicolor/256x256/apps
mkdir -p debian/usr/share/doc/nexusctl

# Create control file
echo -e "${YELLOW}Creating control file...${NC}"
cat > debian/DEBIAN/control << 'EOF'
Package: nexusctl
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: python3-full (>= 3.10), 
 python3-venv (>= 3.10),
 python3-gi,
 python3-tk,
 python3-pip,
 python3-dev,
 gir1.2-gtk-3.0,
 gir1.2-appindicator3-0.1,
 gir1.2-notify-0.7,
 libnotify-bin,
 python3-dbus,
 libdbus-1-dev,
 libgirepository1.0-dev,
 python3-xlib,
 libx11-dev,
 libxss-dev,
 libgtk-3-dev,
 libcairo2-dev,
 pkg-config,
 dbus,
 dbus-x11,
 build-essential
Maintainer: Your Name <your.email@example.com>
Description: Nexus Control System
 A powerful system control and management tool for Linux.
 Provides system updates, monitoring, and automation features.

EOF

# Create postinst script
echo -e "${YELLOW}Creating postinst script...${NC}"
cat > debian/DEBIAN/postinst << 'EOF'
#!/bin/bash
set -e

# Get the actual user who ran sudo
REAL_USER=$SUDO_USER
if [ -z "$REAL_USER" ]; then
    REAL_USER=$(who | awk '{print $1}' | head -n1)
fi

# Create user-specific directories
USER_HOME=$(getent passwd $REAL_USER | cut -d: -f6)
mkdir -p $USER_HOME/.local/share/nexusctl
chown -R $REAL_USER:$REAL_USER $USER_HOME/.local/share/nexusctl

# Create systemd user directory
mkdir -p $USER_HOME/.config/systemd/user
cp /usr/lib/systemd/user/nexusctl.service $USER_HOME/.config/systemd/user/
chown -R $REAL_USER:$REAL_USER $USER_HOME/.config

# Create virtual environment
VENV_PATH=/opt/nexusctl/venv
mkdir -p /opt/nexusctl
python3 -m venv $VENV_PATH

# Set ownership of virtual environment
chown -R $REAL_USER:$REAL_USER /opt/nexusctl

# Install Python dependencies as the real user
sudo -u $REAL_USER $VENV_PATH/bin/pip install \
  PyQt5 \
  notify2 \
  customtkinter \
  darkdetect \
  Markdown \
  markdown2 \
  pillow \
  psutil \
  pycairo \
  PyGObject \
  pytesseract \
  python-dotenv \
  requests \
  dbus-python \
  python-xlib \
  pyautogui \
  screeninfo \
  pynput \
  pyperclip

# Enable and start the service as the user
sudo -u $REAL_USER XDG_RUNTIME_DIR=/run/user/$(id -u $REAL_USER) systemctl --user daemon-reload
sudo -u $REAL_USER XDG_RUNTIME_DIR=/run/user/$(id -u $REAL_USER) systemctl --user enable nexusctl
sudo -u $REAL_USER XDG_RUNTIME_DIR=/run/user/$(id -u $REAL_USER) systemctl --user start nexusctl

# Update desktop database
update-desktop-database

# Create autostart entry
mkdir -p /etc/xdg/autostart
cp /usr/share/applications/nexusctl.desktop /etc/xdg/autostart/

# Set permissions
chmod +x /usr/bin/nexusctl
chmod +x /usr/lib/nexusctl/main.py

exit 0
EOF

# Create prerm script
echo -e "${YELLOW}Creating prerm script...${NC}"
cat > debian/DEBIAN/prerm << 'EOF'
#!/bin/bash
set -e

# Stop and disable service
systemctl stop nexusctl.service || true
systemctl disable nexusctl.service || true

# Remove autostart entry
rm -f /etc/xdg/autostart/nexusctl.desktop

# Clean up virtual environment
rm -rf /opt/nexusctl

exit 0
EOF

# Create systemd service file
echo -e "${YELLOW}Creating systemd service file...${NC}"
mkdir -p debian/usr/lib/systemd/user
cat > debian/usr/lib/systemd/user/nexusctl.service << 'EOF'
[Unit]
Description=Nexus Control System
After=network.target
After=graphical-session.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
ExecStart=/usr/bin/nexusctl

[Install]
WantedBy=graphical-session.target
EOF

# Create desktop entry
echo -e "${YELLOW}Creating desktop entry...${NC}"
cat > debian/usr/share/applications/nexusctl.desktop << 'EOF'
[Desktop Entry]
Name=Nexus Control
Comment=System Control and Management Tool
Exec=nexusctl
Icon=nexusctl
Terminal=false
Type=Application
Categories=Utility;System;
StartupNotify=true
X-GNOME-Autostart-enabled=true
EOF

# Create executable script
echo -e "${YELLOW}Creating executable script...${NC}"
cat > debian/usr/bin/nexusctl << 'EOF'
#!/bin/bash

# Don't allow running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "Error: This application should not be run as root"
    exit 1
fi

# Create user directory if it doesn't exist
mkdir -p ~/.local/share/nexusctl

# Ensure dbus session is available
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    eval $(dbus-launch --sh-syntax)
fi

# Debug information
echo "Environment:"
echo "DISPLAY=$DISPLAY"
echo "DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
echo "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"

# Use the virtual environment's Python
export VIRTUAL_ENV=/opt/nexusctl/venv
export PATH="/opt/nexusctl/venv/bin:$PATH"
export PYTHONPATH=/usr/lib/nexusctl:$PYTHONPATH
export GI_TYPELIB_PATH=/usr/lib/girepository-1.0:$GI_TYPELIB_PATH
export QT_DEBUG_PLUGINS=1

# Run the application
$VIRTUAL_ENV/bin/python3 /usr/lib/nexusctl/main.py "$@" 2>&1 | tee ~/.local/share/nexusctl/debug.log
EOF

# Copy application files
echo -e "${YELLOW}Copying application files...${NC}"
cp -r main.py nexus.py about.py help.py logo.png debian/usr/lib/nexusctl/

# Copy icon
cp logo.png debian/usr/share/icons/hicolor/256x256/apps/nexusctl.png

# Set permissions
echo -e "${YELLOW}Setting permissions...${NC}"
chmod 755 debian/DEBIAN/postinst
chmod 755 debian/DEBIAN/prerm
chmod 755 debian/usr/bin/nexusctl
chmod 644 debian/DEBIAN/control
chmod 644 debian/etc/systemd/system/nexusctl.service
chmod 644 debian/usr/share/applications/nexusctl.desktop
chmod 644 debian/usr/share/icons/hicolor/256x256/apps/nexusctl.png

# Build the package
echo -e "${YELLOW}Building package...${NC}"
dpkg-deb --build debian nexusctl_1.0.0_amd64.deb

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Package built successfully!${NC}"
    echo -e "${YELLOW}To install, run:${NC}"
    echo "sudo dpkg -i nexusctl_1.0.0_amd64.deb"
    echo "sudo apt-get install -f"
else
    echo -e "${RED}Package build failed!${NC}"
    exit 1
fi

# Create changelog
cat > debian/usr/share/doc/nexusctl/changelog << EOF
nexusctl (1.0.0) stable; urgency=medium

  * Initial release
  * Added AI chat functionality
  * Added system monitoring
  * Added clipboard management

 -- Your Name <your.email@example.com>  $(date -R)
EOF

# Compress changelog
gzip -9 debian/usr/share/doc/nexusctl/changelog 