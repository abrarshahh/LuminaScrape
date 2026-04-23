import platform
import sys
import os
from typing import Dict

def check_platform() -> Dict:
    """
    Checks the current operating system and environment details.
    Returns recommendations for browser configurations (e.g., Chrome path for Linux).
    
    Returns:
        Dict: OS details and environment recommendations.
    """
    os_name = platform.system() # 'Windows', 'Linux', 'Darwin'
    architecture = platform.machine()
    
    recommendations = {
        "os": os_name,
        "arch": architecture,
        "python_version": sys.version,
        "browser_args": ["--no-sandbox", "--disable-dev-shm-usage"] if os_name == "Linux" else []
    }
    
    # Check for specific Chrome paths on Linux
    if os_name == "Linux":
        chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
        for path in chrome_paths:
            if os.path.exists(path):
                recommendations["chrome_path"] = path
                break
                
    return recommendations

# Usage:
# platform_info = check_platform()
# print(f"Running on {platform_info['os']}")
