import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib, Gdk, Gio
import sys
import logging
import notify2
import time
import os
import subprocess
import webbrowser
from about import AboutUs
from help import HelpDialog
from nexus import NexusBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.expanduser('~/.local/share/nexusctl/nexusctl.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

# Check if running as snap
if os.environ.get('SNAP'):
    # Set up snap-specific configurations
    os.environ['HOME'] = os.path.expanduser('~/snap/nexus-assistant/current')
    os.makedirs(os.environ['HOME'], exist_ok=True)

# Force X11 backend
os.environ['GDK_BACKEND'] = 'x11'

class NexusApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.altech.nexus",
                        flags=Gio.ApplicationFlags.FLAGS_NONE)  # Add proper flags
        self.window = None
        self.nexus = None
        
    def do_startup(self):
        # Initialize GTK before doing anything else
        Gtk.Application.do_startup(self)
        
        # Initialize notify2 here instead of in Nexus class
        notify2.init(" AL Nexus ")
        
        # Set up actions if needed
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit)
        self.add_action(quit_action)

        # Add CSS styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
                                    
            menuitem {
                padding: 12px 16px;
                border-radius: 8px;
                margin: 3px 6px;
                transition: all 200ms ease;
            }
            
            menuitem:hover {
                background: linear-gradient(145deg, alpha(@theme_selected_bg_color, 0.9), alpha(@theme_selected_bg_color, 0.7));
                box-shadow: 0 2px 4px alpha(black, 0.2);
            }
            
            menuitem > box {
                margin: 2px 0;
            }
            
            menuitem label {
                font-size: 14px;
                margin: 0 6px;
            }
            
            .shortcut-label {
                color: alpha(@theme_fg_color, 0.6);
                font-size: 12px;
                font-family: monospace;
                background-color: alpha(@theme_bg_color, 0.2);
                padding: 4px 8px;
                border-radius: 4px;
                margin-left: 12px;
            }
            
            separator {
                margin: 6px 0;
                background: linear-gradient(to right, 
                    transparent,
                    alpha(@theme_fg_color, 0.1),
                    transparent
                );
                min-height: 2px;
            }
            
            .title-item {
                background: linear-gradient(135deg, 
                    @theme_selected_bg_color,
                    shade(@theme_selected_bg_color, 1.3)
                );
                border-radius: 8px;
                padding: 16px;
                margin: 4px 6px 8px 6px;
                box-shadow: 0 2px 6px alpha(black, 0.2);
            }
            
            .title-item label {
                color: @theme_selected_fg_color;
                font-weight: bold;
                font-size: 18px;
                text-shadow: 0 1px 2px alpha(black, 0.2);
            }
            
            menu {
                background: alpha(@theme_bg_color, 0.95);
                border-radius: 12px;
                box-shadow: 0 4px 12px alpha(black, 0.2);
                padding: 4px;
            }
        """)
        
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        # Create main window if it doesn't exist
        if not self.window:
            self.window = Gtk.ApplicationWindow(application=self, title="AL Nexus")
            self.window.set_default_size(400, 300)
            self.window.set_position(Gtk.WindowPosition.CENTER)
            self.window.connect('delete-event', self.on_window_delete)
            
            # Create the Nexus indicator
            try:
                self.nexus = Nexus(self)
            except Exception as e:
                logging.error(f"Failed to create Nexus indicator: {e}")
                self.quit()
                return

    def on_window_delete(self, window, event):
        window.hide()
        return True
    
    def on_quit(self, action, param):
        self.quit_application()
    
    def quit_application(self):
        try:
            if self.nexus:
                self.nexus.cleanup()
            notify2.uninit()  # Clean up notify2 here
            self.quit()
        except Exception as e:
            logging.error(f"Error during application shutdown: {e}")
            sys.exit(1)


class Nexus:
    def __init__(self, application):
        self.application = application
        self.auto_update_enabled = False
        self.auto_update_source_id = None
        
        try:
            # Create the application indicator with correct icon path
            base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_dir, "logo.png")  # Make sure this file exists
            
            if not os.path.exists(icon_path):
                logging.warning(f"Icon file not found: {icon_path}")
                # Use fallback system icon
                self.indicator = AppIndicator3.Indicator.new(
                    "al-nexus",
                    "system-software-update",
                    AppIndicator3.IndicatorCategory.APPLICATION_STATUS
                )
            else:
                self.indicator = AppIndicator3.Indicator.new_with_path(
                    "al-nexus",
                    "logo",
                    AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
                    base_dir
                )
            
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            
            # Initialize menu
            self.menu = Gtk.Menu()
            self.accel_group = Gtk.AccelGroup()
            self.menu.set_accel_group(self.accel_group)
            
            # Build menu items
            self._build_menu()
            
            # Show the menu
            self.menu.show_all()
            self.indicator.set_menu(self.menu)
            
            try:
                icon_path = os.path.join(base_dir, "logo.png")
                self.indicator.set_icon_full(icon_path, "AL Nexus")
            except Exception as e:
                logging.warning(f"Failed to set custom icon: {e}")
                # Use a system icon instead
                self.indicator.set_icon_full("system-software-update", "AL Nexus")
            
        except Exception as e:
            logging.error(f"Failed to initialize Nexus: {e}")
            raise

    def _build_menu(self):
        # Title
        title_item = Gtk.MenuItem()
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_box.set_halign(Gtk.Align.CENTER)
        
        title_label = Gtk.Label()
        title_label.set_markup("<span font_weight='bold' font_size='large'>⚡ AL Nexus</span>")
        title_box.pack_start(title_label, True, False, 5)
        
        title_item.add(title_box)
        title_item.set_sensitive(False)
        title_item.get_style_context().add_class('title-item')
        self.menu.append(title_item)
        
        self.menu.append(Gtk.SeparatorMenuItem())

        # Update & Upgrade
        update_item = Gtk.MenuItem()
        update_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        update_label = Gtk.Label()
        update_label.set_text("🔄  Update & Upgrade")
        update_label.set_xalign(0)
        update_box.pack_start(update_label, True, True, 5)
        
        shortcut_label = Gtk.Label(label="Control + U")
        shortcut_label.get_style_context().add_class('shortcut-label')
        update_box.pack_end(shortcut_label, False, False, 5)
        
        update_item.add(update_box)
        update_item.connect("activate", self.update_upgd)
        update_item.add_accelerator("activate", self.accel_group, Gdk.KEY_U, 
                                  Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.menu.append(update_item)

        # Silent Update
        silent_item = Gtk.MenuItem()
        silent_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        silent_label = Gtk.Label()
        silent_label.set_text("🔕  Silent Update & Upgrade")
        silent_label.set_xalign(0)
        silent_box.pack_start(silent_label, True, True, 5)
        silent_item.add(silent_box)
        silent_item.connect("activate", lambda x: self.silent_update())
        self.menu.append(silent_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Delayed Update
        delay_item = Gtk.MenuItem()
        delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        delay_label = Gtk.Label()
        delay_label.set_text("⏲️  Update after 5s")
        delay_label.set_xalign(0)
        delay_box.pack_start(delay_label, True, True, 5)
        delay_item.add(delay_box)
        delay_item.connect("activate", self.update_sec)
        self.menu.append(delay_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Auto Update
        auto_item = Gtk.CheckMenuItem()
        auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        auto_label = Gtk.Label()
        auto_label.set_text("🔄  Auto Update")
        auto_label.set_xalign(0)
        auto_box.pack_start(auto_label, True, True, 5)
        auto_item.add(auto_box)
        auto_item.set_active(True)
        auto_item.connect("toggled", self.auto_update)
        self.menu.append(auto_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Nexus Bot
        bot_item = Gtk.MenuItem()
        bot_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bot_label = Gtk.Label()
        bot_label.set_text("🤖  Nexus Bot")
        bot_label.set_xalign(0)
        bot_box.pack_start(bot_label, True, True, 5)
        bot_item.add(bot_box)
        bot_item.connect('activate', self.nexus_bot)
        self.menu.append(bot_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # More Features submenu
        features_item = Gtk.MenuItem()
        features_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        features_label = Gtk.Label()
        features_label.set_text("⚙️  More Features")
        features_label.set_xalign(0)
        features_box.pack_start(features_label, True, True, 5)
        
        arrow_label = Gtk.Label(label=" ▶")
        features_box.pack_end(arrow_label, False, False, 5)
        
        features_item.add(features_box)
        
        submenu = Gtk.Menu()
        submenu_items = [
            ("📱  Share Nexus", self.on_share_nexus),
            ("ℹ️  About Nexus", self.about),
            ("❓  Help", self.nexus_help)
        ]

        for label, callback in submenu_items:
            item = Gtk.MenuItem()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            label_widget = Gtk.Label()
            label_widget.set_text(label)
            label_widget.set_xalign(0)
            box.pack_start(label_widget, True, True, 5)
            item.add(box)
            item.connect("activate", callback)
            submenu.append(item)

        submenu.show_all()
        features_item.set_submenu(submenu)
        self.menu.append(features_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem()
        quit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        quit_label = Gtk.Label()
        quit_label.set_text("🚪  Quit")
        quit_label.set_xalign(0)
        quit_box.pack_start(quit_label, True, True, 5)
        
        quit_shortcut = Gtk.Label(label="Control + Q")
        quit_shortcut.get_style_context().add_class('shortcut-label')
        quit_box.pack_end(quit_shortcut, False, False, 5)
        
        quit_item.add(quit_box)
        quit_item.connect("activate", self.quit)
        quit_item.add_accelerator("activate", self.accel_group, Gdk.KEY_Q, 
                                Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.menu.append(quit_item)

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
            logging.error("Error launching terminal for update: %s", e)
        return False

    # Quit the AppIndicator
    def quit(self, widget):
        """Quit the application properly"""
        logging.info("Exiting Nexus")
        self.application.quit_application()

    # Auto Update
    def auto_update(self, widget):
        self.auto_update_enabled = widget.get_active()
        self.setup_auto_update()

    # Update after 5s
    def update_sec(self, widget):
        logging.info("Update will start in 5 seconds...")
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
            logging.error("Error launching terminal for update: %s", e)
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

    def show_notification(self, title, message):
        """Show a notification dialog with delay"""
        def show_dialog():
            dialog = Gtk.MessageDialog(
                transient_for=self.application.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=title
            )
            dialog.format_secondary_text(message)
            dialog.connect("response", lambda dialog, response: dialog.destroy())
            dialog.show()
            return False

        # Add a small delay to prevent rapid dialog spawning
        GLib.timeout_add(500, show_dialog)

    def setup_auto_update(self):
        if self.auto_update_enabled:
            # Get current hour for next update
            current_time = time.localtime()
            hours_until_next = 24 - current_time.tm_hour
            seconds_until_next = hours_until_next * 3600
            
            # Schedule next update
            self.auto_update_source_id = GLib.timeout_add_seconds(
                seconds_until_next,
                self.run_scheduled_update
            )
            
            next_update = time.strftime(
                "%H:%M tomorrow",
                time.localtime(time.time() + seconds_until_next)
            )
            
            self.show_notification(
                "Auto Update Enabled",
                f"Next update scheduled for {next_update}"
            )
            logging.info(f"Auto update scheduled for {next_update}")
        else:
            if self.auto_update_source_id:
                GLib.source_remove(self.auto_update_source_id)
                self.auto_update_source_id = None
            self.show_notification(
                "Auto Update Disabled",
                "Automatic updates have been disabled"
            )
            logging.info("Auto update disabled")

    def run_scheduled_update(self):
        if not self.auto_update_enabled:
            return False
            
        logging.info("Running scheduled update")
        self.show_notification("Auto Update", "Starting scheduled system update...")
        
        try:
            # Run updates in background without terminal
            env = os.environ.copy()
            env['DEBIAN_FRONTEND'] = 'noninteractive'
            
            # Update
            subprocess.run(
                ["pkexec", "apt-get", "update", "-qq"],
                check=True,
                capture_output=True,
                env=env
            )
            
            # Upgrade
            subprocess.run(
                ["pkexec", "apt-get", "upgrade", "-y", "-qq"],
                check=True,
                capture_output=True,
                env=env
            )
            
            # Cleanup
            subprocess.run(
                ["pkexec", "apt-get", "autoremove", "-y", "-qq"],
                check=True,
                capture_output=True,
                env=env
            )
            
            self.show_notification(
                "Auto Update Complete",
                "System has been successfully updated"
            )
            logging.info("Scheduled update completed successfully")
            
        except subprocess.CalledProcessError as e:
            self.show_notification(
                "Auto Update Failed",
                f"Error during update: {str(e)}"
            )
            logging.error(f"Scheduled update failed: {e}")
            
        # Reschedule next update
        return True

    def silent_update(self):
        """Perform system update without showing terminal"""
        try:
            # Show initial notification
            self.show_notification("Update Started", "Starting system update...")
            
            env = os.environ.copy()
            env['DEBIAN_FRONTEND'] = 'noninteractive'
            
            # Combine all commands into one pkexec call
            update_command = [
                "pkexec",
                "bash",
                "-c",
                "apt-get update -qq && "
                "apt-get upgrade -y -qq && "
                "apt-get autoremove -y -qq && "
                "apt-get autoclean -qq"
            ]
            
            # Run all commands at once
            subprocess.run(update_command, check=True, capture_output=True, env=env)
            
            # Show completion notification
            self.show_notification(
                "Update Complete",
                "System has been successfully updated!"
            )
            
        except subprocess.CalledProcessError as e:
            self.show_notification(
                "Update Failed",
                f"Error during update: {str(e)}"
            )
            logging.error(f"Silent update failed: {e}")

    def cleanup(self):
        """Cleanup resources before quitting"""
        if self.auto_update_source_id:
            GLib.source_remove(self.auto_update_source_id)
        notify2.uninit()
        self.indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(
            title="Nexus Settings",
            transient_for=parent,
            flags=0
        )
        self.set_default_size(400, 300)
        
        box = self.get_content_area()
        
        # Auto-update settings
        auto_update_frame = Gtk.Frame(label="Auto Update Settings")
        auto_update_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        time_label = Gtk.Label(label="Update time:")
        time_spinner = Gtk.SpinButton.new_with_range(0, 23, 1)
        time_box.pack_start(time_label, False, False, 0)
        time_box.pack_start(time_spinner, False, False, 0)
        
        notify_switch = Gtk.Switch()
        notify_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        notify_label = Gtk.Label(label="Show notifications:")
        notify_box.pack_start(notify_label, False, False, 0)
        notify_box.pack_start(notify_switch, False, False, 0)
        
        auto_update_box.pack_start(time_box, False, False, 0)
        auto_update_box.pack_start(notify_box, False, False, 0)
        auto_update_frame.add(auto_update_box)
        
        box.pack_start(auto_update_frame, True, True, 0)
        
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Save", Gtk.ResponseType.OK)
        
        self.show_all()


if __name__ == "__main__":
    try:
        # Create and run application
        app = NexusApplication()
        exit_status = app.run(sys.argv)
        sys.exit(exit_status)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
