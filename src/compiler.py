import importlib
import importlib.util
import os
from time import sleep

class Compiler():
    def __init__(self, ui):
        self.ui = ui
    def compile(self):
        global global_vars
        addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_dir = os.path.join(addon_dir, "static")
        
        for _script_ in self.ui.theme.scripts:
            module_name = _script_.replace(".py", "")
            try:
                script_path = os.path.join(static_dir, f"{module_name}.py")
                spec = importlib.util.spec_from_file_location(module_name, script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'main'):
                    self.ui = module.main(self.ui)
                sleep(0.1)
            except (ImportError, FileNotFoundError) as e:
                print(f"Failed to import {module_name}: {e}")
        return self.ui
