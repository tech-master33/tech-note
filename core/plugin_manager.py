import importlib.util
import json
import os
import shutil
import sys
import tempfile
import zipfile
from core.config import TECH_SOFT

PLUGIN_DIR = os.path.join(TECH_SOFT, 'plugins')

_plugin_manager_instance = None


def get_plugin_manager():
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = PluginManager()
    return _plugin_manager_instance


class PluginManager:
    def __init__(self):
        self._synth_plugins = {}
        self._braille_plugins = {}
        self._filter_plugins = []
        self._loaded_modules = {}
        self._plugin_infos = {}

    def scan(self):
        self._synth_plugins.clear()
        self._braille_plugins.clear()
        self._filter_plugins.clear()
        self._plugin_infos.clear()
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        for fname in os.listdir(PLUGIN_DIR):
            if fname.endswith('.scrugn'):
                path = os.path.join(PLUGIN_DIR, fname)
                try:
                    self._load_scrugn(path)
                except Exception as e:
                    print(f"Plugin load error {fname}: {e}")

    def _load_scrugn(self, path):
        with zipfile.ZipFile(path, 'r') as z:
            names = z.namelist()
            if 'manifest.json' not in names:
                return
            manifest = json.loads(z.read('manifest.json'))
            plugin_type = manifest.get('plugin_type')
            entry = manifest.get('entry', '__init__.py')
            name = manifest.get('name', os.path.basename(path))
            version = manifest.get('version', '1.0')
            author = manifest.get('author', 'Unknown')
            description = manifest.get('description', '')
            if not plugin_type or not entry:
                return
            if entry not in names:
                return
            self._plugin_infos[name] = {
                'name': name,
                'version': version,
                'author': author,
                'description': description,
                'plugin_type': plugin_type,
                'path': path,
                'filename': os.path.basename(path),
            }
            tmp = tempfile.mkdtemp()
            try:
                z.extractall(tmp)
                spec = importlib.util.spec_from_file_location(
                    f"scrugn_{os.path.basename(path)}",
                    os.path.join(tmp, entry)
                )
                if not spec or not spec.loader:
                    return
                mod = importlib.util.module_from_spec(spec)
                self._loaded_modules[path] = (mod, tmp)
                spec.loader.exec_module(mod)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, self._get_plugin_base(plugin_type)) and attr is not self._get_plugin_base(plugin_type):
                        instance = attr()
                        instance.plugin_name = name
                        instance.plugin_version = version
                        instance.initialize()
                        if plugin_type == 'synth':
                            self._synth_plugins[name] = instance
                        elif plugin_type == 'braille':
                            self._braille_plugins[name] = instance
                        elif plugin_type == 'filter':
                            self._filter_plugins.append(instance)
            except Exception:
                shutil.rmtree(tmp, ignore_errors=True)
                self._loaded_modules.pop(path, None)

    def _get_plugin_base(self, plugin_type):
        from core.plugin_base import SynthPlugin, BrailleDisplayPlugin, FilterPlugin
        return {
            'synth': SynthPlugin,
            'braille': BrailleDisplayPlugin,
            'filter': FilterPlugin,
        }.get(plugin_type)

    def install_plugin(self, src_path):
        if not src_path.endswith('.scrugn'):
            raise ValueError("Not a .scrugn file")
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        dest = os.path.join(PLUGIN_DIR, os.path.basename(src_path))
        shutil.copy2(src_path, dest)
        self._load_scrugn(dest)
        return True

    def uninstall_plugin(self, name):
        info = self._plugin_infos.get(name)
        if not info:
            raise KeyError(f"Plugin '{name}' not found")
        path = info['path']
        if path in self._loaded_modules:
            mod, tmp = self._loaded_modules.pop(path)
            shutil.rmtree(tmp, ignore_errors=True)
        self._synth_plugins.pop(name, None)
        self._braille_plugins.pop(name, None)
        self._filter_plugins[:] = [p for p in self._filter_plugins if p.plugin_name != name]
        self._plugin_infos.pop(name, None)
        if os.path.exists(path):
            os.remove(path)
        return True

    def get_all_plugin_info(self):
        return list(self._plugin_infos.values())

    def get_plugin_info(self, name):
        return self._plugin_infos.get(name)

    def get_synth_plugins(self):
        return dict(self._synth_plugins)

    def get_braille_plugins(self):
        return dict(self._braille_plugins)

    def get_filter_plugins(self):
        return list(self._filter_plugins)

    def shutdown_all(self):
        for plugin in list(self._synth_plugins.values()) + list(self._braille_plugins.values()) + self._filter_plugins:
            try:
                plugin.shutdown()
            except Exception:
                pass
        self._synth_plugins.clear()
        self._braille_plugins.clear()
        self._filter_plugins.clear()
        for path, (mod, tmp) in list(self._loaded_modules.items()):
            shutil.rmtree(tmp, ignore_errors=True)
        self._loaded_modules.clear()
        self._plugin_infos.clear()
