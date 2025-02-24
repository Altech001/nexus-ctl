import webbrowser
import gi
from about import AboutUs
from help import HelpDialog
from nexus import NexusBot

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib, Gdk
import subprocess
# import time
import os
# import threading


class Nexus:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_file = "logo"

        # Create the application indicator
        self.indicator = AppIndicator3.Indicator.new_with_path(
            "Nexus",
            icon_file,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            base_dir
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Build the menu
        self.menu = Gtk.Menu()

        # Create an accelerator group
        self.accel_group = Gtk.AccelGroup()
        self.menu.set_accel_group(self.accel_group)

        # "Daily Update & Upgrade" Menu Item
        update_item = Gtk.MenuItem(label="Update & Upgrade")
        update_item.connect("activate", self.update_upgd)
        update_item.add_accelerator("activate", self.accel_group, Gdk.KEY_u, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.menu.append(update_item)

        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())

        # Update after 5s
        update_sec = Gtk.MenuItem(label="Update after 5s")
        update_sec.connect("activate", self.update_sec)
        self.menu.append(update_sec)

        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())

        # Auto Update
        auto_update = Gtk.CheckMenuItem(label="Auto Update")
        auto_update.set_active(True)
        auto_update.connect("toggled", self.auto_update)
        self.menu.append(auto_update)

        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())

        # Nexus Bot
        nexus_bot = Gtk.MenuItem(label="Nexus Bot")
        nexus_bot.connect('activate', self.nexus_bot)
        self.menu.append(nexus_bot)

        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())

        # Share Nexus
        share_nexus = Gtk.MenuItem(label="More Features")
        submenu = Gtk.Menu()

        submenu_1 = Gtk.MenuItem(label="Share Nexus")
        submenu_1.connect("activate", self.on_share_nexus)
        submenu.append(submenu_1)

        submenu_2 = Gtk.MenuItem(label="About Nexus")
        submenu_2.connect('activate', self.about)
        submenu.append(submenu_2)

        submenu_3 = Gtk.MenuItem(label="Help")
        submenu_3.connect('activate', self.nexus_help)
        submenu.append(submenu_3)

        submenu.show_all()
        share_nexus.set_submenu(submenu)
        self.menu.append(share_nexus)

        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())

        # "Quit" Menu Item
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit)
        quit_item.add_accelerator("activate", self.accel_group, Gdk.KEY_q, Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.menu.append(quit_item)

        # Show the menu and set it for the indicator
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    # Update & Upgrade
    def update_upgd(self, widget):
        try:
            # Launch GNOME Terminal to execute the update commands.
            subprocess.Popen([
                "gnome-terminal",
                "--",
                "bash",
                "-c",
                "echo '############## ..Lets Start Linux Update and Upgrade.. #####################\n\n'; "
                "pkexec apt update && "
                "pkexec apt upgrade -y && "
                "echo '#############Upgrade complete!################'; "
                "exec bash"
            ])
        except Exception as e:
            print("Error launching terminal for update:", e)
        return False

    # Quit the AppIndicator
    def quit(self, widget):
        print("Exiting Nexus .>..>..>..>..>..>..>.")
        Gtk.main_quit()

    # Auto Update
    def auto_update(self, widget):
        new_state = widget.get_active()
        if new_state:
            try:
                print("Running: sudo apt update")
                subprocess.run(["pkexec", "apt", "update"], check=True)

                print("Running: sudo apt upgrade -y")
                subprocess.run(["pkexec", "apt", "upgrade", "-y"], check=True)

                # Additional update commands
                print("#### Running: sudo apt autoremove -y")
                subprocess.run(["pkexec", "apt", "autoremove", "-y"], check=True)

                print("#### Running: sudo apt autoclean")
                subprocess.run(["pkexec", "apt", "autoclean"], check=True)

                print("***Updates complete!")
            except subprocess.CalledProcessError as e:
                print("Update process failed:", e)

    # Update after 5s
    def update_sec(self, widget):
        print("Update will start in 5 seconds...")
        # Schedule to run after 5 seconds.
        GLib.timeout_add_seconds(5, self.run_update)

    def run_update(self):
        try:
            # Launch GNOME Terminal to execute the update commands.
            subprocess.Popen([
                "gnome-terminal",
                "--",
                "bash",
                "-c",
                "echo '*******************Update will start in 5 seconds..********************'\n\n"
                "echo '############## ..Lets Start Linux Update and Upgrade.. #####################\n\n'; "
                "for i in {5..1}; do echo '########## Progress: $((i*20))% ##########'; sleep 1; done;\n\n "
                "pkexec apt update && "
                "pkexec apt upgrade -y && "
                "echo '#############Upgrade complete!################'; "
                "exec bash"
            ])
        except Exception as e:
            print("Error launching terminal for update:", e)
        return False

    # Nexus Bot
    def nexus_bot(self, _):
        bot = NexusBot()
        bot.show_all()

    # Help
    def nexus_help(self, _):
        help = HelpDialog()
        help.show_all()

    # About Us
    def about(self, _):
        about = AboutUs()
        about.show_all()

    # Share Nexus
    def on_share_nexus(self, widget):
        message = "🚀 Install Nexus on Linux:\n```sudo snap install --classic nexus```"
        whatsapp_url = f"https://api.whatsapp.com/send?text={message}"
        webbrowser.open(whatsapp_url)


if __name__ == "__main__":
    Nexus()
    Gtk.main()
