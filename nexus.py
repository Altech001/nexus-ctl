from PIL import Image  # Corrected import for Image
import gi
import psutil
import os
import time
import threading
import webbrowser
import requests
import logging
import pytesseract # type: ignore
from dotenv import load_dotenv # type: ignore


load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class NexusBot(Gtk.Window):
    def __init__(self):
        super().__init__(title="<span foreground='white'>Nexus AI Bot</span>")
        self.set_default_size(350,400)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_border_width(10)

        # Apply Dark Theme
        # self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.12, 0.12, 0.12, 1))
        self.apply_css()
        
    def apply_css(self):
        """ Apply Dark Theme CSS """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            * {
                background-color: #1E1E1E;
                color: white;
                font-size: 14px;
            }
            entry {
                background-color: #292929;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            textview {
                background-color: #1A1A1A;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            label {
                font-weight: bold;
                font-size: 12px;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Main Box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(self.main_box)

        # Navigation Bar
        self.create_nav_bar()

        # Chat History (Markdown & Images)
        self.chat_history = Gtk.TextView()
        self.chat_history.set_editable(False)
        self.chat_history.set_wrap_mode(Gtk.WrapMode.WORD)
        self.chat_history.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.15, 0.15, 0.15, 1))
        self.chat_history.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        self.chat_buffer = self.chat_history.get_buffer()
        self.create_text_tags()  # Create text tags

        chat_scroll = Gtk.ScrolledWindow()
        chat_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        chat_scroll.set_size_request(-1, 450)
        chat_scroll.add(self.chat_history)
        self.main_box.pack_start(chat_scroll, True, True, 0)

        # Entry Field
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Type your request...")
        self.entry.connect("activate", self.on_send_message)
        self.entry.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.18, 0.18, 0.18, 1))
        self.entry.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1, 1, 1, 1))
        self.main_box.pack_start(self.entry, False, False, 5)

        # RAM Usage Label
        self.ram_label = Gtk.Label(label="RAM Usage: Loading...")
        self.ram_label.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.8, 0.8, 0.8, 1))
        self.main_box.pack_start(self.ram_label, False, False, 5)

        # Workspace change detection
        self.connect("notify::workspace", self.on_workspace_changed)

        self.show_all()
        self.start_system_monitoring()
        self.start_clipboard_monitoring()

    def create_nav_bar(self):
        self.nav_bar = Gtk.HeaderBar()
        self.nav_bar.set_show_close_button(True)
        self.set_titlebar(self.nav_bar)

        # Clipboard Icon
        self.clipboard_icon = Gtk.MenuButton()
        self.clipboard_icon.set_image(Gtk.Image.new_from_icon_name("edit-paste-symbolic", Gtk.IconSize.BUTTON))
        self.nav_bar.pack_end(self.clipboard_icon)

        # Clipboard Menu
        self.clipboard_menu = Gtk.Menu()
        self.clipboard_icon.set_popup(self.clipboard_menu)

        paste_item = Gtk.MenuItem(label="Paste Clipped Data")
        paste_item.connect("activate", self.paste_clipped_data)
        self.clipboard_menu.append(paste_item)

        clean_item = Gtk.MenuItem(label="Clean Copied Data using AI")
        clean_item.connect("activate", self.clean_copied_data)
        self.clipboard_menu.append(clean_item)

        history_item = Gtk.MenuItem(label="Clipboard History")
        history_item.connect("activate", self.show_clipboard_history)
        self.clipboard_menu.append(history_item)

        self.clipboard_menu.show_all()

    def create_text_tags(self):
        tag_table = self.chat_buffer.get_tag_table()
        
        left_tag = Gtk.TextTag.new("left")
        left_tag.set_property("justification", Gtk.Justification.LEFT)
        tag_table.add(left_tag)

        right_tag = Gtk.TextTag.new("right")
        right_tag.set_property("justification", Gtk.Justification.RIGHT)
        tag_table.add(right_tag)

    def append_message(self, sender, message, alignment="left"):
        """ Adds messages to the chat window dynamically with alignment """
        end_iter = self.chat_buffer.get_end_iter()
        self.chat_buffer.insert_with_tags_by_name(end_iter, f"**{sender}**: {message}\n\n", alignment)
        
        # Scroll to the newly added message
        GLib.idle_add(self.chat_history.scroll_to_iter, self.chat_buffer.get_end_iter(), 0, False, 0, 0)

    def on_send_message(self, widget):
        user_input = self.entry.get_text().strip()
        if user_input:
            self.append_message("You", user_input, "right")
            self.entry.set_text("")
            threading.Thread(target=self.process_query, args=(user_input,), daemon=True).start()

    def process_query(self, query):
        """ Process user input and return responses """
        response = None

        if query.lower() in ["check ram", "ram usage"]:
            ram = psutil.virtual_memory()
            response = f"RAM Usage: {ram.percent}%"

        elif query.lower() in ["check cpu", "cpu usage"]:
            cpu_usage = psutil.cpu_percent(interval=1)
            response = f"CPU Usage: {cpu_usage}%"

        elif query.lower().startswith("search "):
            search_query = query.replace("search ", "").strip()
            webbrowser.open(f"https://www.google.com/search?q={search_query}")
            response = f"Searching Google for: {search_query}"

        elif query.lower().startswith("read image "):
            image_path = query.replace("read image ", "").strip()
            if os.path.exists(image_path):
                try:
                    text = pytesseract.image_to_string(Image.open(image_path))
                    response = f"Text from image:\n{text}"
                except Exception as e:
                    response = f"Error reading image: {e}"
                    logging.error(f"Error reading image: {e}")
            else:
                response = "Image file not found."

        else:
            api_key = os.environ.get('GEMINI_API_KEY')
            if api_key:
                response = self.query_gemini(query, api_key)
            else:
                response = "⚠️ Please set GEMINI_API_KEY environment variable to use Gemini AI."

        GLib.idle_add(self.append_message, "Nexus", response, "left")

    def query_gemini(self, query, api_key):
        """ Queries the Gemini API and returns the response with retries """
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {'Content-Type': 'application/json'}
        data = {"contents": [{"parts": [{"text": query}]}]}

        max_retries = 5
        retries = 0
        backoff_factor = 2  # Exponential backoff factor

        while retries < max_retries:
            try:
                response = requests.post(url + '?key=' + api_key, headers=headers, json=data)
                response.raise_for_status()

                # If the request is successful, parse the response
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No response from Gemini.")
                return "⚠️ No response from Gemini AI."

            except requests.exceptions.RequestException as e:
                if response.status_code == 429:
                    # If rate-limited, back off and retry
                    wait_time = backoff_factor ** retries
                    logging.error(f"Rate-limited. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    logging.error(f"Error querying Gemini: {e}")
                    return f"❌ Error querying Gemini: {e}"

        return "❌ Too many retries. Please try again later."

    def start_system_monitoring(self):
        """ Starts automatic monitoring of RAM every 5 seconds """
        def monitor():
            while True:
                ram = psutil.virtual_memory().percent
                GLib.idle_add(self.ram_label.set_text, f"RAM Usage: {ram}%")
                time.sleep(5)

        threading.Thread(target=monitor, daemon=True).start()

    def start_clipboard_monitoring(self):
        """ Monitors clipboard for changes and stores text globally """
        self.clipboard_history = []
        def monitor_clipboard():
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            last_text = ""
            while True:
                text = clipboard.wait_for_text()
                if text and text != last_text:
                    last_text = text
                    self.clipboard_history.append(text)
                    if len(self.clipboard_history) > 10:  # Limit history to last 10 items
                        self.clipboard_history.pop(0)
                    # Comment out or remove the following line to stop auto-appending
                    # GLib.idle_add(self.append_message, "Clipboard", f"Copied: {text}", "left")
                time.sleep(1)

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
        """ Shows clipboard history in a dialog """
        pass
        # dialog = Gtk.Dialog("Clipboard History", self, 0,
        #                     (Gtk.STOCK_OK, Gtk.ResponseType.OK))
        
        # content_area = dialog.get_content_area()
        # history_text = Gtk.TextView()
        # history_buffer = history_text.get_buffer()
        # for item in reversed(self.clipboard_history):  # Show latest first
        #     history_buffer.insert(history_buffer.get_end_iter(), f"{item}\n\n")
        # history_text.set_editable(False)
        # content_area.add(history_text)
        # content_area.show_all()
        # dialog.run()
        # dialog.destroy()

    def on_workspace_changed(self, window, pspec):
        """ Detects when the workspace changes """
        self.append_message("System", "Detected workspace change!", "left")

    def clear_clipboard(self):
        """ Clears the clipboard content """
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text("", -1)

if __name__ == "__main__":
    win = NexusBot()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
