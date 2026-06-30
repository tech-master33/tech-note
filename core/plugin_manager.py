import importlib.util
import importlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
import ctypes
import urllib.request
import urllib.error
from core.config import TECH_SOFT
from core.command_registry import get_command_registry

PLUGIN_DIR = os.path.join(TECH_SOFT, 'plugins')
PLUGIN_CATALOG_URL = "https://tech-note.surge.sh/plugin_catalog.json"
PLUGIN_CATALOG_CACHE = os.path.join(TECH_SOFT, "plugin_catalog_cache.json")

_plugin_manager_instance = None


def get_plugin_manager():
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = PluginManager()
    return _plugin_manager_instance


class DependencyError(Exception):
    pass


class PluginManager:
    def __init__(self):
        self._synth_plugins = {}
        self._braille_plugins = {}
        self._filter_plugins = {}
        self._filter_plugin_order = []
        self._dll_plugins = {}
        self._loaded_modules = {}
        self._plugin_infos = {}
        self._plugin_deps = {}
        self._temp_dirs = []
        self._catalog = []

    def scan(self):
        self._synth_plugins.clear()
        self._braille_plugins.clear()
        self._filter_plugins.clear()
        self._filter_plugin_order = []
        self._dll_plugins.clear()
        self._plugin_infos.clear()
        self._plugin_deps.clear()
        for path, (mod, tmp) in list(self._loaded_modules.items()):
            shutil.rmtree(tmp, ignore_errors=True)
        self._loaded_modules.clear()
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        for fname in os.listdir(PLUGIN_DIR):
            path = os.path.join(PLUGIN_DIR, fname)
            try:
                if fname.endswith('.scrugn'):
                    self._load_scrugn(path)
                elif fname.endswith('.pyd'):
                    self._load_pyd_plugin(path)
                elif fname.endswith('.dll'):
                    self._load_dll_plugin(path)
            except Exception as e:
                print(f"Plugin load error {fname}: {e}")
        self._resolve_dependencies()

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
            dependencies = manifest.get('dependencies', [])
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
                'dependencies': dependencies,
            }
            self._plugin_deps[name] = dependencies
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
                        commands = instance.get_commands() if hasattr(instance, 'get_commands') else []
                        for cmd_name, cmd_help, cmd_handler in commands:
                            get_command_registry().register(f"{instance.plugin_name}:{cmd_name}", cmd_help, cmd_handler)
                        if plugin_type == 'synth':
                            self._synth_plugins[name] = instance
                        elif plugin_type == 'braille':
                            self._braille_plugins[name] = instance
                        elif plugin_type == 'filter':
                            self._filter_plugins[name] = instance
                            self._filter_plugin_order.append(name)
            except Exception:
                shutil.rmtree(tmp, ignore_errors=True)
                self._loaded_modules.pop(path, None)

    def _load_pyd_plugin(self, path):
        fname = os.path.basename(path)
        name = os.path.splitext(fname)[0]
        if name in self._plugin_infos:
            return
        try:
            spec = importlib.util.spec_from_file_location(f"pyd_plugin_{name}", path)
            if not spec or not spec.loader:
                return
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._loaded_modules[path] = (mod, "")
            plugin_type = None
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type):
                    for base_name in ('synth', 'braille', 'filter'):
                        base = self._get_plugin_base(base_name)
                        if base and issubclass(attr, base) and attr is not base:
                            plugin_type = base_name
                            break
                if plugin_type:
                    break
            if not plugin_type:
                plugin_type = "native"
            info = {
                'name': name,
                'version': getattr(mod, '__version__', '1.0'),
                'author': getattr(mod, '__author__', 'Unknown'),
                'description': getattr(mod, '__doc__', 'PYD plugin'),
                'plugin_type': plugin_type,
                'path': path,
                'filename': fname,
                'dependencies': [],
            }
            self._plugin_infos[name] = info
            self._plugin_deps[name] = []
            if plugin_type == 'synth':
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, self._get_plugin_base('synth')) and attr is not self._get_plugin_base('synth'):
                        instance = attr()
                        instance.plugin_name = name
                        instance.plugin_version = info['version']
                        instance.initialize()
                        self._synth_plugins[name] = instance
            elif plugin_type == 'braille':
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, self._get_plugin_base('braille')) and attr is not self._get_plugin_base('braille'):
                        instance = attr()
                        instance.plugin_name = name
                        instance.plugin_version = info['version']
                        instance.initialize()
                        self._braille_plugins[name] = instance
            elif plugin_type == 'filter':
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, self._get_plugin_base('filter')) and attr is not self._get_plugin_base('filter'):
                        instance = attr()
                        instance.plugin_name = name
                        instance.plugin_version = info['version']
                        instance.initialize()
                        self._filter_plugins[name] = instance
                        self._filter_plugin_order.append(name)
        except Exception as e:
            print(f"PYD load error {fname}: {e}")

    def _load_dll_plugin(self, path):
        fname = os.path.basename(path)
        name = os.path.splitext(fname)[0]
        if name in self._plugin_infos:
            return
        try:
            dll = ctypes.WinDLL(path)
            self._loaded_modules[path] = (dll, "")
            info = {
                'name': name,
                'version': '1.0',
                'author': 'Unknown',
                'description': f'Native DLL plugin: {fname}',
                'plugin_type': 'native',
                'path': path,
                'filename': fname,
                'dependencies': [],
            }
            self._plugin_infos[name] = info
            self._plugin_deps[name] = []
        except Exception as e:
            print(f"DLL load error {fname}: {e}")

    def _get_plugin_base(self, plugin_type):
        from core.plugin_base import SynthPlugin, BrailleDisplayPlugin, FilterPlugin
        return {
            'synth': SynthPlugin,
            'braille': BrailleDisplayPlugin,
            'filter': FilterPlugin,
        }.get(plugin_type)

    def _resolve_dependencies(self):
        for name, deps in self._plugin_deps.items():
            for dep_name, dep_ver in deps:
                if dep_name not in self._plugin_infos:
                    print(f"Plugin {name}: missing dependency {dep_name}")
                    continue
                info = self._plugin_infos.get(dep_name, {})
                installed_ver = info.get('version', '0')
                if dep_ver and installed_ver != dep_ver and not installed_ver.startswith(dep_ver):
                    print(f"Plugin {name}: dependency {dep_name} version mismatch (need {dep_ver}, have {installed_ver})")

    def _resolve_dependency(self, name, deps):
        for dep_name, dep_ver in deps:
            if dep_name not in self._plugin_infos:
                raise DependencyError(f"Plugin '{name}' requires missing dependency '{dep_name}'")
            info = self._plugin_infos[dep_name]
            installed_ver = info.get('version', '0')
            if dep_ver and installed_ver != dep_ver and not installed_ver.startswith(dep_ver):
                raise DependencyError(f"Plugin '{name}' requires {dep_name} v{dep_ver}, have v{installed_ver}")

    def install_plugin(self, src_path):
        if not src_path.endswith('.scrugn'):
            raise ValueError("Not a .scrugn file")
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        dest = os.path.join(PLUGIN_DIR, os.path.basename(src_path))
        shutil.copy2(src_path, dest)
        self._load_scrugn(dest)
        return True

    def install_dll(self, src_path):
        if not src_path.lower().endswith(('.dll', '.pyd')):
            raise ValueError("Not a DLL or PYD file")
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        dest = os.path.join(PLUGIN_DIR, os.path.basename(src_path))
        shutil.copy2(src_path, dest)
        if src_path.lower().endswith('.pyd'):
            self._load_pyd_plugin(dest)
        else:
            self._load_dll_plugin(dest)
        return True

    def uninstall_plugin(self, name):
        info = self._plugin_infos.get(name)
        if not info:
            raise KeyError(f"Plugin '{name}' not found")
        for other_name, other_deps in self._plugin_deps.items():
            for dep_name, dep_ver in other_deps:
                if dep_name == name:
                    print(f"Warning: '{other_name}' depends on '{name}'; uninstall may break it")
        path = info['path']
        if path in self._loaded_modules:
            mod, tmp = self._loaded_modules.pop(path)
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
        self._synth_plugins.pop(name, None)
        self._braille_plugins.pop(name, None)
        self._filter_plugins.pop(name, None)
        self._filter_plugin_order = [n for n in self._filter_plugin_order if n != name]
        self._dll_plugins.pop(name, None)
        self._plugin_infos.pop(name, None)
        self._plugin_deps.pop(name, None)
        if os.path.exists(path):
            os.remove(path)
        return True

    def reload_plugin(self, name):
        info = self._plugin_infos.get(name)
        if not info:
            raise KeyError(f"Plugin '{name}' not found")
        old_path = info['path']
        if old_path in self._loaded_modules:
            old_mod, old_tmp = self._loaded_modules.pop(old_path)
            if old_tmp:
                shutil.rmtree(old_tmp, ignore_errors=True)
        self._synth_plugins.pop(name, None)
        self._braille_plugins.pop(name, None)
        self._filter_plugins.pop(name, None)
        self._filter_plugin_order = [n for n in self._filter_plugin_order if n != name]
        self._dll_plugins.pop(name, None)
        self._plugin_infos.pop(name, None)
        self._plugin_deps.pop(name, None)
        if os.path.exists(old_path):
            if old_path.endswith('.scrugn'):
                self._load_scrugn(old_path)
            elif old_path.endswith('.pyd'):
                self._load_pyd_plugin(old_path)
            elif old_path.endswith('.dll'):
                self._load_dll_plugin(old_path)
        return name in self._plugin_infos

    def get_all_plugin_info(self):
        return list(self._plugin_infos.values())

    def get_plugin_info(self, name):
        return self._plugin_infos.get(name)

    def get_synth_plugins(self):
        return dict(self._synth_plugins)

    def get_braille_plugins(self):
        return dict(self._braille_plugins)

    def get_filter_plugins(self):
        return [self._filter_plugins[n] for n in self._filter_plugin_order if n in self._filter_plugins]

    def get_dll_plugins(self):
        return {n: info for n, info in self._plugin_infos.items() if info['plugin_type'] == 'native'}

    def shutdown_all(self):
        for plugin in list(self._synth_plugins.values()) + list(self._braille_plugins.values()) + self.get_filter_plugins():
            try:
                plugin.shutdown()
            except Exception:
                pass
        self._synth_plugins.clear()
        self._braille_plugins.clear()
        self._filter_plugins.clear()
        self._filter_plugin_order = []
        self._dll_plugins.clear()
        for path, (mod, tmp) in list(self._loaded_modules.items()):
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
        self._loaded_modules.clear()
        self._plugin_infos.clear()
        self._plugin_deps.clear()

    def fetch_catalog(self):
        try:
            req = urllib.request.Request(PLUGIN_CATALOG_URL, headers={"User-Agent": "TechNote/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            self._catalog = data.get("plugins", [])
            os.makedirs(os.path.dirname(PLUGIN_CATALOG_CACHE), exist_ok=True)
            with open(PLUGIN_CATALOG_CACHE, 'w') as f:
                json.dump(self._catalog, f)
            return self._catalog
        except urllib.error.URLError:
            cached = self._load_catalog_cache()
            if cached:
                self._catalog = cached
            return self._catalog
        except:
            return []

    def _load_catalog_cache(self):
        try:
            if os.path.exists(PLUGIN_CATALOG_CACHE):
                with open(PLUGIN_CATALOG_CACHE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []

    def get_catalog(self):
        if not self._catalog:
            cached = self._load_catalog_cache()
            if cached:
                self._catalog = cached
        return list(self._catalog)

    def install_from_catalog(self, catalog_entry):
        name = catalog_entry.get("name", "Unknown")
        download_url = catalog_entry.get("download_url", "")
        if not download_url:
            raise ValueError("No download URL")
        if not download_url.endswith('.scrugn') and not download_url.lower().endswith(('.pyd', '.dll')):
            raise ValueError("Unsupported plugin format")
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        fname = os.path.basename(download_url)
        dest = os.path.join(PLUGIN_DIR, fname)
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "TechNote/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            tmp = tempfile.NamedTemporaryFile(dir=PLUGIN_DIR, suffix='.tmp', delete=False)
            try:
                tmp.write(data)
                tmp.close()
                shutil.move(tmp.name, dest)
            except:
                os.unlink(tmp.name)
                raise
            if dest.endswith('.scrugn'):
                self._load_scrugn(dest)
            elif dest.endswith('.pyd'):
                self._load_pyd_plugin(dest)
            elif dest.endswith('.dll'):
                self._load_dll_plugin(dest)
            return True
        except urllib.error.URLError:
            raise ValueError("Download failed. No internet.")
        except:
            raise
