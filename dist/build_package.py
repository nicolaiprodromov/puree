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
import os
import sys
import shutil
import glob
import subprocess

def run_command(cmd, shell=True):
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(project_root)
    
    print("\nBuilding Python package")
    
    for tarball in glob.glob("dist/*.tar.gz"):
        os.remove(tarball)
        print(f"Removed {tarball}")
    for old_wheel in glob.glob("dist/puree_ui-*.whl"):
        os.remove(old_wheel)
        print(f"Removed {old_wheel}")
    
    python_cmd = "python" if sys.platform == "win32" else "python3"
    run_command(f"{python_cmd} setup.py sdist bdist_wheel")
    
    wheels_dir = os.path.join(project_root, "wheels")
    os.makedirs(wheels_dir, exist_ok=True)
    
    for old_wheel in glob.glob(os.path.join(wheels_dir, "puree_ui-*.whl")):
        os.remove(old_wheel)
        print(f"Removed old wheel: {os.path.basename(old_wheel)}")
    
    for wheel in glob.glob("dist/puree_ui-*.whl"):
        dest = os.path.join(wheels_dir, os.path.basename(wheel))
        shutil.copy2(wheel, dest)
        print(f"Copied {os.path.basename(wheel)} to wheels/")
    
    if os.path.exists("build"):
        shutil.rmtree("build")
        print("Removed build/")
    
    for egg_info in glob.glob("*.egg-info"):
        shutil.rmtree(egg_info)
        print(f"Removed {egg_info}")
    

if __name__ == "__main__":
    main()
