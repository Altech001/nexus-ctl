from PIL import Image  # Corrected import for Image
import gi
import psutil
import os
import time
import threading
import webbrowser
import requests
import logging
from help import HelpDialog
import pytesseract # type: ignore
from dotenv import load_dotenv # type: ignore
import subprocess
import notify2  # Changed from Notify to notify2
from Xlib import display  # For active window detection
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, Gdk, GLib, AppIndicator3, Wnck

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def is_wayland():
    """Check if running under Wayland"""
    return os.environ.get('XDG_SESSION_TYPE') == 'wayland'

# Check for X11 display
def check_x11_display():
    try:
        d = display.Display()
        if d is None:
            return False
        return True
    except Exception:
        return False

# Initialize window tracking more safely
def init_wnck_screen():
    try:
        if check_x11_display():
            screen = Wnck.Screen.get_default()
            screen.force_update()
            return screen
        return None
    except Exception as e:
        logging.error(f"Failed to initialize Wnck screen: {e}")
        return None

class NexusBot(Gtk.Window):
    def __init__(self):
        super().__init__(title="Nexus AI Bot")
        self.set_default_size(300, 600)
        
        # Position window on the left side
        screen = Gdk.Screen.get_default()
        self.move(0, 0)
        self.set_size_request(300, screen.get_height())
        self.stick()
        self.set_keep_above(True)

        # Initialize clipboard
        self.clipboard_history = []
        notify2.init("AL Nexus")

        # Create a spinner for loading indication
        self.spinner = Gtk.Spinner()
        self.spinner.set_margin_top(10)
        self.spinner.set_margin_bottom(10)
        self.spinner.set_sensitive(False)

        # Apply CSS
        self.apply_css()
        
        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.main_box)

        # Create UI elements
        self.create_nav_bar()
        self.create_chat_area()
        self.create_input_area()

        self.show_all()
        self.start_clipboard_monitoring()

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background: linear-gradient(to bottom, #2c3e50, #34495e);
                color: white;
            }
            
            headerbar {
                background: linear-gradient(135deg, #2196F3 0%, #64B5F6 100%);
                border: none;
                min-height: 42px;
                padding: 4px 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            headerbar button {
                background: linear-gradient(to bottom, #3498db, #2980b9);
                color: white;
                border: none;
                padding: 8px;
                margin: 4px;
            }
            
            headerbar button:hover {
                background: linear-gradient(to bottom, #2980b9, #2471a3);
            }
            
            headerbar label {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            
            entry {
                background: white;
                color: #2c3e50;
                border-radius: 8px;
                border: 1px solid #E3E9EF;
                padding: 8px 12px;
                margin: 8px;
                font-size: 13px;
            }
            
            entry:focus {
                border-color: #2196F3;
                box-shadow: 0 0 0 2px rgba(33,150,243,0.2);
            }
            
            textview {
                background: white;
                color: #2c3e50;
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            }
            
            textview text {
                background: transparent;
                color: #2c3e50;
            }
            
            .user-message {
                background: rgba(33,150,243,0.1);
                border-radius: 10px;
                padding: 8px 12px;
                margin: 4px 8px;
            }
            
            .bot-message {
                background: #F8FAFC;
                border-radius: 10px;
                padding: 8px 12px;
                margin: 4px 8px;
                border: 1px solid #E3E9EF;
            }
            
            .timestamp {
                color: #94A3B8;
                font-size: 11px;
                margin: 2px 8px;
            }
            
            scrolledwindow {
                border: none;
                background: transparent;
            }
            
            scrolledwindow undershoot, 
            scrolledwindow overshoot {
                background: none;
            }
            
            scrollbar {
                background: transparent;
                border: none;
            }
            
            scrollbar slider {
                min-width: 6px;
                min-height: 6px;
                border-radius: 3px;
                background: rgba(33,150,243,0.3);
            }
            
            scrollbar slider:hover {
                background: rgba(33,150,243,0.5);
            }
            
            menu {
                background: white;
                border: 1px solid #E3E9EF;
                border-radius: 8px;
                padding: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            menuitem {
                padding: 8px 12px;
                color: #2c3e50;
                border-radius: 4px;
            }
            
            menuitem:hover {
                background: rgba(33,150,243,0.1);
            }
            
            separator {
                background: #E3E9EF;
                margin: 4px 0;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def create_nav_bar(self):
        self.nav_bar = Gtk.HeaderBar()
        self.nav_bar.set_show_close_button(True)
        self.nav_bar.set_title("Nexus AI")
        self.set_titlebar(self.nav_bar)

        # Clear Chat Button
        clear_button = Gtk.Button()
        clear_button.set_tooltip_text("Clear Chat")
        clear_button.set_image(Gtk.Image.new_from_icon_name("edit-clear-symbolic", Gtk.IconSize.MENU))
        clear_button.connect("clicked", self.clear_chat)
        self.nav_bar.pack_start(clear_button)

        # Clipboard Button
        self.clipboard_icon = Gtk.MenuButton()
        self.clipboard_icon.set_tooltip_text("Clipboard History")
        self.clipboard_icon.set_image(Gtk.Image.new_from_icon_name("edit-paste-symbolic", Gtk.IconSize.MENU))
        self.nav_bar.pack_end(self.clipboard_icon)

        self.create_clipboard_indicator()

    def create_chat_area(self):
        # Chat area
        chat_scroll = Gtk.ScrolledWindow()
        chat_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.chat_history = Gtk.TextView()
        self.chat_history.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.chat_history.set_editable(False)
        self.chat_history.set_cursor_visible(False)
        self.chat_buffer = self.chat_history.get_buffer()
        self.create_text_tags()
        
        chat_scroll.add(self.chat_history)
        self.main_box.pack_start(chat_scroll, True, True, 0)

    def create_input_area(self):
        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_box.set_margin_top(8)
        input_box.set_margin_bottom(8)
        input_box.set_margin_start(8)
        input_box.set_margin_end(8)
        
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Type your message...")
        self.entry.connect("activate", self.on_send_message)
        input_box.pack_start(self.entry, True, True, 0)

        # Add spinner to the input area
        input_box.pack_start(self.spinner, False, False, 0)

        self.main_box.pack_end(input_box, False, False, 0)

    def create_text_tags(self):
        tag_table = self.chat_buffer.get_tag_table()
        
        # Message alignment tags
        left_tag = Gtk.TextTag.new("left")
        left_tag.set_property("justification", Gtk.Justification.LEFT)
        left_tag.set_property("left-margin", 8)
        left_tag.set_property("right-margin", 64)
        tag_table.add(left_tag)

        right_tag = Gtk.TextTag.new("right")
        right_tag.set_property("justification", Gtk.Justification.RIGHT)
        right_tag.set_property("right-margin", 8)
        right_tag.set_property("left-margin", 64)
        tag_table.add(right_tag)
        
        # Message style tags
        user_tag = Gtk.TextTag.new("user")
        user_tag.set_property("background", "rgba(33,150,243,0.1)")
        user_tag.set_property("foreground", "#2c3e50")
        user_tag.set_property("paragraph-background", "rgba(33,150,243,0.05)")
        user_tag.set_property("pixels-above-lines", 6)
        user_tag.set_property("pixels-below-lines", 6)
        user_tag.set_property("pixels-inside-wrap", 8)
        tag_table.add(user_tag)
        
        bot_tag = Gtk.TextTag.new("bot")
        bot_tag.set_property("background", "#F8FAFC")
        bot_tag.set_property("foreground", "#2c3e50")
        bot_tag.set_property("paragraph-background", "#FFFFFF")
        bot_tag.set_property("pixels-above-lines", 6)
        bot_tag.set_property("pixels-below-lines", 6)
        bot_tag.set_property("pixels-inside-wrap", 8)
        tag_table.add(bot_tag)
        
        timestamp_tag = Gtk.TextTag.new("timestamp")
        timestamp_tag.set_property("scale", 0.8)
        timestamp_tag.set_property("foreground", "#94A3B8")
        timestamp_tag.set_property("pixels-above-lines", 4)
        tag_table.add(timestamp_tag)

    def append_message(self, sender, message, alignment="left"):
        end_iter = self.chat_buffer.get_end_iter()
        
        # Add timestamp
        timestamp = time.strftime("%H:%M")
        self.chat_buffer.insert_with_tags_by_name(
            end_iter, 
            f"{timestamp}\n", 
            "timestamp"
        )
        
        # Add message with styling
        tag_name = "user" if sender == "You" else "bot"
        message_text = f"{sender}: {message}\n\n"
        
        # Insert message with both alignment and style tags
        self.chat_buffer.insert_with_tags_by_name(
            end_iter,
            message_text,
            alignment,
            tag_name
        )
        
        # Scroll to new message
        GLib.idle_add(
            self.chat_history.scroll_to_iter,
            self.chat_buffer.get_end_iter(),
            0, False, 0, 0
        )

    def on_send_message(self, widget):
        """Handle sending messages"""
        user_input = self.entry.get_text().strip()
        if user_input:
            self.append_message("You", user_input, "right")
            self.entry.set_text("")
            self.spinner.start()  # Start the spinner
            threading.Thread(target=self.process_query, args=(user_input,), daemon=True).start()

    def process_query(self, query):
        """Process user input and get AI response"""
        try:
            response = self.query_gemini(query, api_key)
            GLib.idle_add(self.append_message, "Nexus", response, "left")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            GLib.idle_add(self.append_message, "System", error_msg, "left")
        finally:
            GLib.idle_add(self.stop_spinner)  # Stop the spinner

    def query_gemini(self, query, api_key):
        """Query the Gemini API"""
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {'Content-Type': 'application/json'}
        data = {"contents": [{"parts": [{"text": query}]}]}

        try:
            response = requests.post(f"{url}?key={api_key}", headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            candidates = result.get("candidates", [])
            if candidates:
                return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No response")

        except requests.exceptions.Timeout:
            return "Request timed out. Please try again."
        except Exception as e:
            logging.error(f"API Error: {e}")
            return f"Error: {str(e)}"

    def start_system_monitoring(self):
        """Monitor system resources"""
        def monitor():
            while True:
                ram = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)
                
                GLib.idle_add(self.ram_label.set_text, f"RAM: {ram.percent}%")
                GLib.idle_add(self.cpu_label.set_text, f"CPU: {cpu}%")
                
                time.sleep(2)

        threading.Thread(target=monitor, daemon=True).start()

    def start_clipboard_monitoring(self):
        """Monitor clipboard for changes"""
        def monitor_clipboard():
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            last_text = ""
            
            while True:
                try:
                    text = clipboard.wait_for_text()
                    if text and text != last_text and len(text.strip()) > 0:
                        last_text = text
                        self.clipboard_history.append(text)
                        if len(self.clipboard_history) > 20:  # Keep last 20 items
                            self.clipboard_history.pop(0)
                        GLib.idle_add(self.update_clipboard_menu)
                except Exception as e:
                    logging.error(f"Clipboard monitoring error: {e}")
                time.sleep(0.5)

        threading.Thread(target=monitor_clipboard, daemon=True).start()

    def paste_clipped_data(self, widget):
        """ Pastes the last clipped data where the cursor is """
        text = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
        if text:
            self.entry.set_text(text)

    def clean_copied_data(self, widget):
        """ Cleans copied data using AI """
        text = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text()
        if text:
            cleaned_text = self.simulate_ai_cleaning(text)
            GLib.idle_add(self.append_message, "AI Cleaned", cleaned_text, "left")

    def simulate_ai_cleaning(self, text):
        """ Simulates AI cleaning of text """
        # Replace with actual AI API call
        return f"Cleaned Text: {text.strip()}"

    def show_clipboard_history(self, widget):
        dialog = Gtk.Dialog(
            title="Clipboard History",
            parent=self,
            flags=0,
            buttons=("Clear History", Gtk.ResponseType.REJECT,
                    "Close", Gtk.ResponseType.ACCEPT)
        )
        dialog.set_default_size(400, 300)
        
        # Add CSS class
        dialog.get_style_context().add_class('clipboard-dialog')
        
        content_area = dialog.get_content_area()
        content_area.set_spacing(8)
        content_area.set_margin_top(12)
        content_area.set_margin_bottom(12)
        content_area.set_margin_start(12)
        content_area.set_margin_end(12)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        history_box = Gtk.ListBox()
        history_box.set_selection_mode(Gtk.SelectionMode.NONE)
        
        for item in reversed(self.clipboard_history):
            row = Gtk.ListBoxRow()
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_margin_top(6)
            row_box.set_margin_bottom(6)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)
            
            text = Gtk.Label(label=item)
            text.set_line_wrap(True)
            text.set_xalign(0)
            row_box.pack_start(text, True, True, 0)
            
            copy_button = Gtk.Button.new_from_icon_name(
                "edit-copy-symbolic",
                Gtk.IconSize.BUTTON
            )
            copy_button.connect("clicked", lambda btn, txt=item: 
                Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(txt, -1))
            row_box.pack_end(copy_button, False, False, 0)
            
            row.add(row_box)
            history_box.add(row)
        
        scrolled.add(history_box)
        content_area.pack_start(scrolled, True, True, 0)
        content_area.show_all()
        
        response = dialog.run()
        if response == Gtk.ResponseType.REJECT:
            self.clipboard_history.clear()
        
        dialog.destroy()

    def on_workspace_changed(self, window, pspec):
        """ Detects when the workspace changes """
        self.append_message("System", "Detected workspace change!", "left")

    def clear_clipboard(self):
        """ Clears the clipboard content """
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text("", -1)

    def show_typing_indicator(self):
        end_iter = self.chat_buffer.get_end_iter()
        self.typing_mark = self.chat_buffer.create_mark("typing", end_iter, True)
        self.chat_buffer.insert_with_tags_by_name(
            end_iter,
            "Nexus is typing...\n",
            "timestamp"
        )
        
    def remove_typing_indicator(self):
        if hasattr(self, 'typing_mark'):
            start_iter = self.chat_buffer.get_iter_at_mark(self.typing_mark)
            end_iter = self.chat_buffer.get_end_iter()
            self.chat_buffer.delete(start_iter, end_iter)

    def clear_chat(self, button):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Clear Chat History?"
        )
        dialog.format_secondary_text("This action cannot be undone.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.chat_buffer.set_text("")
        dialog.destroy()

    def create_clipboard_indicator(self):
        """Create clipboard menu and indicator"""
        # Create menu
        self.clipboard_menu = Gtk.Menu()
        
        # Create system tray indicator
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.indicator = AppIndicator3.Indicator.new(
            "nexus-clipboard",
            "edit-paste-symbolic",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.clipboard_menu)
        
        # Set menu for the clipboard button in headerbar
        self.clipboard_icon.set_popup(self.clipboard_menu)
        
        # Initial menu update
        self.update_clipboard_menu()

    def update_clipboard_menu(self):
        """Update the clipboard menu items"""
        # Clear existing items
        for item in self.clipboard_menu.get_children():
            self.clipboard_menu.remove(item)
        
        # Add header
        header = Gtk.MenuItem(label="Clipboard History")
        header.set_sensitive(False)
        self.clipboard_menu.append(header)
        self.clipboard_menu.append(Gtk.SeparatorMenuItem())
        
        # Add clipboard items
        for text in reversed(self.clipboard_history):
            # Create menu item
            display_text = (text[:50] + "...") if len(text) > 50 else text
            item = Gtk.MenuItem(label=display_text)
            item.connect('activate', lambda x, t=text: self.paste_clipboard_item(None, t))
            self.clipboard_menu.append(item)
        
        if not self.clipboard_history:
            empty_item = Gtk.MenuItem(label="(Empty)")
            empty_item.set_sensitive(False)
            self.clipboard_menu.append(empty_item)
        
        # Add separator and management options
        self.clipboard_menu.append(Gtk.SeparatorMenuItem())
        
        # Add preferences option
        prefs_item = Gtk.MenuItem(label="Preferences")
        prefs_item.connect('activate', self.show_clipboard_preferences)
        self.clipboard_menu.append(prefs_item)
        
        # Add clear option
        clear_item = Gtk.MenuItem(label="Clear History")
        clear_item.connect('activate', lambda x: self.clear_clipboard_history())
        self.clipboard_menu.append(clear_item)
        
        self.clipboard_menu.show_all()

    def paste_clipboard_item(self, menuitem, text):
        """Paste the selected clipboard item"""
        try:
            # Set clipboard content
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)
            clipboard.store()
            
            # Use xdotool to simulate typing instead of Ctrl+V
            subprocess.run([
                'xdotool', 'type', '--delay', '50', text
            ], check=True)
            
        except Exception as e:
            logging.error(f"Paste failed: {e}")
            self.show_paste_error()

    def show_paste_error(self):
        """Show error dialog when paste fails"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Paste Operation Failed"
        )
        dialog.format_secondary_text(
            "Could not paste the text. Please ensure required tools are installed:\n"
            "sudo apt-get install xdotool xclip\n\n"
            "You can still paste manually using Ctrl+V or right-click > Paste"
        )
        dialog.run()
        dialog.destroy()

    def add_keyboard_shortcuts(self):
        """Add global keyboard shortcuts"""
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)
        
        # Ctrl+L to clear chat
        key, mod = Gtk.accelerator_parse("<Control>L")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE, 
                          lambda *x: self.clear_chat(None))
        
        # Ctrl+K to focus entry
        key, mod = Gtk.accelerator_parse("<Control>K")
        accel_group.connect(key, mod, Gtk.AccelFlags.VISIBLE,
                          lambda *x: self.entry.grab_focus())

    def clear_clipboard_history(self):
        """Clear clipboard history with confirmation"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Clear Clipboard History?"
        )
        dialog.format_secondary_text("This action cannot be undone.")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            self.clipboard_history.clear()
            self.update_clipboard_menu()
        dialog.destroy()

    def show_clipboard_preferences(self, widget):
        """Show clipboard preferences dialog"""
        dialog = Gtk.Dialog(
            title="Clipboard Preferences",
            parent=self,
            flags=0,
            buttons=("Cancel", Gtk.ResponseType.CANCEL,
                    "Save", Gtk.ResponseType.OK)
        )
        
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        
        # History size
        history_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        history_label = Gtk.Label(label="Maximum History Size:")
        history_spin = Gtk.SpinButton.new_with_range(5, 50, 5)
        history_spin.set_value(len(self.clipboard_history) if self.clipboard_history else 20)
        history_box.pack_start(history_label, False, False, 0)
        history_box.pack_end(history_spin, False, False, 0)
        box.pack_start(history_box, False, False, 0)
        
        # Auto-paste option
        paste_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        paste_label = Gtk.Label(label="Auto-paste on select:")
        paste_switch = Gtk.Switch()
        paste_switch.set_active(True)
        paste_box.pack_start(paste_label, False, False, 0)
        paste_box.pack_end(paste_switch, False, False, 0)
        box.pack_start(paste_box, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            # Save the new history size
            new_size = int(history_spin.get_value())
            while len(self.clipboard_history) > new_size:
                self.clipboard_history.pop(0)
            
            # Update the menu
            self.update_clipboard_menu()
            
        dialog.destroy()

    def get_active_windows(self):
        """Get list of currently open windows"""
        windows = []
        if self.screen and not is_wayland():
            try:
                for window in self.screen.get_windows():
                    if not window.is_skip_tasklist():
                        windows.append({
                            'name': window.get_name(),
                            'app_name': window.get_application().get_name(),
                            'pid': window.get_pid()
                        })
            except Exception as e:
                logging.error(f"Error getting window list: {e}")
        return windows

    def get_active_window(self):
        """Get currently focused window"""
        if is_wayland():
            return None
            
        try:
            d = display.Display()
            window = d.get_input_focus().focus
            wmname = window.get_wm_name()
            wmclass = window.get_wm_class()
            if wmclass is not None:
                return {
                    'name': wmname,
                    'class': wmclass[1] if len(wmclass) > 1 else wmclass[0]
                }
        except Exception as e:
            logging.error(f"Error getting active window: {e}")
        return None

    def get_active_window_details(self):
        """Get detailed information about the active window and its content"""
        try:
            window = self.get_active_window()
            if not window:
                return "Could not get window information"

            details = []
            window_class = window.get('class', '').lower()

            if window_class == 'vlc':
                # Get VLC media information
                try:
                    # Get VLC process
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        if proc.info['name'] == 'vlc':
                            cmdline = proc.info['cmdline']
                            if cmdline:
                                # Get media file path
                                media_file = [arg for arg in cmdline if any(ext in arg.lower() 
                                    for ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv'])]
                                if media_file:
                                    details.append(f"Media File: {os.path.basename(media_file[0])}")
                                    details.append(f"Full Path: {media_file[0]}")
                                    
                                    # Get media information using ffprobe
                                    try:
                                        result = subprocess.run([
                                            'ffprobe',
                                            '-v', 'quiet',
                                            '-print_format', 'json',
                                            '-show_format',
                                            '-show_streams',
                                            media_file[0]
                                        ], capture_output=True, text=True)
                                        
                                        if result.stdout:
                                            import json
                                            media_info = json.loads(result.stdout)
                                            format_info = media_info.get('format', {})
                                            
                                            # Add media details
                                            duration = float(format_info.get('duration', 0))
                                            details.append(f"Duration: {int(duration//60)}m {int(duration%60)}s")
                                            details.append(f"Size: {int(int(format_info.get('size', 0))/1024/1024)}MB")
                                            
                                            # Get video stream info
                                            for stream in media_info.get('streams', []):
                                                if stream['codec_type'] == 'video':
                                                    details.append(f"Resolution: {stream.get('width')}x{stream.get('height')}")
                                                    details.append(f"Codec: {stream.get('codec_name')}")
                                    except Exception as e:
                                        logging.error(f"Error getting media info: {e}")

                except Exception as e:
                    logging.error(f"Error analyzing VLC: {e}")

            # Get general window information
            details.insert(0, f"Application: {window.get('class')}")
            details.insert(1, f"Window Title: {window.get('name')}")

            return "\n".join(details)

        except Exception as e:
            logging.error(f"Error getting window details: {e}")
            return "Error analyzing window"

    def setup_window_behavior(self):
        """Setup window behavior and positioning"""
        def on_configure_event(widget, event):
            # Keep window on left side
            if event.x != 0:
                self.move(0, event.y)
            return False

        self.connect('configure-event', on_configure_event)

        # Add resize handle
        self.resize_handle = Gtk.Button()
        self.resize_handle.set_size_request(5, -1)
        self.resize_handle.connect('button-press-event', self.on_resize_start)
        self.resize_handle.connect('button-release-event', self.on_resize_end)
        self.resize_handle.connect('motion-notify-event', self.on_resize)
        
        # Add to main box
        resize_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        resize_box.pack_end(self.resize_handle, False, False, 0)
        self.main_box.pack_end(resize_box, False, False, 0)

    def on_resize_start(self, widget, event):
        self.resizing = True
        return True

    def on_resize_end(self, widget, event):
        self.resizing = False
        return True

    def on_resize(self, widget, event):
        if hasattr(self, 'resizing') and self.resizing:
            width, _ = self.get_size()
            new_width = max(300, event.x_root)  # Minimum width of 300
            self.resize(new_width, self.get_size()[1])
        return True

    def show_system_info(self):
        """Show system information"""
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        info = (
            f"System Information:\n\n"
            f"RAM Usage: {ram.percent}%\n"
            f"CPU Usage: {cpu}%\n"
            f"Disk Usage: {disk.percent}%\n"
            f"Available RAM: {ram.available/1024/1024:.1f} MB\n"
            f"Total RAM: {ram.total/1024/1024:.1f} MB"
        )
        
        self.append_message("System", info, "left")

    def show_window_info(self):
        """Show current window information"""
        info = self.get_active_window_details()
        self.append_message("System", info, "left")

    def show_settings(self, widget):
        """Show settings dialog"""
        dialog = Gtk.Dialog(
            title="Settings",
            parent=self,
            flags=0,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK)
        )
        
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)

        # Theme selector
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        theme_label = Gtk.Label(label="Theme:")
        theme_combo = Gtk.ComboBoxText()
        theme_combo.append_text("Dark")
        theme_combo.append_text("Light")
        theme_combo.set_active(0)
        theme_box.pack_start(theme_label, False, False, 0)
        theme_box.pack_end(theme_combo, False, False, 0)
        box.pack_start(theme_box, False, False, 0)

        # Font size
        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        font_label = Gtk.Label(label="Font Size:")
        font_spin = Gtk.SpinButton.new_with_range(8, 24, 1)
        font_spin.set_value(14)
        font_box.pack_start(font_label, False, False, 0)
        font_box.pack_end(font_spin, False, False, 0)
        box.pack_start(font_box, False, False, 0)

        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def show_help(self, widget):
        """Show help dialog"""
        help_dialog = HelpDialog()
        help_dialog.show_all()

    def stop_spinner(self):
        """Stop the loading spinner"""
        self.spinner.stop()

if __name__ == "__main__":
    win = NexusBot()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
