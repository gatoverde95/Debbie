import os
import sys
import gi
import subprocess
import hashlib
import locale
import json
from translations import _, set_language  # Importamos la función de traducción y el selector de idioma

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk

CONFIG_FILE = "config.json"  # Archivo de configuración

class DebInstaller(Gtk.Window):
    def __init__(self, file_path=None):
        super().__init__(title=_("title"))
        self.set_default_size(600, 400)
        self.set_icon_from_file("debbie.svg")
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Variables internas
        self.package_cache = {}
        self.info_hidden = False
        self.current_file_path = None
        self.is_process_visible = False
        
        # Cargar o crear configuración de idioma
        self.load_or_create_config()
        
        self._setup_ui()
        self._setup_drag_and_drop()
        
        # Cargar el archivo .deb si se proporciona al inicio
        if file_path and os.path.exists(file_path):
            self._load_package(file_path)

    def _setup_ui(self):
        # Configurar HeaderBar
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.props.title = _("title")
        self.header.props.subtitle = _("subtitle")
        
        # Botón para abrir paquetes DEB
        self.open_button = self._create_button("document-open-symbolic", _("open_deb"), self.on_open_clicked)
        self.header.pack_start(self.open_button)
        
        # Botón para cambiar idioma
        self.language_button = self._create_button("preferences-desktop-locale-symbolic", _("Change Language"), self.show_language_selector)
        self.header.pack_end(self.language_button)
        
        # Botón para mostrar "Acerca de"
        self.about_button = self._create_button("help-about-symbolic", _("about"), self.show_about_dialog)
        self.header.pack_end(self.about_button)
        
        self.set_titlebar(self.header)
        
        # Contenedor principal
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._set_margins(self.main_box, 10)
        
        # Panel de información del paquete
        info_frame = Gtk.Frame(label=_("package_info"))
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._set_margins(info_box, 10)
        
        self.file_label = Gtk.Label(label=_("no_file"))
        self.file_label.set_xalign(0)
        info_box.pack_start(self.file_label, False, False, 0)
        
        # Vista de información del paquete
        self.info_view = Gtk.TextView()
        self.info_view.set_editable(False)
        self.info_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.info_buffer = self.info_view.get_buffer()
        
        info_scroll = Gtk.ScrolledWindow()
        info_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        info_scroll.set_min_content_height(150)
        info_scroll.add(self.info_view)
        info_box.pack_start(info_scroll, True, True, 0)
        
        # Botones de información
        info_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        info_button_box.set_halign(Gtk.Align.END)
        
        self.update_button = self._create_button("view-refresh-symbolic", _("update_info"), self.on_update_clicked)
        self.update_button.set_sensitive(False)
        info_button_box.pack_start(self.update_button, False, False, 0)
        
        self.toggle_info_button = self._create_button("view-list-symbolic", _("toggle_info"), self.on_toggle_info_clicked)
        self.toggle_info_button.set_sensitive(False)
        info_button_box.pack_start(self.toggle_info_button, False, False, 0)
        
        info_box.pack_start(info_button_box, False, False, 0)
        info_frame.add(info_box)
        
        # Panel de proceso (inicialmente no visible)
        self.process_frame = Gtk.Frame(label=_("process"))
        self.process_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._set_margins(self.process_box, 10)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.output_buffer = self.output_view.get_buffer()
        
        output_scroll = Gtk.ScrolledWindow()
        output_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        output_scroll.set_min_content_height(150)
        output_scroll.add(self.output_view)
        self.process_box.pack_start(output_scroll, True, True, 0)
        
        self.clear_button = self._create_button("edit-clear-symbolic", _("clear_output"), self.on_clear_output_clicked)
        self.clear_button.set_halign(Gtk.Align.END)
        self.process_box.pack_start(self.clear_button, False, False, 0)
        
        self.process_frame.add(self.process_box)
        
        # Botón de acción principal
        self.action_button = Gtk.Button()
        self.action_button.set_image(Gtk.Image.new_from_icon_name("system-software-install", Gtk.IconSize.BUTTON))
        self.action_button.set_label(_("install"))
        self.action_button.set_always_show_image(True)
        self.action_button.set_sensitive(False)
        self.action_button.connect("clicked", self.on_action_clicked)
        self.action_button.get_style_context().add_class("suggested-action")
        
        # Barra de estado
        self.statusbar = Gtk.Statusbar()
        self.statusbar.push(0, _("ready"))
        
        # Añadir todo al contenedor principal
        self.main_box.pack_start(info_frame, True, True, 0)
        self.main_box.pack_start(self.action_button, False, False, 10)
        self.main_box.pack_start(self.statusbar, False, False, 0)
        
        self.add(self.main_box)

    def _create_button(self, icon_name, tooltip, callback):
        button = Gtk.Button()
        button.set_tooltip_text(tooltip)
        button.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))
        button.connect("clicked", callback)
        return button
        
    def _set_margins(self, widget, margin=10):
        widget.set_margin_top(margin)
        widget.set_margin_bottom(margin)
        widget.set_margin_start(margin)
        widget.set_margin_end(margin)

    def _setup_drag_and_drop(self):
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        target_entry = Gtk.TargetEntry.new("text/uri-list", 0, 0)
        self.drag_dest_set_target_list([target_entry])
        self.connect("drag-data-received", self.on_drag_data_received)
        self.connect("drag-motion", lambda w, ctx, x, y, t: self.statusbar.push(0, "Suelte el archivo .deb para cargarlo"))
        self.connect("drag-leave", lambda w, ctx, t: self.statusbar.push(0, "Listo"))
    
    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):  #pylint: disable=unused-argument
        uris = data.get_uris()
        if not uris:
            return
        
        file_path = self._uri_to_path(uris[0])
        if file_path and file_path.lower().endswith('.deb'):
            self._load_package(file_path)
        else:
            self.statusbar.push(0, "El archivo no es un paquete .deb válido")
    
    def _uri_to_path(self, uri):
        if uri.startswith('file://'):
            import urllib.parse
            path = urllib.parse.unquote(uri[7:])
            if sys.platform == 'win32' and path.startswith('/'):
                path = path[1:]
            return path
        return None
    
    def _load_package(self, file_path):
        self.current_file_path = file_path
        self.file_label.set_text(f"Archivo: {os.path.basename(file_path)}")
        self.update_package_info(file_path)
        self.statusbar.push(0, f"Archivo cargado: {os.path.basename(file_path)}")
    
    def _toggle_process_frame(self, show=True):
        if show and not self.is_process_visible:
            self.main_box.pack_start(self.process_frame, True, True, 0)
            self.process_frame.show_all()
            self.is_process_visible = True
            self.main_box.reorder_child(self.statusbar, -1)
        elif not show and self.is_process_visible:
            self.main_box.remove(self.process_frame)
            self.is_process_visible = False
    
    def on_open_clicked(self, widget):  #pylint: disable=unused-argument
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar un paquete .deb",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        filter_deb = Gtk.FileFilter()
        filter_deb.set_name("Archivos .deb")
        filter_deb.add_pattern("*.deb")
        dialog.add_filter(filter_deb)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self._load_package(dialog.get_filename())
        
        dialog.destroy()
    
    def on_update_clicked(self, widget):  #pylint: disable=unused-argument
        if self.current_file_path:
            self.update_package_info(self.current_file_path, force_update=True)
    
    def on_toggle_info_clicked(self, widget):  #pylint: disable=unused-argument
        if self.info_hidden:
            self._show_full_info()
            self.toggle_info_button.set_image(Gtk.Image.new_from_icon_name("view-list-symbolic", Gtk.IconSize.BUTTON))
            self.toggle_info_button.set_tooltip_text("Ver información resumida")
        else:
            self._show_basic_info()
            self.toggle_info_button.set_image(Gtk.Image.new_from_icon_name("view-paged-symbolic", Gtk.IconSize.BUTTON))
            self.toggle_info_button.set_tooltip_text("Ver información completa")
        self.info_hidden = not self.info_hidden
    
    def _show_basic_info(self):
        if self.current_file_path:
            package_name, package_description, package_version = self._get_package_fields(
                self.current_file_path, ["Package", "Description", "Version"]
            )
            if package_name:
                summary = f"Nombre: {package_name}\nVersión: {package_version}\nDescripción: {package_description}"
                self.info_buffer.set_text(summary)
    
    def _show_full_info(self):
        if self.current_file_path:
            package_hash = self._hash_file(self.current_file_path)
            package_info = self.package_cache.get(package_hash)
            if package_info:
                self.info_buffer.set_text(package_info)
    
    def _hash_file(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def update_package_info(self, file_path, force_update=False):
        self.statusbar.push(0, "Cargando información del paquete...")
        package_hash = self._hash_file(file_path)
        
        if package_hash in self.package_cache and not force_update:
            package_info = self.package_cache[package_hash]
            self.info_buffer.set_text(package_info)
        else:
            try:
                result = subprocess.run(
                    ["dpkg-deb", "--info", file_path],
                    capture_output=True, text=True, check=True
                )
                package_info = result.stdout
                self.info_buffer.set_text(package_info)
                self.package_cache[package_hash] = package_info
            except subprocess.CalledProcessError:
                self._show_dialog("Error", "No se pudo obtener información del paquete.")
                self.statusbar.push(0, "Error al obtener información del paquete")
                return
        
        package_name = self._get_package_field(file_path, "Package")
        if package_name:
            self._update_action_button(package_name)
            self.update_button.set_sensitive(True)
            self.toggle_info_button.set_sensitive(True)
            self.statusbar.push(0, f"Paquete: {package_name}")
    
    def _get_package_field(self, file_path, field):
        try:
            result = subprocess.run(
                ["dpkg-deb", "--field", file_path, field],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def _get_package_fields(self, file_path, fields):
        results = []
        for field in fields:
            results.append(self._get_package_field(file_path, field))
        return results
    
    def _is_package_installed(self, package_name):
        try:
            result = subprocess.run(
                ["dpkg-query", "-W", "--showformat=${Status}", package_name],
                capture_output=True, text=True, check=True
            )
            return "install ok installed" in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def _update_action_button(self, package_name):
        is_installed = self._is_package_installed(package_name)
        ctx = self.action_button.get_style_context()
        
        if is_installed:
            self.action_button.set_label("Desinstalar")
            self.action_button.set_image(Gtk.Image.new_from_icon_name("package-remove", Gtk.IconSize.BUTTON))
            ctx.remove_class("suggested-action")
            ctx.add_class("destructive-action")
        else:
            self.action_button.set_label("Instalar")
            self.action_button.set_image(Gtk.Image.new_from_icon_name("system-software-install", Gtk.IconSize.BUTTON))
            ctx.remove_class("destructive-action")
            ctx.add_class("suggested-action")
        
        self.action_button.set_sensitive(True)
    
    def on_action_clicked(self, widget):  #pylint: disable=unused-argument
        if not self.current_file_path:
            return
        
        package_name = self._get_package_field(self.current_file_path, "Package")
        if not package_name:
            self._show_dialog("Error", "No se pudo determinar el nombre del paquete")
            return
        
        is_installed = self._is_package_installed(package_name)
        
        if is_installed:
            confirm = self._show_confirmation(f"¿Desea desinstalar el paquete {package_name}?")
            if confirm:
                self._toggle_process_frame(True)
                self.statusbar.push(0, "Desinstalando paquete...")
                self._run_command(
                    ["pkexec", "apt", "remove", "-y", package_name],
                    f"Desinstalación de {package_name} completada."
                )
        else:
            self._toggle_process_frame(True)
            self.statusbar.push(0, "Instalando paquete...")
            self._run_command(
                ["pkexec", "bash", "-c", f"dpkg -i \"{self.current_file_path}\" && apt-get install -f -y"],
                "Instalación completada y dependencias resueltas."
            )
        
        GLib.timeout_add(1000, self._update_after_action, package_name)
    
    def _update_after_action(self, package_name):
        self._update_action_button(package_name)
        status = "Paquete desinstalado" if not self._is_package_installed(package_name) else "Paquete instalado correctamente"
        self.statusbar.push(0, status)
        return False
    
    def _run_command(self, command, success_message):
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            for stream, prefix in [(process.stdout, ""), (process.stderr, "ERROR: ")]:
                if stream:
                    for line in iter(stream.readline, ""):
                        if line:
                            self._append_to_output(f"{prefix}{line.strip()}")
                            while Gtk.events_pending():
                                Gtk.main_iteration()
            
            process.wait()
            message = success_message if process.returncode == 0 else f"Error (código {process.returncode})"
            self._append_to_output(message)
            
            GLib.idle_add(self._scroll_output_to_end)
        except Exception as e:
            self._append_to_output(f"Error en el comando: {e}")
    
    def _append_to_output(self, message):
        end_iter = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end_iter, message + "\n")
    
    def _scroll_output_to_end(self):
        scrolled_window = self.output_view.get_parent()
        if isinstance(scrolled_window, Gtk.ScrolledWindow):
            adj = scrolled_window.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
    
    def on_clear_output_clicked(self, widget):  #pylint: disable=unused-argument
        self.output_buffer.set_text("")
        self._toggle_process_frame(False)
    
    def _show_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.set_title(title)
        dialog.run()
        dialog.destroy()
    
    def _show_confirmation(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=message
        )
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES
    
    def get_current_language(self):
        """Obtiene el idioma actual desde translations."""
        from translations import current_language
        return current_language
    
    def toggle_process_frame(self, show=True):
        if show and not self.is_process_visible:
            self.main_box.pack_start(self.process_frame, True, True, 0)
            self.process_frame.show_all()
            self.is_process_visible = True
            self.main_box.reorder_child(self.statusbar, -1)
        elif not show and self.is_process_visible:
            self.main_box.remove(self.process_frame)
            self.is_process_visible = False

    def show_language_selector(self, widget):  # pylint: disable=unused-argument
        """Muestra un selector de idioma."""
        dialog = Gtk.Dialog(
            title=_("Select Language"),
            transient_for=self,
            modal=True
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        content_area = dialog.get_content_area()
        combo = Gtk.ComboBoxText()
        combo.append("en", "English")
        combo.append("es", "Español")
        combo.append("ja", "日本語")
        combo.append("pt", "Português")
        combo.append("de", "Deutsch")
        combo.append("ko", "한국어")
        combo.append("it", "Italiano")
        combo.set_active_id(self.get_current_language())
        content_area.pack_start(combo, False, False, 10)

        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            lang_code = combo.get_active_id()
            set_language(lang_code)
            self.save_config(lang_code)  # Guardar la configuración
            self.refresh_ui()  # Actualizar la interfaz
        dialog.destroy()
    
    def load_or_create_config(self):
        """Carga o crea el archivo de configuración."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
                    config = json.load(config_file)
                    if "language" in config:
                        set_language(config["language"])
                        return
            except Exception as e:
                print(f"Error loading config: {e}")

        # Si no existe el archivo o hay un error, crear configuración predeterminada
        default_language = self.detect_system_language() or "en"
        set_language(default_language)
        self.save_config(default_language)

    def save_config(self, language):
        """Guarda la configuración actual en un archivo JSON."""
        config = {
            "language": language
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
                json.dump(config, config_file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def detect_system_language(self):
        """Detecta el idioma del sistema."""
        system_language, _ = locale.getdefaultlocale()
        if system_language:
            return system_language.split("_")[0]
        return None

    def show_about_dialog(self, widget):  # pylint: disable=unused-argument
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_modal(True)
        about.set_program_name("Debbie")
        about.set_version("2.0")
        about.set_comments(_("about_program"))
        about.set_copyright("© 2025 CuerdOS")
        about.set_website("https://cuerdos.github.io")
        about.set_website_label(_("about_website"))
        about.set_license_type(Gtk.License.GPL_3_0)

        logo_path = "debbie.svg"
        if os.path.exists(logo_path):
            try:
                logo = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 128, 128, True)
                about.set_logo(logo)
            except Exception:
                pass

        about.set_authors(_("about_authors"))
        about.run()
        about.destroy()

    def refresh_ui(self):
        """Recarga los textos de la interfaz en el idioma actual."""
        self.header.props.title = _("title")
        self.header.props.subtitle = _("subtitle")
        self.file_label.set_text(_("no_file"))
        self.update_button.set_label(_("update_info"))
        self.toggle_info_button.set_label(_("toggle_info"))
        self.clear_button.set_label(_("clear_output"))
        self.action_button.set_label(_("install"))
        self.statusbar.push(0, _("ready"))

if __name__ == "__main__":
    if not Gtk.init_check()[0]:
        print("Error al inicializar Gtk")
        sys.exit(1)
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    app = DebInstaller(input_file)
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
