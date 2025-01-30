import os
import sys
import gi

# Detectar si estamos en Wayland o X11
def detect_graphics_backend():
    session_type = os.getenv('XDG_SESSION_TYPE', '').lower()
    if session_type == 'wayland':
        print("Detectado Wayland")
    else:
        print("Detectado X11, usando backend X11")
        os.environ['GDK_BACKEND'] = 'x11'

# Inicializar GTK
detect_graphics_backend()
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf
import subprocess
import hashlib

# Verificar si Gtk se inicializa correctamente
if not Gtk.init_check()[0]:
    print("Error al inicializar Gtk")
    exit(1)

class DebInstaller(Gtk.Window):
    def __init__(self, deb_file=None):
        super().__init__(title="Debbie de Deb's")
        self.set_default_size(600, 400)
        self.set_resizable(True)
        self.set_icon_from_file("/usr/share/debbie/debbie.svg")

        paned = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        self.create_menu()

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.file_chooser = Gtk.FileChooserButton(title="Seleccionar un paquete .deb")
        self.file_chooser.set_filter(self.create_filter())
        self.file_chooser.connect("file-set", self.on_file_selected)
        info_box.pack_start(self.file_chooser, False, False, 0)

        self.info_view = Gtk.TextView()
        self.info_view.set_editable(False)
        self.info_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.info_buffer = self.info_view.get_buffer()
        info_scrolled_window = Gtk.ScrolledWindow()
        info_scrolled_window.set_vexpand(True)
        info_scrolled_window.set_hexpand(True)
        info_scrolled_window.add(self.info_view)
        info_box.pack_start(info_scrolled_window, True, True, 0)

        # Crear una caja horizontal para los botones de actualizar y mostrar/ocultar información
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.update_button = Gtk.Button(label="Actualizar Información")
        self.update_button.set_sensitive(False)
        self.update_button.connect("clicked", self.on_update_clicked)
        button_box.pack_start(self.update_button, False, False, 0)

        self.hide_info_button = Gtk.Button(label="Ocultar Info. Adicional")
        self.hide_info_button.set_sensitive(False)
        self.hide_info_button.connect("clicked", self.on_hide_info_clicked)
        button_box.pack_start(self.hide_info_button, False, False, 0)

        info_box.pack_start(button_box, False, False, 0)

        paned.pack1(info_box, True, False)

        process_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.output_buffer = self.output_view.get_buffer()
        output_scrolled_window = Gtk.ScrolledWindow()
        output_scrolled_window.set_vexpand(True)
        output_scrolled_window.set_hexpand(True)
        output_scrolled_window.add(self.output_view)
        process_box.pack_start(output_scrolled_window, True, True, 0)

        button_box = Gtk.Box(spacing=6)
        self.install_button = Gtk.Button(label="Instalar")
        self.install_button.set_sensitive(False)
        self.install_button.connect("clicked", self.on_install_clicked)
        button_box.pack_start(self.install_button, True, True, 0)

        self.uninstall_button = Gtk.Button(label="Desinstalar")
        self.uninstall_button.set_sensitive(False)
        self.uninstall_button.connect("clicked", self.on_uninstall_clicked)
        button_box.pack_start(self.uninstall_button, True, True, 0)

        process_box.pack_start(button_box, False, False, 0)
        paned.pack2(process_box, True, False)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.pack_start(self.menubar, False, False, 0)
        main_box.pack_start(paned, True, True, 0)
        self.add(main_box)

        self.package_cache = {}
        self.info_hidden = False

        # Cargar el archivo .deb si se proporciona al inicio
        if deb_file and os.path.exists(deb_file):
            self.file_chooser.set_filename(deb_file)
            self.update_package_info(deb_file)

    def create_menu(self):
        self.menubar = Gtk.MenuBar()

        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="Archivo")
        file_item.set_submenu(file_menu)

        load_item = Gtk.MenuItem(label="Cargar paquete Debian")
        load_item.connect("activate", self.on_load_package)
        file_menu.append(load_item)

        save_item = Gtk.MenuItem(label="Guardar información del paquete")
        save_item.connect("activate", self.on_save_package_info)
        file_menu.append(save_item)

        exit_item = Gtk.MenuItem(label="Salir")
        exit_item.connect("activate", Gtk.main_quit)
        file_menu.append(exit_item)

        help_menu = Gtk.Menu()
        help_item = Gtk.MenuItem(label="Ayuda")
        help_item.set_submenu(help_menu)

        about_item = Gtk.MenuItem(label="Acerca de")
        about_item.connect("activate", self.show_about_dialog)
        help_menu.append(about_item)

        self.menubar.append(file_item)
        self.menubar.append(help_item)

    def on_load_package(self, widget):  # pylint: disable=unused-argument
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar un paquete .deb",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        filter_deb = Gtk.FileFilter()
        filter_deb.set_name("Archivos .deb")
        filter_deb.add_pattern("*.deb")
        dialog.set_filter(filter_deb)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.file_chooser.set_filename(dialog.get_filename())
        dialog.destroy()

    def on_save_package_info(self, widget):  # pylint: disable=unused-argument
        dialog = Gtk.FileChooserDialog(
            title="Guardar información del paquete",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            with open(filename, 'w', encoding='utf-8') as file:
                start_iter = self.info_buffer.get_start_iter()
                end_iter = self.info_buffer.get_end_iter()
                file.write(self.info_buffer.get_text(start_iter, end_iter, True))
        dialog.destroy()

    def show_about_dialog(self, widget):  # pylint: disable=unused-argument
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_program_name("Debbie de Deb's")
        about_dialog.set_version("1.0 v291224a Elena")
        about_dialog.set_comments("Instalador de paquetes para CuerdOS GNU/Linux.")
        about_dialog.set_license_type(Gtk.License.GPL_3_0)
        current_dir = os.getcwd()
        logo_path = os.path.join(current_dir, "/usr/share/debbie/debbie.svg")
        about_dialog.set_authors([
            "Ale D.M ",
            "Leo H. Pérez (GatoVerde95)",
            "Pablo G.",
            "Welkis",
            "GatoVerde95 Studios",
            "CuerdOS Community"
        ])
        about_dialog.set_copyright("© 2025 CuerdOS")
        if os.path.exists(logo_path):
            logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file(logo_path)
            logo_pixbuf = logo_pixbuf.scale_simple(150, 150, GdkPixbuf.InterpType.BILINEAR)
            about_dialog.set_logo(logo_pixbuf)
        about_dialog.run()
        about_dialog.destroy()

    def create_filter(self):
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Archivos .deb")
        file_filter.add_pattern("*.deb")
        return file_filter

    def on_file_selected(self, widget):  # pylint: disable=unused-argument
        file_path = self.file_chooser.get_filename()
        if file_path:
            self.update_package_info(file_path)

    def on_update_clicked(self, widget):  # pylint: disable=unused-argument
        file_path = self.file_chooser.get_filename()
        if file_path:
            self.update_package_info(file_path, force_update=True)

    def on_hide_info_clicked(self, widget):  # pylint: disable=unused-argument
        if self.info_hidden:
            self.show_package_info()
            self.hide_info_button.set_label("Ocultar Info. Adicional")
        else:
            self.hide_package_info()
            self.hide_info_button.set_label("Mostrar Info. Adicional")
        self.info_hidden = not self.info_hidden

    def update_package_info(self, file_path, force_update=False):
        package_hash = self.hash_file(file_path)
        cached_info = self.package_cache.get(package_hash)
        if cached_info and not force_update:
            self.info_buffer.set_text(cached_info)
        else:
            package_info = self.get_package_info(file_path)
            if package_info:
                self.info_buffer.set_text(package_info)
                self.package_cache[package_hash] = package_info
            else:
                self.show_message_dialog("Error", "El paquete .deb no tiene información o no se pudo obtener.")
        package_name = self.extract_package_name(file_path)
        if package_name:
            self.update_buttons(package_name)
            self.update_button.set_sensitive(True)
            self.hide_info_button.set_sensitive(True)

    def hash_file(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def update_buttons(self, package_name):
        if self.is_package_installed(package_name):
            self.install_button.set_sensitive(False)
            self.uninstall_button.set_sensitive(True)
        else:
            self.install_button.set_sensitive(True)
            self.uninstall_button.set_sensitive(False)

    def get_package_info(self, file_path):
        try:
            result = subprocess.run([
                "dpkg-deb", "--info", file_path
            ], capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return None

    def get_package_basic_info(self, file_path):
        try:
            result = subprocess.run([
                "dpkg-deb", "--info", file_path
            ], capture_output=True, text=True, check=True)
            package_name = ""
            package_description = ""
            package_version = ""
            for line in result.stdout.splitlines():
                if line.strip().startswith("Package:"):
                    package_name = line.split("Package:")[1].strip()
                if line.strip().startswith("Description:"):
                    package_description = line.split("Description:")[1].strip()
                if line.strip().startswith("Version:"):
                    package_version = line.split("Version:")[1].strip()
            return package_name, package_description, package_version
        except subprocess.CalledProcessError:
            return None, None, None

    def hide_package_info(self):
        file_path = self.file_chooser.get_filename()
        if file_path:
            package_name, package_description, package_version = self.get_package_basic_info(file_path)
            if package_name and package_description:
                self.info_buffer.set_text(f"Nombre del paquete: {package_name}\nDescripción: {package_description}\nVersión: {package_version}")

    def show_package_info(self):
        file_path = self.file_chooser.get_filename()
        if file_path:
            package_info = self.package_cache.get(self.hash_file(file_path))
            if package_info:
                self.info_buffer.set_text(package_info)

    def on_install_clicked(self, widget):  # pylint: disable=unused-argument
        file_path = self.file_chooser.get_filename()
        if file_path:
            package_name = self.extract_package_name(file_path)
            if self.is_package_installed(package_name):
                self.show_message_dialog("Paquete ya instalado", "El paquete ya está instalado en tu sistema.")
            else:
                self.run_command_with_output(["pkexec", "dpkg", "-i", file_path], "Instalación completada.")
                self.run_command_with_output(["pkexec", "apt-get", "install", "-f", "-y"], "Reparación de dependencias completada.")
                if not self.is_package_installed(package_name):
                    self.show_message_dialog("Error en la instalación", "Se repararon dependencias pero no se instaló el paquete.")
                else:
                    self.show_message_dialog("Instalación exitosa", "El paquete fue instalado correctamente.")
                if package_name:
                    self.update_buttons(package_name)

    def on_uninstall_clicked(self, widget):  # pylint: disable=unused-argument
        package_name = self.extract_package_name(self.file_chooser.get_filename())
        if package_name:
            self.run_command_with_output(["pkexec", "apt", "remove", "-y", package_name], "Desinstalación completada.")
            self.update_buttons(package_name)

    def extract_package_name(self, file_path):
        if not file_path:
            return None
        try:
            result = subprocess.run([
                "dpkg-deb", "--info", file_path
            ], capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                if line.strip().startswith("Package:"):
                    return line.split("Package:")[1].strip()
        except subprocess.CalledProcessError as e:
            print(f"Error al extraer el nombre del paquete: {e}")
        return None

    def is_package_installed(self, package_name):
        try:
            result = subprocess.run([
                "dpkg-query", "-W", "--showformat=${Status}", package_name
            ], capture_output=True, text=True, check=True)
            return "install ok installed" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def run_command_with_output(self, command, success_message):
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in process.stdout or []:
                self.append_to_output(line)
                while Gtk.events_pending():
                    Gtk.main_iteration()
            process.wait()
            if process.returncode == 0:
                self.append_to_output(success_message)
            else:
                self.append_to_output("Error durante el procedimiento.")
        except Exception as e:
            self.append_to_output(f"Error: {e}")

    def append_to_output(self, message):
        end_iter = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end_iter, message + "\n")

    def show_message_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            self, 
            modal=True, 
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.set_title(title)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    deb_file = sys.argv[1] if len(sys.argv) > 1 else None
    app = DebInstaller(deb_file)
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
