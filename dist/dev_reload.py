#!/usr/bin/env python3
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
"""
Reload the Puree addon in a running Blender instance via the MCP socket.

Clears cached Python modules and re-registers the addon so code changes
take effect without restarting Blender.
"""
import socket
import json
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(f"puree.cli.{os.path.splitext(os.path.basename(__file__))[0]}")
logger.setLevel(logging.DEBUG)
logger.propagate = False
if not logger.handlers:
    _log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _fh = RotatingFileHandler(os.path.join(_log_dir, "puree.log"), maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_fh)
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_ch)


RELOAD_CODE = r"""
import sys, importlib, bpy

addon_module = "bl_ext.user_default.xwz_puree_ui"
mod = sys.modules.get(addon_module)

# 1. Call unregister directly (avoids extension manager reinstalling wheels)
if mod and hasattr(mod, 'unregister'):
    try:
        mod.unregister()
        print("unregister() called")
    except Exception as e:
        print(f"unregister warning: {e}")

# 2. Purge all cached puree modules so Python re-reads from disk
purged = []
for key in list(sys.modules.keys()):
    if key == "puree" or key.startswith("puree."):
        del sys.modules[key]
        purged.append(key)
# Also purge the extension module itself
for key in list(sys.modules.keys()):
    if "xwz_puree_ui" in key:
        del sys.modules[key]
        purged.append(key)

print(f"purged {len(purged)} cached modules")

# 3. Clear __pycache__ bytecode (follows symlinks into source dir)
import pathlib, shutil
for sp in sys.path:
    puree_dir = pathlib.Path(sp) / "puree"
    if puree_dir.exists():
        for cache in puree_dir.rglob("__pycache__"):
            if cache.is_dir() and not cache.is_symlink():
                shutil.rmtree(cache, ignore_errors=True)
                print(f"cleared {cache}")

# 4. Reimport the addon module and call register
try:
    mod = importlib.import_module(addon_module)
    mod.register()
    print("✓ addon reloaded successfully")
except Exception as e:
    print(f"reload error: {e}")
    import traceback
    traceback.print_exc()
    raise
"""


def main():
    client = None
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(15)
        client.connect(('localhost', 9876))

        command = {
            "type": "execute_code",
            "params": {"code": RELOAD_CODE}
        }
        message = json.dumps(command) + '\n'
        client.send(message.encode('utf-8'))

        response = client.recv(16384).decode('utf-8')
        response_obj = json.loads(response)

        if response_obj.get('status') == 'success':
            result = response_obj.get('result', {}).get('result', '')
            if result:
                logger.info(result.strip())
            logger.info('✓ Reload complete')
            return True
        else:
            msg = response_obj.get('message', 'Unknown error')
            logger.error(f'✗ Reload failed: {msg}')
            return False

    except ConnectionRefusedError:
        logger.error('Error: Could not connect to Blender MCP server on port 9876')
        logger.error('Make sure Blender is running with the MCP addon enabled')
        return False
    except socket.timeout:
        logger.error('Error: Timeout — Blender may be busy or the MCP server is not responding')
        return False
    except Exception as e:
        logger.error(f'Error: {e}')
        return False
    finally:
        if client:
            try:
                client.close()
            except:
                pass


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
