import subprocess
import sys
from pathlib import Path
import re

WHEELS_DIR = Path(__file__).parent
WHEELS_DIR.mkdir(exist_ok=True)

PACKAGES = {
    "moderngl": [
        "moderngl==5.12.0",
        "--platform", "win_amd64",
        "--platform", "macosx_11_0_arm64",
        "--platform", "macosx_10_9_x86_64",
        "--platform", "manylinux2014_x86_64"
    ],
    "glcontext": [
        "glcontext==3.0.0",
        "--platform", "win_amd64",
        "--platform", "macosx_11_0_arm64",
        "--platform", "manylinux2014_x86_64"
    ],
    "glcontext-old": [
        "glcontext==2.5.0",
        "--platform", "macosx_10_9_x86_64"
    ],
    "stretchable": [
        "stretchable==1.1.7",
        "--platform", "win_amd64",
        "--platform", "macosx_11_0_arm64",
        "--platform", "manylinux2014_x86_64"
    ],
    "stretchable-old": [
        "stretchable==1.0.0",
        "--platform", "macosx_10_7_x86_64"
    ],
    "toml": ["toml==0.10.2"],
    "attrs": ["attrs==25.3.0"],
    "tinycss2": ["tinycss2==1.4.0"],
    "webencodings": ["webencodings==0.5.1"],
    "textual": ["textual==6.2.1"],
    "rich": ["rich==14.1.0"],
    "pygments": ["pygments==2.19.2"],
    "markdown-it-py": ["markdown-it-py==4.0.0"],
    "mdurl": ["mdurl==0.1.2"],
    "typing-extensions": ["typing-extensions==4.15.0"]
}

PLATFORM_PATTERNS = {
    "win_amd64": r"win_amd64",
    "macosx_11_0_arm64": r"macosx_11_0_arm64",
    "macosx_10_9_x86_64": r"macosx_10_9_x86_64",
    "macosx_10_7_x86_64": r"macosx_10_7_x86_64",
    "manylinux2014_x86_64": r"manylinux.*x86_64"
}

def get_existing_wheels():
    return {wheel.name for wheel in WHEELS_DIR.glob("*.whl")}

def normalize_package_name(name):
    return re.sub(r"[-_.]+", "_", name.lower())

def check_wheel_exists(package_spec, platform, existing_wheels):
    match = re.match(r"([^=]+)==(.+)", package_spec)
    if not match:
        return False
    
    pkg_name = match.group(1)
    version = match.group(2)
    normalized_name = normalize_package_name(pkg_name)
    
    if platform:
        pattern_str = PLATFORM_PATTERNS.get(platform, re.escape(platform))
        for wheel in existing_wheels:
            wheel_lower = wheel.lower()
            if normalized_name in wheel_lower and version in wheel_lower:
                if pattern_str and re.search(pattern_str, wheel_lower):
                    return True
    else:
        for wheel in existing_wheels:
            wheel_lower = wheel.lower()
            if normalized_name in wheel_lower and version in wheel_lower:
                return True
    
    return False

def get_missing_downloads(existing_wheels):
    missing = []
    
    for name, spec_parts in PACKAGES.items():
        package = spec_parts[0]
        
        if len(spec_parts) > 1:
            for i in range(1, len(spec_parts), 2):
                if spec_parts[i] == "--platform":
                    platform = spec_parts[i + 1]
                    if not check_wheel_exists(package, platform, existing_wheels):
                        missing.append((name, package, platform))
        else:
            if not check_wheel_exists(package, None, existing_wheels):
                missing.append((name, package, None))
    
    return missing

def download_wheel(package, platform):
    cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(WHEELS_DIR),
        "--only-binary", ":all:",
        "--python-version", "3.11",
        "--no-deps"
    ]
    
    if platform:
        cmd.extend(["--platform", platform])
    
    cmd.append(package)
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Failed: {e}")
        return False

if __name__ == "__main__":
    print(f"Checking wheels in: {WHEELS_DIR}")
    
    existing_wheels = get_existing_wheels()
    print(f"Found {len(existing_wheels)} existing wheels")
    
    missing = get_missing_downloads(existing_wheels)
    
    if not missing:
        print("\nAll wheels already downloaded!")
    else:
        print(f"\nNeed to download {len(missing)} wheels...\n")
        
        for name, package, platform in missing:
            platform_str = f" ({platform})" if platform else ""
            print(f"Downloading {name}{platform_str}...")
            download_wheel(package, platform)
        
        print("\nDone!")
    
    final_wheels = sorted(WHEELS_DIR.glob("*.whl"))
    print(f"\nTotal wheels: {len(final_wheels)}")
    for wheel in final_wheels:
        print(f"  {wheel.name}")
