import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3



class HelpDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="Nexus Help")
        self.set_default_size(350, 100)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # Help text
        help_label = Gtk.Label()
        help_label.set_markup(
            "<b>Nexus Help</b>\n\n"
            "For more information and support:\n"
            "• Visit our GitHub repository\n"
            "• Report issues on our issue tracker\n"
            "• Contact us through GitHub discussions\n\n"
            "<a href='https://github.com/'>GitHub Repository</a>"
        )
        help_label.set_line_wrap(True)
        vbox.pack_start(help_label, True, True, 10)

        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        
        cancel_button = Gtk.Button.new_with_label("Cancel")
        cancel_button.connect("clicked", self.on_cancel_clicked)
        
        ok_button = Gtk.Button.new_with_label("OK")
        ok_button.connect("clicked", self.on_ok_clicked)
        
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.pack_start(cancel_button, False, True, 10)
        button_box.pack_start(ok_button, False, True, 2)
        vbox.pack_start(button_box, False, True, 10)

    def on_cancel_clicked(self, button):
        self.destroy()

    def on_ok_clicked(self, button):
        self.destroy()

