# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
# ╔═════════════════════════════════╗
# ║  ██   ██  ██      ██  ████████  ║
# ║   ██ ██   ██  ██  ██       ██   ║
# ║    ███    ██  ██  ██     ██     ║
# ║   ██ ██   ██  ██  ██   ██       ║
# ║  ██   ██   ████████   ████████  ║
# ╚═════════════════════════════════╝
import socket
import json
import sys
import os
import re

def read_manifest():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    addon_dir = os.path.dirname(script_dir)
    manifest_path = os.path.join(addon_dir, 'blender_manifest.toml')
    
    if not os.path.exists(manifest_path):
        print(f'Error: blender_manifest.toml not found at {manifest_path}')
        return None, None, None
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        version_match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        id_match = re.search(r'^id\s*=\s*"([^"]+)"', content, re.MULTILINE)
        
        if not all([name_match, version_match, id_match]):
            print('Error: Could not parse name, version, or id from blender_manifest.toml')
            return None, None, None
        
        addon_name = name_match.group(1).replace(' ', '')
        version = version_match.group(1)
        package_id = id_match.group(1)
        
        return addon_name, version, package_id
        
    except Exception as e:
        print(f'Error reading manifest: {str(e)}')
        return None, None, None

def install_addon(package_file, package_id):
    client = None
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        client.connect(('localhost', 9876))
        
        python_code = f"""import bpy
try:
    result = bpy.ops.extensions.package_install_files(filepath=r'{package_file}', repo='user_default', enable_on_install=True)
    print('Extension {package_id} installed and enabled successfully')
except Exception as e:
    print('Installation failed:', str(e))
    raise e"""
        
        command = {
            "type": "execute_code",
            "params": {
                "code": python_code
            }
        }
        
        message = json.dumps(command) + '\n'
        client.send(message.encode('utf-8'))
        
        response = client.recv(4096).decode('utf-8')
        response_obj = json.loads(response)
        
        if response_obj.get('status') == 'success':
            print('Installation successful!')
            return True
        else:
            print('Installation failed:', response_obj.get('message', 'Unknown error'))
            return False
            
    except ConnectionRefusedError:
        print('Error: Could not connect to Blender MCP server on port 9876')
        print('Make sure Blender is running with the MCP addon enabled')
        return False
    except socket.timeout:
        print('Error: Timeout connecting to Blender MCP server')
        return False
    except Exception as e:
        print(f'Error: {str(e)}')
        return False
    finally:
        if client:
            try:
                client.close()
            except:
                pass

def uninstall_addon(package_id):
    client = None
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)
        client.connect(('localhost', 9876))
        
        python_code = f"""import bpy
try:
    print('Uninstalling extension...')
    
    # Method 1: Try using the extension manager directly
    try:
        import addon_utils
        addon_utils.disable('{package_id}')
    except:
        # Method 2: Try preferences disable
        try:
            bpy.ops.preferences.addon_disable(module='{package_id}')
        except:
            print('Could not disable addon, continuing with uninstall...')
    
    # Method 3: Try to remove via extensions system
    try:
        # Find all repos and try to uninstall from each
        repos = bpy.context.preferences.extensions.repos
        uninstalled = False
        
        for i, repo in enumerate(repos):
            try:
                result = bpy.ops.extensions.package_uninstall(pkg_id='{package_id}', repo_index=i)
                if result == {{'FINISHED'}}:
                    print(f'Extension uninstalled from repo: {{repo.name}} (index {{i}})')
                    uninstalled = True
                    break
            except Exception as e:
                print(f'Failed to uninstall from repo {{repo.name}}: {{str(e)}}')
                continue
        
        if not uninstalled:
            # Try without repo_index
            result = bpy.ops.extensions.package_uninstall(pkg_id='{package_id}')
            if result == {{'FINISHED'}}:
                print('Extension uninstalled successfully')
                uninstalled = True
        
        if not uninstalled:
            print('Warning: Could not uninstall extension, it may not be installed or already removed')
            
    except Exception as e:
        print(f'Uninstall error: {{str(e)}}')
        # Try legacy addon removal as last resort
        try:
            bpy.ops.preferences.addon_remove(module='{package_id}')
            print('Extension removed via legacy method')
        except:
            raise Exception(f'All uninstall methods failed: {{str(e)}}')
            
except Exception as e:
    print('Uninstallation failed:', str(e))
    raise e"""
        
        command = {
            "type": "execute_code",
            "params": {
                "code": python_code
            }
        }
        
        message = json.dumps(command) + '\n'
        client.send(message.encode('utf-8'))
        
        response = client.recv(4096).decode('utf-8')
        response_obj = json.loads(response)
        
        if response_obj.get('status') == 'success':
            print('Uninstallation successful!')
            return True
        else:
            print('Uninstallation failed:', response_obj.get('message', 'Unknown error'))
            return False
            
    except ConnectionRefusedError:
        print('Error: Could not connect to Blender MCP server on port 9876')
        print('Make sure Blender is running with the MCP addon enabled')
        return False
    except socket.timeout:
        print('Error: Timeout connecting to Blender MCP server')
        return False
    except Exception as e:
        print(f'Error: {str(e)}')
        return False
    finally:
        if client:
            try:
                client.close()
            except:
                pass

if __name__ == '__main__':
    action = 'install'  # default action
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action not in ['install', 'uninstall']:
            print('Usage: python install.py [install|uninstall]')
            print('  install   - Install the addon (default)')
            print('  uninstall - Uninstall the addon')
            sys.exit(1)
    
    addon_name, version, package_id = read_manifest()
    if not all([addon_name, version, package_id]):
        sys.exit(1)
    
    success = False
    
    if action == 'install':
        print(f'Installing addon: {addon_name} version {version} (ID: {package_id})')
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        package_file = os.path.join(script_dir, f'{addon_name}_{version}.zip')
        
        if not os.path.exists(package_file):
            print(f'Error: Package file not found: {package_file}')
            print('Please run build.bat first to create the package.')
            sys.exit(1)

        success = install_addon(package_file, package_id)
        
    elif action == 'uninstall':
        print(f'Uninstalling addon: {addon_name} (ID: {package_id})')
        success = uninstall_addon(package_id)
    
    sys.exit(0 if success else 1)