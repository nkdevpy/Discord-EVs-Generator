import asyncio
from datetime import datetime
import hashlib
import os
import shutil
from pathlib import Path
import platform
import re
import sys
import threading
import time
import json
import random
import string
import signal
import tempfile
from typing import Optional, Dict
import requests
import httpx
import tls_client
from colorama import Fore, Style, init
from pystyle import Center
from rich.console import Console
import warnings
import nodriver as uc
from nodriver import cdp
import urllib3
import base64
import logging
import ctypes; ctypes.windll.kernel32.SetConsoleTitleW("venumzmail.xyz")
import subprocess
import psutil

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore')
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

async def cdpkey(tab, key: str, code: str, keycode: int):
    try:
        await tab.send(
            cdp.input.dispatchKeyEvent(
                type="keyDown", key=key, code=code,
                windowsVirtualKeyCode=keycode,
                nativeVirtualKeyCode=keycode,
            )
        )
        await asyncio.sleep(0.05)
        await tab.send(
            cdp.input.dispatchKeyEvent(
                type="keyUp", key=key, code=code,
                windowsVirtualKeyCode=keycode,
                nativeVirtualKeyCode=keycode,
            )
        )
    except Exception:
        pass

def getbravepath() -> Optional[str]:
    paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/usr/bin/brave-browser",
        "/usr/bin/brave",
        "/snap/bin/brave",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

bravepath = getbravepath()

if bravepath:
    pass
else:
    print("\033[93m[warn]\033[0m Brave not found — falling back to default Chrome")

nopechadirext = Path(__file__).parent / "nopecha_ext"
nopechakeysfile = Path(__file__).parent / "nopecha_keys.txt"
nopechakeyindex = 0
nopechakeylock = threading.Lock()

def loadnopechakeys() -> list:
    if not nopechakeysfile.exists():
        nopechakeysfile.write_text(
            "# Add your NopeCHA API keys here, one per line\n"
            "# Get keys from https://nopecha.com/setup\n"
        )
        return []
    keys = []
    for line in nopechakeysfile.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            keys.append(line)
    return keys

def getcurrentnopechakey() -> Optional[str]:
    try:
        if isinstance(config, dict):
            nopechaconfig = config.get("nopecha", {})
            if nopechaconfig.get("enabled", False) and nopechaconfig.get("api_key"):
                key = nopechaconfig.get("api_key")
                if key and key != "nopecha-key-here":
                    return key
    except Exception:
        pass
    
    keys = loadnopechakeys()
    if not keys:
        return None
    with nopechakeylock:
        return keys[nopechakeyindex % len(keys)]

def rotatenopechakey():
    global nopechakeyindex
    keys = loadnopechakeys()
    if keys:
        with nopechakeylock:
            nopechakeyindex = (nopechakeyindex + 1) % len(keys)

def injectnopechakey(apikey: str) -> bool:
    if not apikey or not nopechadirext.exists():
        return False
    
    try:
        manifestpath = nopechadirext / "manifest.json"
        if manifestpath.exists():
            with open(manifestpath, 'r') as f:
                manifest = json.load(f)
            if 'nopecha' not in manifest:
                manifest['nopecha'] = {}
            manifest['nopecha']['key'] = apikey
            with open(manifestpath, 'w') as f:
                json.dump(manifest, f, indent=2)
        
        storageinitpath = nopechadirext / "storage_init.js"
        storageinitcode = f"""
(function() {{
  const nopecha_api_key = '{apikey}';
  chrome.storage.local.set({{'nopecha_key': nopecha_api_key}}, function() {{
    console.log('[NopeCHA Storage] API Key initialized');
  }});
}})();
"""
        with open(storageinitpath, 'w') as f:
            f.write(storageinitcode)
        
        configpath = nopechadirext / "nopecha_config.json"
        configdata = {
            'api_key': apikey,
            'enabled': True,
            'timestamp': datetime.now().isoformat()
        }
        with open(configpath, 'w') as f:
            json.dump(configdata, f, indent=2)
        
        return True
    except Exception as e:
        log.warning(f"Inject failed: {e}")
        return False

def downloadnopechaext() -> Optional[Path]:
    if nopechadirext.exists() and (nopechadirext / "manifest.json").exists():
        return nopechadirext
    import zipfile, io
    zipurl = "https://github.com/NopeCHALLC/nopecha-extension/releases/latest/download/chromium_automation.zip"
    try:
        r = requests.get(zipurl, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            log.warning(f"NopeCHA download failed: HTTP {r.status_code}")
            return None
        nopechadirext.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            z.extractall(nopechadirext)
        log.success("NopeCHA extension downloaded!")
        return nopechadirext
    except Exception as e:
        log.warning(f"NopeCHA download error: {e}")
        return None

def generatefingerprint() -> Optional[str]:
    try:
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        }
        response = requests.get(
            "https://discordapp.com/api/v9/experiments",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            fingerprint = data.get('fingerprint')
            if fingerprint:
                return fingerprint
        return None
    except Exception as e:
        log.debug(f"Fingerprint generation error: {e}")
        return None

async def injectfingerprinttopage(page, fingerprint: str) -> bool:
    if not fingerprint:
        return False
    
    installationid = hashlib.md5(fingerprint.encode()).hexdigest()[:16]
    
    js = f'''
    (() => {{
        try {{
            const fingerprintdata = {{
                fingerprint: '{fingerprint}',
                installation: '{installationid}',
                timestamp: {int(time.time()) * 1000}
            }};
            
            window.__discord_fp_data = fingerprintdata;
            window.localStorage.setItem('discord_fp_data', JSON.stringify(fingerprintdata));
            window.localStorage.setItem('discord_fingerprint', '{fingerprint}');
            window.localStorage.setItem('discord_installation_id', '{installationid}');
            
            return true;
        }} catch (e) {{
            return false;
        }}
    }})();
    '''
    try:
        return await page.evaluate(js)
    except Exception as e:
        log.debug(f"Fingerprint injection error: {e}")
        return False

solverurl = "http://127.0.0.1:5003"
solvertimeout = 120

def sendcaptchatosolver(taskid: str, pageurl: str = "https://discord.com/register", captchatype: str = "unknown") -> Optional[str]:
    try:
        payload = {
            'task_id': taskid,
            'type': captchatype,
            'page_url': pageurl
        }
        
        response = requests.post(f'{solverurl}/api/solve', json=payload, timeout=5)
        if response.status_code not in [200, 202]:
            log.warning(f"Solver queue failed: {response.status_code}")
            return None
        
        log.info(f"Captcha task {taskid} sent to solver")
        
        starttime = time.time()
        pollinterval = 2
        while time.time() - starttime < solvertimeout:
            try:
                resultresponse = requests.get(f'{solverurl}/api/result/{taskid}', timeout=5)
                
                if resultresponse.status_code == 200:
                    data = resultresponse.json()
                    if data.get('status') == 'completed':
                        token = data.get('token')
                        log.success(f"Captcha solved: {taskid}")
                        return token
            except:
                pass
            
            time.sleep(pollinterval)
        
        log.warning(f"Solver timeout for {taskid}")
        return None
    
    except Exception as e:
        log.error(f"Solver integration error: {e}")
        return None

def checksolverhealth() -> bool:
    try:
        response = requests.get(f'{solverurl}/api/status', timeout=5)
        return response.status_code == 200
    except:
        return False

jsutils = '''
(() => {
    if (window.utils) return;
    
    function setInput(selector, value) {
        const el = document.querySelector(selector);
        if (el) {
            el.value = value;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }
    
    function clickAllCheckboxes() {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        let clicked = 0;
        checkboxes.forEach(cb => {
            if (!cb.checked) {
                cb.click();
                cb.checked = true;
                clicked++;
            }
        });
        return { clicked: clicked, total: checkboxes.length };
    }
    
    function clickElement(selector) {
        const el = document.querySelector(selector);
        if (el) el.click();
    }
    
    window.utils = {
        setInput,
        clickAllCheckboxes,
        clickElement,
    };
})();
'''

lock = threading.Lock()
sessiontarget = 0
sessioncreated = 0
sessionstop = False
activeworkers = 0
workerlock = threading.Lock()
cooldownseconds = 60

configdir = Path('input')
configpath = configdir / 'config.json'
outputdir = Path('output')
outputdir.mkdir(exist_ok=True)

mullvadstats = {
    'total_rotations': 0,
    'failed_rotations': 0,
    'ip_changes': 0,
    'last_ip': None,
    'last_rotation_time': None,
}

def checkmullvadinstalled() -> bool:
    try:
        result = subprocess.run(
            ['mullvad', 'version'],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def mullvadkillstuckprocess(timeout: int = 30):
    try:
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if 'mullvad' in proc.info['name'].lower():
                    runtime = time.time() - proc.info['create_time']
                    if runtime > timeout:
                        proc.kill()
                        log.warning(f"Killed stuck mullvad process (PID: {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

def mullvadstatus(timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            ['mullvad', 'status'],
            capture_output=True, text=True, timeout=timeout
        )
        status = result.stdout.strip()
        status = re.sub(r'Visible location:[^\r\n]*', '', status, flags=re.IGNORECASE)
        status = re.sub(r'IPv4:[^\r\n]*', '', status, flags=re.IGNORECASE)
        status = re.sub(r'\s{2,}', ' ', status).strip()
        return status
    except subprocess.TimeoutExpired:
        log.warning("mullvad status command timed out")
        mullvadkillstuckprocess()
        return "timeout"
    except Exception:
        return "unknown"

def mullvaddisconnect(timeout: int = 15, max_attempts: int = 15):
    try:
        subprocess.run(
            ['mullvad', 'disconnect'],
            capture_output=True, text=True, timeout=10
        )
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout and attempts < max_attempts:
            status = mullvadstatus(timeout=5)
            if "Disconnected" in status:
                log.info("Mullvad disconnected successfully")
                return
            time.sleep(0.5)
            attempts += 1
        
        if attempts >= max_attempts:
            log.warning(f"Disconnect verification timed out after {attempts} attempts")
    except Exception as e:
        log.warning(f"Mullvad disconnect error: {e}")
        mullvadkillstuckprocess()

def mullvadconnect(country: str = "us", timeout: int = 30, max_attempts: int = 30) -> bool:
    try:
        result = subprocess.run(
            ['mullvad', 'relay', 'set', 'location', country],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            log.warning(f"Failed to set Mullvad location to {country}")
            return False

        subprocess.run(
            ['mullvad', 'relay', 'set', 'tunnel-protocol', 'wireguard'],
            capture_output=True, text=True, timeout=10
        )

        subprocess.run(
            ['mullvad', 'connect'],
            capture_output=True, text=True, timeout=10
        )

        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout and attempts < max_attempts:
            status = mullvadstatus(timeout=5)
            
            if "Connected" in status:
                log.success(f"Mullvad connected to {country}")
                return True
            
            if "Connecting" in status:
                wait_time = 0.5 if attempts < 5 else 1.0
                time.sleep(wait_time)
            else:
                log.debug(f"Mullvad status: {status}")
                time.sleep(1)
            
            attempts += 1
        
        final_status = mullvadstatus(timeout=5)
        log.error(f"Mullvad connection timeout. Final status: {final_status}")
        return False
        
    except subprocess.TimeoutExpired as e:
        log.error(f"Mullvad command timed out: {e}")
        mullvadkillstuckprocess()
        return False
    except Exception as e:
        log.error(f"Mullvad connect error: {e}")
        return False

def mullvadgetip(timeout: int = 15, attempts: int = 3) -> Optional[str]:
    providers = [
        ('https://am.i.mullvad.net/json', 'ip'),
        ('https://api.ipify.org?format=json', 'ip'),
        ('https://ifconfig.me/all.json', 'ip_addr'),
    ]
    
    for attempt in range(attempts):
        for url, key in providers:
            try:
                resp = requests.get(url, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    ip = data.get(key, data.get('ip', None))
                    if ip:
                        return ip
            except Exception:
                continue
        
        if attempt < attempts - 1:
            time.sleep(1)
    
    return None

def mullvadrotate(country: str = "us", max_retries: int = 3, min_rotation_delay: int = 2) -> bool:
    mullvadstats['total_rotations'] += 1
    
    if mullvadstats['last_rotation_time']:
        elapsed = time.time() - mullvadstats['last_rotation_time']
        if elapsed < min_rotation_delay:
            time.sleep(min_rotation_delay - elapsed)
    
    old_ip = mullvadstats['last_ip']
    
    for attempt in range(max_retries):
        try:
            mullvaddisconnect(timeout=15)
            time.sleep(1)
            
            if not mullvadconnect(country, timeout=30):
                if attempt < max_retries - 1:
                    log.warning(f"Rotation attempt {attempt + 1}/{max_retries} failed, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    log.error("Mullvad rotation failed after all retries")
                    mullvadstats['failed_rotations'] += 1
                    return False
            
            time.sleep(1)
            new_ip = mullvadgetip(timeout=15)
            
            if new_ip:
                mullvadstats['last_ip'] = new_ip
                mullvadstats['last_rotation_time'] = time.time()
                
                if old_ip and new_ip == old_ip:
                    log.warning(f"IP did not change: {log.maskip(new_ip)} (retry {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        mullvaddisconnect()
                        continue
                    else:
                        mullvadstats['failed_rotations'] += 1
                        return False
                else:
                    if old_ip:
                        log.success(f"IP rotated: {log.maskip(old_ip)} → {log.maskip(new_ip)}")
                    else:
                        log.success(f"VPN connected — IP: {log.maskip(new_ip)}")
                    mullvadstats['ip_changes'] += 1
                    return True
            else:
                log.warning(f"Could not verify IP (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    mullvadstats['failed_rotations'] += 1
                    return False
        
        except Exception as e:
            log.error(f"Rotation error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                mullvadstats['failed_rotations'] += 1
                return False
    
    return False

mullvadavailable = False

def loadorcreateconfig():
    if not configpath.exists():
        configdir.mkdir(exist_ok=True)
        templateconfig = {
            "threads": 3,
            "cooldown": 15,
            "provider_selection": "venumzmail",
            "email_providers": {
                "venumzmail": {
                    "enabled": True,
                    "api_key": "vz-your-api-key-here",
                    "api_base": "https://api.venumzmail.xyz",
                    "domains": ["lickingpussy.online", "bomboclato.store", "analgex.com", "arewecookedd.com", "goontome.com"]
                }
            },
            "proxy": {"enabled": False, "file": "input/proxies.txt"},
            "nopecha": {"enabled": True, "api_key": "nopecha-key-here"},
            "mullvad": {"enabled": False, "country": "us"}
        }
        with open(configpath, 'w', encoding='utf-8') as f:
            json.dump(templateconfig, f, indent=4)
        print(f"\n\033[93m[config]\033[0m Config created at: {configpath}")
        sys.exit(0)
    with open(configpath, 'r', encoding='utf-8') as f:
        return json.load(f)

config = loadorcreateconfig()
threadcount = config.get("threads", 1)
cooldownseconds = config.get("cooldown", 10)

mullvad_config = config.get("mullvad", {})
if mullvad_config.get("enabled", False):
    if checkmullvadinstalled():
        mullvadavailable = True
        threadcount = 1
        print(f"\033[92m[info]\033[0m Mullvad VPN enabled (country: {mullvad_config.get('country', 'us')})")
    else:
        print("\033[91m[error]\033[0m Mullvad CLI not found! Install Mullvad VPN or disable it in config.")
        sys.exit(1)

if sys.platform == 'win32':
    import ctypes
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

gray = '\033[90m'
green = '\033[92m'
cyan = '\033[96m'
red = '\033[91m'
yellow = '\033[93m'
white = '\033[97m'
reset = '\033[0m'
blue = '\033[94m'
purple = '\033[95m'
magenta = '\033[95m'
orange = '\033[38;5;208m'

class Logger:
    def __init__(self):
        self._lock = threading.Lock()

    def _printinline(self, emoji: str, tag: str, tagcolor: str, message: str):
        ts = datetime.now().strftime('%H:%M:%S')
        with self._lock:
            line = f"{gray}[{ts}]{reset} {tagcolor}{tag:<10}{reset} {gray}│{reset} {white}{message}{reset}\n"
            sys.stdout.write(line)
            sys.stdout.flush()

    def maskemail(self, email: str) -> str:
        if '@' not in email:
            return email
        username, domain = email.split('@', 1)
        masked = (username[:4] if len(username) > 4 else username[0]) + '****'
        return f"{masked}@{domain}"

    def masktoken(self, token: str) -> str:
        return token[:20] + '***' if len(token) > 20 else token

    def maskip(self, ip: str) -> str:
        if not ip:
            return ip
        if ':' in ip:
            parts = ip.split(':')
            if len(parts) >= 3:
                masked_middle = ':'.join('****' for _ in parts[1:-1])
                return f"{parts[0]}:{masked_middle}:{parts[-1]}"
            return ':'.join(parts[:1] + ['****'])
        if '.' in ip:
            parts = ip.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.***.***.{parts[3]}"
            if len(parts) == 2:
                return f"{parts[0]}.***"
        return re.sub(r'[0-9]', '*', ip)

    def hunt(self, message: str):
        self._printinline("", "HUNT", cyan, message)

    def solved(self, message: str):
        self._printinline("", "SOLVED", magenta, message)

    def warning(self, message: str):
        self._printinline("", "WARNING", yellow, message)

    def error(self, message: str):
        self._printinline("", "ERROR", red, message)

    def info(self, message: str):
        self._printinline("", "INFO", blue, message)

    def success(self, message: str):
        self._printinline("", "SUCCESS", green, message)

    def debug(self, message: str):
        self._printinline("", "DEBUG", gray, message)

    def batch(self, message: str):
        self._printinline("", "BATCH", cyan, message)

    def tokenstatus(self, status: str):
        colormap = {'VALID': green, 'LOCKED': yellow, 'INVALID': red}
        color = colormap.get(status, white)
        ts = datetime.now().strftime('%H:%M:%S')
        with self._lock:
            line = f"{color}TOKEN{reset:<7} {gray}│{reset} {color}[{status}]{reset} {gray}[{ts}]{reset}\n"
            sys.stdout.write(line)
            sys.stdout.flush()

log = Logger()

class VenumzMailAPI:
    def __init__(self, apikey: str, domain: str = None, apibase: str = None):
        self.apikey = apikey
        self.baseurl = apibase or "https://api.venumzmail.xyz"
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'Content-Type': 'application/json',
            'x-api-key': self.apikey
        })
    
    def generateemail(self, username: str = None, domain: str = None) -> dict:
        if not username:
            adjectives = ['cool', 'epic', 'super', 'mega', 'ultra', 'pro', 'elite', 'master', 'dark', 'light', 'shadow', 'fire', 'ice', 'storm', 'thunder', 'wild', 'crazy', 'fast', 'smart', 'great', 'best', 'top', 'king', 'queen', 'lord', 'sir', 'dame', 'captain', 'general', 'chief', 'major', 'agent', 'spy', 'hunter', 'scout', 'ranger', 'knight', 'wizard', 'mage', 'druid', 'rogue', 'bard', 'cleric', 'paladin', 'warrior', 'berserker', 'guardian', 'sentinel', 'watcher', 'keeper', 'warden']
            nouns = ['gamer', 'player', 'user', 'hero', 'legend', 'champion', 'warrior', 'hunter', 'ranger', 'knight', 'mage', 'rogue', 'bard', 'druid', 'cleric', 'paladin', 'berserker', 'guardian', 'sentinel', 'watcher', 'keeper', 'warden', 'dragon', 'phoenix', 'wolf', 'tiger', 'lion', 'hawk', 'eagle', 'raven', 'falcon', 'viper', 'cobra', 'python', 'shark', 'dolphin', 'whale', 'bear', 'panda', 'fox', 'deer', 'stag', 'horse', 'unicorn', 'pegasus', 'griffin', 'chimera', 'hydra', 'behemoth', 'leviathan', 'zephyr', 'tempest', 'cyclone', 'hurricane', 'typhoon', 'blizzard', 'avalanche', 'volcano', 'earthquake', 'tsunami']
            
            username = f"{random.choice(adjectives)}{random.choice(nouns)}{random.randint(10, 9999)}"
        
        usedomain = domain or "lickingpussy.online"
        
        payload = {
            "count": 1,
            "username": username,
            "domain": usedomain,
            "type": "public"
        }
        
        try:
            resp = self.session.post(f"{self.baseurl}/create", json=payload, timeout=30)
            
            if resp.status_code in [200, 201]:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        if data.get("success") or data.get("status") == "success":
                            email = f"{username}@{usedomain}"
                            return {
                                "success": True,
                                "email": email,
                                "username": username,
                                "domain": usedomain
                            }
                        elif data.get("message") == "Email created successfully":
                            email = f"{username}@{usedomain}"
                            return {
                                "success": True,
                                "email": email,
                                "username": username,
                                "domain": usedomain
                            }
                        elif data.get("email"):
                            return {
                                "success": True,
                                "email": data.get("email"),
                                "username": username,
                                "domain": usedomain
                            }
                        elif data.get("inboxes") and len(data["inboxes"]) > 0:
                            email = data["inboxes"][0].get("email")
                            if email:
                                return {
                                    "success": True,
                                    "email": email,
                                    "username": username,
                                    "domain": usedomain
                                }
                        else:
                            email = f"{username}@{usedomain}"
                            return {
                                "success": True,
                                "email": email,
                                "username": username,
                                "domain": usedomain
                            }
                except json.JSONDecodeError:
                    if resp.status_code == 201:
                        email = f"{username}@{usedomain}"
                        return {
                            "success": True,
                            "email": email,
                            "username": username,
                            "domain": usedomain
                        }
                    return {"success": False, "error": f"Invalid JSON response: {resp.text[:100]}"}
            
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:100]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def getinbox(self, email: str) -> list:
        try:
            resp = self.session.get(f"{self.baseurl}/inbox/{email}", timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and data.get("messages"):
                    return data.get("messages", [])
                elif isinstance(data, dict) and data.get("emails"):
                    return data.get("emails", [])
            return []
        except Exception:
            return []

def getvenumzmailemail(config: dict) -> tuple:
    vconfig = config.get("email_providers", {}).get("venumzmail", {})
    if not vconfig:
        vconfig = config.get("email_provider", {})
    
    apikey = vconfig.get("api_key", "").strip()
    if not apikey:
        log.warning("No VenumzMail api_key configured")
        return None, None, None, None
    
    domainslist = vconfig.get("domains", ["lickingpussy.online"])
    domain = random.choice(domainslist)
    apibase = vconfig.get("api_base", "https://api.venumzmail.xyz")
    
    for attempt in range(3):
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(12, 18)))
        
        payload = {
            "count": 1,
            "username": username,
            "domain": domain,
            "type": "public"
        }
        
        try:
            session = requests.Session()
            session.verify = False
            session.headers.update({
                'Content-Type': 'application/json',
                'x-api-key': apikey
            })
            
            resp = session.post(f"{apibase}/create", json=payload, timeout=60)
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                if data.get("inboxes") and len(data["inboxes"]) > 0:
                    email = data["inboxes"][0].get("email")
                    if email:
                        log.success(f"✓ Got VenumzMail: {log.maskemail(email)}")
                        return (email, "", apikey, domain)
                email = f"{username}@{domain}"
                log.success(f"✓ Got VenumzMail: {log.maskemail(email)}")
                return (email, "", apikey, domain)
            else:
                log.debug(f"Attempt {attempt + 1} failed: HTTP {resp.status_code}")
        except Exception as e:
            log.debug(f"Attempt {attempt + 1} failed: {e}")
            continue
    
    log.error(f"VenumzMail error: All attempts failed")
    return None, None, None, None

def getemailfromprovider(config: dict) -> tuple:
    email, password, token, uuid = getvenumzmailemail(config)
    if email:
        return email, password, token, uuid, "venumzmail"
    
    log.error("No email provider available or all failed")
    return None, None, None, None, None

def generateusername() -> str:
    adjectives = ['cool', 'epic', 'super', 'mega', 'ultra', 'pro', 'elite', 'master', 'dark', 'light', 'shadow', 'fire', 'ice', 'storm', 'thunder', 'wild', 'crazy', 'fast', 'smart', 'great', 'best', 'top', 'king', 'queen', 'lord', 'sir', 'dame', 'captain', 'general', 'chief', 'major', 'agent', 'spy', 'hunter', 'scout', 'ranger', 'knight', 'wizard', 'mage', 'druid', 'rogue', 'bard', 'cleric', 'paladin', 'warrior', 'berserker', 'guardian', 'sentinel', 'watcher', 'keeper', 'warden']
    nouns = ['gamer', 'player', 'user', 'hero', 'legend', 'champion', 'warrior', 'hunter', 'ranger', 'knight', 'mage', 'rogue', 'bard', 'druid', 'cleric', 'paladin', 'berserker', 'guardian', 'sentinel', 'watcher', 'keeper', 'warden', 'dragon', 'phoenix', 'wolf', 'tiger', 'lion', 'hawk', 'eagle', 'raven', 'falcon', 'viper', 'cobra', 'python', 'shark', 'dolphin', 'whale', 'bear', 'panda', 'fox', 'deer', 'stag', 'horse', 'unicorn', 'pegasus', 'griffin', 'chimera', 'hydra', 'behemoth', 'leviathan', 'zephyr', 'tempest', 'cyclone', 'hurricane', 'typhoon', 'blizzard', 'avalanche', 'volcano', 'earthquake', 'tsunami']
    
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    numbers = ''.join(str(random.randint(0, 9)) for _ in range(10))
    
    return f"{adj}{noun}{numbers}"

def generatepassword(length: int = 16) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choices(chars, k=length))
    if not any(c.isupper() for c in password):
        password = password[:1].upper() + password[1:]
    if not any(c.isdigit() for c in password):
        password = password[:-1] + str(random.randint(0, 9))
    return password

def generateformpassword(minlength: int = 8) -> str:
    length = max(minlength, 8)
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    password = ''.join(random.choices(chars, k=length))
    if not any(c.isupper() for c in password):
        password = random.choice(string.ascii_uppercase) + password[1:]
    if not any(c.isdigit() for c in password):
        password = password[:-1] + random.choice(string.digits)
    return password

def checktoken(token: str, proxyconfig: Dict = None) -> str:
    try:
        session = tls_client.Session(client_identifier="chrome_138")
        if proxyconfig:
            proxydict = getsessionproxy(proxyconfig)
            if proxydict:
                session.proxies = proxydict
        headers = {'Authorization': token}
        response = session.get('https://discordapp.com/api/v9/users/@me/library', headers=headers)
        if response.status_code == 200:
            return 'VALID'
        elif response.status_code == 403:
            return 'LOCKED'
        elif response.status_code == 401:
            return 'INVALID'
        else:
            return 'INVALID'
    except:
        return 'ERROR'

def saveaccounttofile(email: str, password: str, token: str, status: str):
    try:
        if status == 'VALID':
            outputfile = outputdir / "valid.txt"
        elif status == 'LOCKED':
            outputfile = outputdir / "locked.txt"
        else:
            outputfile = outputdir / "invalid.txt"
        with lock:
            with open(outputfile, 'a', encoding='utf-8') as f:
                f.write(f"{email}:{password}:{token}\n")
        log.success(f"Saved to {outputfile.name}")
    except Exception as e:
        log.error(f"Save failed: {e}")

def checkemailverifiedapi(token: str, proxyconfig: Dict = None):
    try:
        session = tls_client.Session(client_identifier="chrome_138")
        if proxyconfig:
            proxydict = getsessionproxy(proxyconfig)
            if proxydict:
                session.proxies = proxydict
        headers = {'Authorization': token}
        response = session.get('https://discord.com/api/v9/users/@me', headers=headers)
        if response.status_code == 200:
            return response.json().get('verified', False), response.json().get('email', 'N/A')
        return None, None
    except:
        return None, None

async def filldateofbirth(page):
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    day = str(random.randint(1, 28))
    month = random.choice(months)
    year = str(random.randint(1998,2004))
    
    try:
        result = await page.evaluate(f'''
        (async () => {{
            async function setDobField(label, value) {{
                const el = document.querySelector(`div[aria-label="${{label}}"]`);
                if (!el) return false;
                el.click();
                await new Promise(r => setTimeout(r, 100));
                
                for (let i = 0; i < value.length; i++) {{
                    const char = value[i];
                    document.activeElement.dispatchEvent(new KeyboardEvent('keydown', {{
                        key: char,
                        code: isNaN(char) ? 'Key' + char.toUpperCase() : 'Digit' + char,
                        keyCode: char.toUpperCase().charCodeAt(0),
                        bubbles: true
                    }}));
                    await new Promise(r => setTimeout(r, 50));
                }}
                
                await new Promise(r => setTimeout(r, 100));
                
                document.activeElement.dispatchEvent(new KeyboardEvent('keydown', {{
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    bubbles: true
                }}));
                
                await new Promise(r => setTimeout(r, 100));
                return true;
            }}

            const m = await setDobField("Month", "{month}");
            if (!m) return {{ success: false, error: "Month field not found" }};
            
            const d = await setDobField("Day", "{day}");
            if (!d) return {{ success: false, error: "Day field not found" }};
            
            const y = await setDobField("Year", "{year}");
            if (!y) return {{ success: false, error: "Year field not found" }};
            
            document.body.click();
            await new Promise(r => setTimeout(r, 150));
            
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {{
                const text = btn.textContent || '';
                if (text.includes('Continue') || text.includes('Create') || text.includes('Submit') || text.includes('Register')) {{
                    btn.click();
                    break;
                }}
            }}
            
            return {{ success: true }};
        }})()
        ''')
        
        if result and isinstance(result, dict) and result.get('success'):
            log.success(f"DOB: {month} {day}, {year}")
        else:
            log.debug(f"DOB failed: {result}")

    except Exception as e:
        log.debug(f"DOB error: {e}")

async def fillregistrationform(page, email: str, displayname: str, username: str, password: str) -> bool:
    try:
        emailelement = await page.wait_for('input[name="email"]', timeout=10000)
        await emailelement.send_keys(email)
        await asyncio.sleep(0.1)
        
        displayelement = await page.wait_for('input[name="global_name"]', timeout=5000)
        await displayelement.send_keys(displayname)
        await asyncio.sleep(0.1)
        
        usernameelement = await page.wait_for('input[name="username"]', timeout=5000)
        await usernameelement.send_keys(username)
        await asyncio.sleep(0.1)
        
        passwordelement = None
        selectors = [
            'input[aria-label="Password"]',
            'input[name="password"]',
            'input[type="password"]'
        ]
        
        for selector in selectors:
            try:
                passwordelement = await page.query_selector(selector)
                if passwordelement:
                    break
            except:
                continue
        
        if passwordelement:
            await passwordelement.send_keys(password)
            await asyncio.sleep(0.2)
        
        await asyncio.sleep(0.2)
        await filldateofbirth(page)
        await asyncio.sleep(0.1)
        
        try:
            await page.evaluate(jsutils)
            await asyncio.sleep(0.1)
            result = await page.evaluate('window.utils.clickAllCheckboxes()')
            if result and result.get('clicked', 0) > 0:
                log.success(f"✓ Clicked {result.get('clicked')} checkbox(es)")
        except Exception as e:
            pass
        
        clicked = False
        await asyncio.sleep(0.3)
        
        try:
            buttons = await page.query_selector_all('button')
            for button in buttons:
                try:
                    text = await button.get('textContent') or ""
                    if text and any(keyword in text for keyword in ['Continue', 'Create', 'Submit', 'Register']):
                        await button.click()
                        clicked = True
                        break
                except:
                    continue
        except:
            pass
        
        if not clicked:
            try:
                submit = await page.query_selector('[type="submit"]')
                if submit:
                    await submit.click()
                    clicked = True
            except:
                pass
        
        if not clicked:
            try:
                clicked = await page.evaluate('''() => {
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('Continue') || text.includes('Create') || text.includes('Submit')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                if clicked:
                    log.success("Clicked submit via evaluate")
            except:
                pass
        
        if not clicked:
            log.error("Could not find submit button")
            return False
        
        log.success("✓ Form submitted!")
        return True
        
    except Exception as e:
        log.error(f"Form fill error: {e}")
        return False

async def waitforaccountcreation(page, timeout: int = 300) -> bool:
    starttime = time.time()
    lasturl = ""

    while (time.time() - starttime) < timeout:
        await asyncio.sleep(0.5)

        try:
            try:
                currenturl = await page.evaluate('window.location.href')
                if hasattr(currenturl, 'value'):
                    currenturl = currenturl.value or ""
                elif isinstance(currenturl, tuple):
                    currenturl = str(currenturl[0]) if currenturl[0] else ""
                else:
                    currenturl = str(currenturl) if currenturl else ""
            except Exception:
                currenturl = ""

            if currenturl and currenturl != lasturl:
                lasturl = currenturl

            if not currenturl:
                continue

            skip = ['discord.com/register', 'discord.com/login', 'about:blank', 'chrome://']
            if 'discord.com' in currenturl and not any(s in currenturl for s in skip):
                return True

        except Exception as e:
            pass

    log.error("Timeout waiting for account creation")
    return False

async def fetchdiscordtoken(email: str, password: str, proxyconfig: Dict = None) -> str:
    url = "https://discord.com/api/v9/auth/login"
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    payload = {"login": email, "password": password}
    session = tls_client.Session(client_identifier="chrome_131", random_tls_extension_order=True)
    if proxyconfig:
        proxydict = getsessionproxy(proxyconfig)
        if proxydict:
            session.proxies = proxydict
    try:
        response = session.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return ""
        return response.json().get("token", "")
    except:
        return ""

async def waitfordiscordtoken(page, timeout: int = 30, email: str = None, password: str = None, proxyconfig: Dict = None):
    if not email or not password:
        log.error("Email and password required")
        return None
    
    await asyncio.sleep(3)
    
    attempts = 0
    maxattempts = 5
    
    while attempts < maxattempts:
        attempts += 1
        try:
            token = await fetchdiscordtoken(email, password, proxyconfig)
            if token:
                return token
        except Exception as e:
            pass
        
        await asyncio.sleep(3)
    
    log.error("Could not fetch token")
    return None

def parseproxy(proxystring: str) -> Optional[Dict]:
    if not proxystring:
        return None
    proxystring = proxystring.strip()
    if '://' not in proxystring:
        proxystring = 'socks5://' + proxystring
    try:
        from urllib.parse import urlparse
        parsed = urlparse(proxystring)
        proxytype = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            return None
        fullurl = proxystring
        maskedurl = proxystring
        if parsed.username and parsed.password:
            maskedurl = f"{proxytype}://{parsed.username}:***@{host}:{port}"
        return {
            'type': proxytype,
            'host': host,
            'port': port,
            'full_url': fullurl,
            'masked_url': maskedurl,
        }
    except Exception:
        return None

def getbrowserproxyargs(proxyconfig: Dict) -> list:
    args = []
    if not proxyconfig:
        return args
    fullurl = proxyconfig.get('full_url')
    if fullurl:
        args.append(f'--proxy-server={fullurl}')
        args.append('--proxy-bypass-list=<-loopback>')
    return args

def getsessionproxy(proxyconfig: Dict) -> Optional[Dict]:
    if not proxyconfig:
        return None
    fullurl = proxyconfig.get('full_url')
    if fullurl:
        return {'http': fullurl, 'https': fullurl}
    return None

def loadproxies(config: dict) -> list:
    proxyconfig = config.get("proxy", {})
    if not proxyconfig.get("enabled", False):
        return []
    proxyfile = proxyconfig.get("file", "input/proxies.txt")
    proxypath = Path(proxyfile)
    if not proxypath.exists():
        log.warning(f"Proxy file not found: {proxyfile}")
        return []
    try:
        proxies = []
        with open(proxypath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parsed = parseproxy(line)
                    if parsed:
                        proxies.append(parsed)
        if proxies:
            log.success(f"Loaded {len(proxies)} proxies")
            return proxies
    except Exception as e:
        log.error(f"Error loading proxies: {e}")
    return []

proxylist = []
proxylistlock = threading.Lock()

def getrandomproxy() -> Optional[Dict]:
    with proxylistlock:
        if not proxylist:
            return None
        return random.choice(proxylist)

async def verifyemailvenumzmail(email: str, apikey: str, browser, token: str, domain: str = None, apibase: str = None, timeout: int = 60) -> bool:
    api = VenumzMailAPI(apikey=apikey, domain=domain, apibase=apibase)
    starttime = time.time()
    
    while (time.time() - starttime) < timeout:
        try:
            resp = api.session.get(f"{api.baseurl}/inbox/{email}", timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                messages = data.get("messages", [])
                
                if not messages:
                    await asyncio.sleep(5)
                    continue
                
                for msg in messages:
                    sender = msg.get("sender", "").lower()
                    subject = msg.get("subject", "").lower()
                    
                    if "discord" not in sender and "discord" not in subject:
                        continue
                    
                    if "verify" not in subject and "confirm" not in subject and "email" not in subject:
                        continue
                    
                    log.success(f"Found Discord verification email from {sender}")
                    
                    body = msg.get("body", "")
                    bodyhtml = msg.get("body_html", "")
                    combined = body + " " + bodyhtml
                    
                    verifypattern = r'https?://discord\.com/verify\?token=[a-zA-Z0-9_\-\.]+'
                    match = re.search(verifypattern, combined)
                    
                    if match:
                        verifyurl = match.group(0)
                        log.success(f"Found verification URL!")
                        return await verifyemailwithurl(browser, verifyurl, token)
                    
                    clickpatterns = [
                        r'https?://click\.discord\.com/ls/click\?[^\s"\'<>]+',
                        r'https?://links\.discord\.com[^\s"\'<>]+',
                        r'https?://cdn\.discordapp\.com[^\s"\'<>]+'
                    ]
                    
                    for pattern in clickpatterns:
                        for match in re.finditer(pattern, combined):
                            url = match.group(0)
                            try:
                                sessionreq = requests.Session()
                                sessionreq.verify = False
                                respreq = sessionreq.get(url, allow_redirects=True, timeout=10)
                                finalurl = respreq.url
                                
                                if "discord.com/verify" in finalurl:
                                    log.success("Found verification URL via redirect!")
                                    return await verifyemailwithurl(browser, finalurl, token)
                                
                                verifyinbody = re.search(r'https?://discord\.com/verify\?token=[a-zA-Z0-9_\-\.]+', respreq.text)
                                if verifyinbody:
                                    log.success("Found verification URL in redirect response!")
                                    return await verifyemailwithurl(browser, verifyinbody.group(0), token)
                            except Exception:
                                continue
                    
                    tokenpattern = r'token[=:][\s]*["\']?([a-zA-Z0-9_\-\.]+)["\']?'
                    tokenmatch = re.search(tokenpattern, combined, re.IGNORECASE)
                    if tokenmatch:
                        extractedtoken = tokenmatch.group(1)
                        if '.' in extractedtoken and len(extractedtoken) > 50:
                            verifyurl = f"https://discord.com/verify?token={extractedtoken}"
                            log.success("Found verification token in email!")
                            return await verifyemailwithurl(browser, verifyurl, token)
                    
                    log.warning("Discord email found but no verification URL extracted")
            
            await asyncio.sleep(5)
            
        except Exception as e:
            log.debug(f"VenumzMail check error: {e}")
            await asyncio.sleep(5)
    
    log.warning(f"Discord verification email not found after {timeout} seconds")
    return False

async def verifyemailwithurl(browser, verifyurl: str, token: str, timeout: int = 60) -> bool:
    if not verifyurl:
        return False
    
    try:
        page = await browser.get(verifyurl)
        await asyncio.sleep(5)
        
        for _ in range(timeout // 5):
            await asyncio.sleep(5)
            verified, _ = checkemailverifiedapi(token)
            if verified:
                return True
        
        return True
    except Exception as e:
        log.warning(f"Error opening verification URL: {e}")
        return False

async def worker(workerid: int, proxyconfig: Dict = None):
    global sessioncreated, sessionstop, activeworkers

    if sessionstop:
        return

    with workerlock:
        activeworkers += 1

    browser = None
    tempprofile = None

    try:
        if mullvadavailable:
            country = config.get("mullvad", {}).get("country", "us")
            if not mullvadrotate(country):
                log.error("Mullvad rotate failed, skipping")
                return

        fingerprint = generatefingerprint()
        if fingerprint:
            log.success(f"Fingerprint generated: {fingerprint[:20]}...")
        else:
            log.warning("Could not generate fingerprint, continuing without")

        firstnames = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Sam', 'Blake', 'Drew', 'Avery', 'Jamie', 'Parker', 'Cameron', 'Dakota', 'Skyler', 'Quinn', 'Reese', 'Sage', 'River', 'Phoenix', 'Devon', 'Adrian', 'Bailey', 'Chase', 'Dakota', 'Ellis', 'Finley', 'Gray', 'Harper', 'Indigo', 'Jackie', 'Kennedy', 'Logan', 'Morgan', 'Noah', 'Ocean', 'Paris', 'Quinn', 'Robin', 'Sage', 'Taylor', 'Union', 'Vale', 'Wade', 'Xander', 'York', 'Zephyr', 'Aaron', 'Benjamin', 'Christopher', 'Daniel', 'Edward', 'Frank', 'George', 'Henry', 'Isaac', 'James', 'Kevin', 'Leonard', 'Michael', 'Nathan', 'Oliver', 'Patrick', 'Quinn', 'Robert', 'Steven', 'Thomas', 'Ulysses', 'Victor', 'William', 'Xavier', 'Yuki', 'Zachary', 'Alice', 'Bella', 'Charlotte', 'Diana', 'Elena', 'Fiona', 'Grace', 'Hannah', 'Iris', 'Jessica', 'Katherine', 'Laura', 'Michelle', 'Nancy', 'Olivia', 'Paige', 'Quinley', 'Rachel', 'Sophia', 'Tessa', 'Ursula', 'Victoria', 'Wendy', 'Ximena', 'Yasmine', 'Zoe']
        surnames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Wilson', 'Anderson', 'Taylor', 'Thomas', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker', 'Young', 'Allen', 'King', 'Wright', 'Lopez', 'Hill', 'Scott', 'Green', 'Adams', 'Nelson', 'Carter', 'Roberts', 'Edwards', 'Collins', 'Reeves', 'Morris', 'Murphy', 'Rogers', 'Morgan', 'Peterson', 'Cooper', 'Reed', 'Bell', 'Gomez', 'Murray', 'Freeman', 'Wells', 'Webb', 'Simpson', 'Stevens', 'Tucker', 'Porter', 'Hunter', 'Hicks', 'Crawford', 'Henry', 'Boyd', 'Mason', 'Moreno', 'Kennedy', 'Warren', 'Dixon', 'Ramos', 'Reeves', 'Burns', 'Gordon', 'Shaw', 'Holmes', 'Rice', 'Robertson', 'Hunt', 'Black', 'Daniels', 'Palmer', 'Mills', 'Nicholson', 'Grant', 'Knight', 'Ferguson', 'Stone', 'Hawkins', 'Dunn', 'Perkins', 'Hudson', 'Spencer', 'Gardner', 'Stephens', 'Payne', 'Pierce', 'Berry', 'Matthews', 'Arnold', 'Wagner', 'Willis', 'Ray', 'Watkins', 'Olson', 'Carroll', 'Duncan', 'Snyder', 'Hart', 'Cunningham', 'Knight', 'Chase', 'Wyatt']
        
        firstname = random.choice(firstnames).lower()
        lastname = random.choice(surnames).lower()
        displayname = firstname.capitalize() + ' ' + lastname.capitalize()
        
        usernamesuffixes = ['goturback', 'alltake', 'isdone', 'nowake', 'makeit', 'bestme', 'allset', 'isgood', 'letgo', 'final']
        discordusername = f"{firstname}{random.choice(usernamesuffixes)}{random.randint(100, 999)}"
        
        email, emailpassword, emailtoken, emailuuid, emailprovider = getemailfromprovider(config)
        if not email:
            log.error("Failed to get email")
            return
        
        accountpassword = emailpassword or generateformpassword(10)
        log.success(f"Email: {log.maskemail(email)}")
        
        tempprofile = tempfile.mkdtemp()
        browserargs = [
            f'--user-data-dir={tempprofile}',
            '--disable-backgrounding-occluded-windows',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-throttling',
            '--no-first-run',
            '--disable-default-apps',
            '--disable-features=IsolateOrigins,site-per-process,ChromeWhatsNewUI',
            '--disable-dev-shm-usage',
            '--disable-breakpad',
            '--disable-component-extensions-with-background-pages',
            '--disable-features=TranslateUI,MediaRouter,OptimizationHints',
            '--disable-domain-reliability',
            '--window-size=960,1070',
            '--window-position=0,0',
            '--force-device-scale-factor=1',
        ]
        
        if proxyconfig:
            browserargs.extend(getbrowserproxyargs(proxyconfig))

        if nopechadirext.exists():
            browserargs.append(f'--load-extension={nopechadirext}')
        
        currentkey = getcurrentnopechakey()
        if currentkey:
            injectnopechakey(currentkey)
            log.info("NopeCHA key injected")
        
        browser = await uc.start(
            headless=False,
            browser_executable_path=bravepath if bravepath else None,
            browser_args=browserargs,
        )
        
        page = await browser.get("https://discord.com/register")
        if not page:
            log.error("Could not get page")
            return

        if fingerprint:
            injected = await injectfingerprinttopage(page, fingerprint)
            if injected:
                log.success("Fingerprint injected into page")
            else:
                log.warning("Fingerprint injection failed")
        
        for _ in range(30):
            try:
                if await page.query_selector('input[name="email"]'):
                    break
            except:
                pass
            await asyncio.sleep(0.3)

        await asyncio.sleep(0.3)

        success = await fillregistrationform(page, email, displayname, discordusername, accountpassword)
        if not success:
            log.error("Form fill failed")
            return
        
        created = await waitforaccountcreation(page)
        
        if created:
            log.solved("Account created!")
        else:
            log.error("Creation failed")
            return
        
        token = await waitfordiscordtoken(page, email=email, password=accountpassword, proxyconfig=proxyconfig)
        
        if token:
            if token.startswith('"') and token.endswith('"'):
                token = token[1:-1]

            tokenmatch = re.search(r'([a-zA-Z0-9_-]{20,})\.([a-zA-Z0-9_-]{6})\.([a-zA-Z0-9_-]{27,})', token)
            if tokenmatch:
                token = f"{tokenmatch.group(1)}.{tokenmatch.group(2)}.{tokenmatch.group(3)}"
            
            log.success(f"✓ Token fetched! Token: {log.masktoken(token)}")
            
            vconfig = config.get("email_providers", {}).get("venumzmail", {})
            apikey = vconfig.get("api_key", "").strip()
            apibase = vconfig.get("api_base", "https://api.venumzmail.xyz")
            domain = email.split('@')[1] if '@' in email else "lickingpussy.online"
            verified = await verifyemailvenumzmail(
                email, apikey, browser, token, domain, apibase, timeout=60
            )
            if verified:
                log.success("Email verified!")
            else:
                log.warning("Email verification failed")
                unverifiedfile = outputdir / "unverified.txt"
                with lock:
                    with open(unverifiedfile, 'a', encoding='utf-8') as f:
                        f.write(f"{email}:{accountpassword}:{token}\n")
                log.info("Saved unverified account to unverified.txt")
            
            result = checktoken(token, proxyconfig)
            log.tokenstatus(result)
            saveaccounttofile(email, accountpassword, token, result)

            with lock:
                sessioncreated += 1
                creatednow = sessioncreated

            log.success(f"Account #{creatednow} created")
            
            if sessiontarget > 0 and creatednow >= sessiontarget:
                with lock:
                    sessionstop = True
        else:
            pass
            
    except Exception as e:
        log.error(f"Error: {e}")
    
    finally:
        if browser:
            try:
                await browser.stop()
            except:
                pass
        if tempprofile and os.path.exists(tempprofile):
            try:
                shutil.rmtree(tempprofile, ignore_errors=True)
            except:
                pass
        with workerlock:
            activeworkers -= 1

async def batchcooldown(batchsize: int, accountscreated: int):
    if accountscreated == 0:
        return
    for remaining in range(cooldownseconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        print(f"\r{yellow}[BATCH] ➜ {reset}Next batch in: {cyan}{mins:02d}:{secs:02d}{reset} ", end='', flush=True)
        await asyncio.sleep(1)
    print()

async def runworkers():
    global sessiontarget, sessioncreated, sessionstop, proxylist
    
    allproxies = loadproxies(config)
    with proxylistlock:
        proxylist = allproxies if allproxies else []
    
    while not sessionstop:
        with lock:
            if sessiontarget > 0 and sessioncreated >= sessiontarget:
                sessionstop = True
                break
        
        accountsbefore = sessioncreated
        remaining = sessiontarget - sessioncreated if sessiontarget > 0 else threadcount
        batchsize = min(threadcount, remaining) if sessiontarget > 0 else threadcount
        
        if batchsize <= 0 and sessiontarget > 0:
            break
        
        tasks = []
        for i in range(batchsize):
            workerid = random.randint(10000, 99999)
            currentproxy = getrandomproxy()
            rotatenopechakey()
            tasks.append(asyncio.create_task(worker(workerid, currentproxy)))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        accountscreated = sessioncreated - accountsbefore
        
        if sessiontarget > 0:
            if sessioncreated < sessiontarget:
                await batchcooldown(batchsize, accountscreated)
        else:
            await batchcooldown(batchsize, accountscreated)
        
        await asyncio.sleep(0.1)
    
    log.success(f"Completed! Created {sessioncreated} account(s)")

def showvenombanner():
    banner = f"""{blue}
                                                                       
                                                                       
██  ██ ██████ ███  ██ ██  ██ ██▄  ▄██ ██████ ██▄  ▄██ ▄████▄ ██ ██     
██▄▄██ ██▄▄   ██ ▀▄██ ██  ██ ██ ▀▀ ██  ▄▄▀▀  ██ ▀▀ ██ ██▄▄██ ██ ██     
 ▀██▀  ██▄▄▄▄ ██   ██ ▀████▀ ██    ██ ██████ ██    ██ ██  ██ ██ ██████{reset}
{blue}https://venumzmail.xyz{reset}
"""
    print(banner)

async def main():
    global sessiontarget
    
    showvenombanner()
    
    if not checksolverhealth():
        log.warning("Local Solver not detected!")
        log.info("Start solver: python solver_v2.py")
        usesolver = input(f"{white}Continue without solver? [y/n]: {reset}").strip().lower() == 'y'
        if not usesolver:
            return
    else:
        log.success("Captcha Solver connected")
    
    while True:
        try:
            count = input(f"{white}Accounts to create (0=infinite): {reset}").strip()
            if count.isdigit():
                sessiontarget = int(count)
                break
        except:
            pass
    
    print()
    if sessiontarget == 0:
        log.info("Running in infinite mode")
    else:
        log.info(f"Target: {sessiontarget} accounts")
    print()
    
    downloadnopechaext()
    
    allproxies = loadproxies(config)
    if allproxies:
        log.info(f"Proxy mode: ENABLED ({len(allproxies)} proxies)")
    else:
        log.info("Proxy mode: DISABLED (using direct connection)")
    
    try:
        await runworkers()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{yellow}Stopped{reset}")
    except Exception as e:
        log.error(f"Error: {e}")
