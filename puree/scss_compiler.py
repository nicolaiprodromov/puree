from typing import Dict, Optional
import sass

class SCSSCompiler:
    def __init__(self, injected_vars: Optional[Dict[str, str]] = None):
        pass
        
    def compile(self, scss_content: str, namespace: str = "", param_overrides: Optional[Dict[str, str]] = None, component_name: str = "") -> str:
        if param_overrides:
            var_defs = []
            for key, value in param_overrides.items():
                var_name = key.replace("-", "_")
                if isinstance(value, str):
                    if not value.startswith(('rgb(', 'rgba(', '#', '"', "'")):
                        parts = value.split()
                        if len(parts) > 1:
                            is_css_multi_value = all(
                                part.rstrip('px%emremvwvhptcmmmininchpcexchvminvmax').replace('.', '').replace('-', '').isdigit() or 
                                part in ('auto', 'inherit', 'initial', 'unset')
                                for part in parts
                            )
                            if is_css_multi_value:
                                pass
                            else:
                                value = f'"{value}"'
                        else:
                            stripped = value.rstrip('px%emremvwvhptcmmmininchpcexchvminvmax')
                            try:
                                float(stripped)
                            except ValueError:
                                value = f'"{value}"'
                var_defs.append(f'${var_name}: {value};')
            scss_content = '\n'.join(var_defs) + '\n' + scss_content
        
        compiled_css = sass.compile(string=scss_content)
        
        if namespace:
            compiled_css = self._apply_namespace(compiled_css, namespace, component_name)
        
        return compiled_css
    
    def _apply_namespace(self, css: str, namespace: str, component_base_name: str = "") -> str:
        lines = []
        print(f"[NAMESPACE_INIT] component_base_name='{component_base_name}', namespace='{namespace}'")
        if not component_base_name:
            component_base_name = namespace.split('_')[-1] if '_' in namespace else namespace
            print(f"[NAMESPACE_INIT] Derived base name: '{component_base_name}'")
        
        for line in css.split('\n'):
            line = line.strip()
            if line and not line.startswith(('@', '/*', '}')):
                if '{' in line:
                    selector_part = line.split('{')[0].strip()
                    selectors = [s.strip() for s in selector_part.split(',')]
                    namespaced_selectors = []
                    for selector in selectors:
                        if selector:
                            selector_clean = selector.lstrip('.')
                            print(f"[NAMESPACE] selector='{selector}', base='{component_base_name}', namespace='{namespace}', match={selector_clean == component_base_name}")
                            if selector_clean == component_base_name:
                                namespaced_selectors.append(namespace)
                            elif selector_clean.startswith(component_base_name + '_'):
                                namespaced_selectors.append(selector_clean.replace(component_base_name, namespace, 1))
                            elif not selector_clean.startswith(namespace):
                                namespaced_selectors.append(f'{namespace}_{selector_clean}')
                            else:
                                namespaced_selectors.append(selector_clean)
                    line = ', '.join(namespaced_selectors) + ' {' + line.split('{', 1)[1]
            lines.append(line)
        return '\n'.join(lines)
    
    def compile_file(self, filepath: str, namespace: str = "", param_overrides: Optional[Dict[str, str]] = None, component_name: str = "") -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            scss_content = f.read()
        return self.compile(scss_content, namespace, param_overrides, component_name)
