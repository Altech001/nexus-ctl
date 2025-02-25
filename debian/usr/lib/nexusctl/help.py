import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import webbrowser

class HelpDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="AL Nexus Help")
        self.set_default_size(500, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Add CSS styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .help-title {
                font-size: 24px;
                font-weight: bold;
                margin: 20px;
                color: #1a5fb4;
            }
            
            .help-section {
                font-size: 16px;
                font-weight: bold;
                margin: 10px;
                color: #1c71d8;
            }
            
            .help-text {
                margin: 10px 20px;
                font-size: 14px;
            }
            
            .help-link {
                color: #3584e4;
            }
            
            .help-button {
                padding: 8px 16px;
                border-radius: 8px;
                background: linear-gradient(145deg, #1a5fb4, #1c71d8);
                color: white;
                font-weight: bold;
            }
            
            .help-button:hover {
                background: linear-gradient(145deg, #1c71d8, #3584e4);
            }
        """)
        
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_halign(Gtk.Align.CENTER)
        
        logo = Gtk.Image.new_from_icon_name("help-about", Gtk.IconSize.DIALOG)
        header_box.pack_start(logo, False, False, 10)
        
        title = Gtk.Label(label="AL Nexus Help")
        title.get_style_context().add_class('help-title')
        header_box.pack_start(title, False, False, 10)
        
        main_box.pack_start(header_box, False, False, 10)

        # Create a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.pack_start(scrolled, True, True, 0)

        # Content box inside scrolled window
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        scrolled.add(content_box)

        # Help sections
        sections = [
            {
                "title": "Getting Started",
                "content": """
• AL Nexus is your system update companion
• Access quick updates from the system tray
• Choose from multiple update methods"""
            },
            {
                "title": "Update Methods",
                "content": """
1. Update & Upgrade (Ctrl+U):
   - Standard update with terminal output
   - Shows detailed progress

2. Silent Update:
   - Updates in background
   - No terminal window
   - Perfect for routine updates

3. Delayed Update:
   - Starts update after 5 seconds
   - Useful for scheduling

4. Auto Update:
   - Enable automatic daily updates
   - Runs in background"""
            },
            {
                "title": "Additional Features",
                "content": """
• Nexus Bot: AI-powered assistance
• Share: Easy sharing options
• System Tray: Quick access to all features"""
            }
        ]

        for section in sections:
            # Section title
            section_title = Gtk.Label()
            section_title.set_markup(f"<b>{section['title']}</b>")
            section_title.set_halign(Gtk.Align.START)
            section_title.get_style_context().add_class('help-section')
            content_box.pack_start(section_title, False, False, 5)

            # Section content
            content_label = Gtk.Label()
            content_label.set_markup(section['content'])
            content_label.set_line_wrap(True)
            content_label.set_halign(Gtk.Align.START)
            content_label.get_style_context().add_class('help-text')
            content_box.pack_start(content_label, False, False, 5)

        # Links section
        links_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        links_box.set_margin_top(10)
        links_box.set_margin_bottom(10)
        
        links = [
            ("GitHub Repository", "https://github.com/altechnology/al-nexus"),
            ("Report Issues", "https://github.com/altechnology/al-nexus/issues"),
            ("Documentation", "https://github.com/altechnology/al-nexus/wiki")
        ]

        for label, url in links:
            link_button = Gtk.LinkButton.new_with_label(url, label)
            link_button.get_style_context().add_class('help-link')
            links_box.pack_start(link_button, False, False, 0)

        content_box.pack_start(links_box, False, False, 10)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(10)
        button_box.set_margin_bottom(10)
        
        close_button = Gtk.Button.new_with_label("Close")
        close_button.get_style_context().add_class('help-button')
        close_button.connect("clicked", self.on_close_clicked)
        
        button_box.pack_start(close_button, False, False, 0)
        main_box.pack_start(button_box, False, False, 0)

    def on_close_clicked(self, button):
        self.destroy()

