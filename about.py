import gi
import webbrowser

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf


class AboutUs(Gtk.Window):
    def __init__(self):
        super().__init__(title="About Nexus")
        self.set_default_size(300, 280)
        self.set_border_width(10)

        # Main Vertical Box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_halign(Gtk.Align.CENTER)
        self.add(vbox)

        # Logo/Icon (Ensure "icon.png" is in the same folder)
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale("icon.png", 50, 50, True)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            vbox.pack_start(image, False, False, 0)
        except Exception as e:
            print("Icon not found:", e)

        # Title Label
        title_label = Gtk.Label()
        title_label.set_markup("<span font='14' weight='bold'>Nexus</span>")
        vbox.pack_start(title_label, False, False, 2)

        # Description Label
        description_label = Gtk.Label(
            label="Nexus is a modern Linux automation tool for system updates, "
                  "network management, and AI integration."
        )
        description_label.set_line_wrap(True)
        description_label.set_justify(Gtk.Justification.CENTER)
        vbox.pack_start(description_label, False, False, 2)

        # Separator
        vbox.pack_start(Gtk.Separator(), False, False, 2)

        # Info Box (Properly aligned)
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_halign(Gtk.Align.START)  # Aligns to left

        info_label = Gtk.Label()
        info_label.set_markup(
            "<b>Developer:</b> CodeWithAltech\n"
            "<b>University:</b> Victoria University Kampala\n"
            "<b>Stars:</b> 10k⭐\n"
            "<b>Likes:</b> 10k\n"
            "<b>GitHub:</b> <a href='https://github.com/codeWithAltech/'>Nexus</a>"
        )
        info_label.set_line_wrap(True)
        info_label.set_justify(Gtk.Justification.LEFT)
        info_box.pack_start(info_label, False, False, 0)

        vbox.pack_start(info_box, False, False, 2)

        # Like Button (Opens GitHub)
        like_button = Gtk.Button(label="Leave a Star ⭐")
        like_button.connect("clicked", self.on_like_button_clicked)
        vbox.pack_start(like_button, False, False, 2)

        # Separator
        vbox.pack_start(Gtk.Separator(), False, False, 2)

        # Features Label
        features_label = Gtk.Label()
        features_label.set_markup(
            "<b>Key Features:</b>\n"
            "✔ Automatic System Update\n"
            "✔ System Upgrade\n"
            "✔ VU WiFi Networks\n"
            "✔ Personal AI Assistant (WIP)"
        )
        features_label.set_line_wrap(True)
        features_label.set_justify(Gtk.Justification.LEFT)
        vbox.pack_start(features_label, False, False, 2)

        # Close Button
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", self.on_close_clicked)
        vbox.pack_end(close_button, False, False, 2)  # No extra space at the bottom

        self.show_all()

    def on_like_button_clicked(self, button):
        webbrowser.open("https://github.com/codeWithAltech/")

    def on_close_clicked(self, button):
        self.destroy()


if __name__ == "__main__":
    win = AboutUs()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
