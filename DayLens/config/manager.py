import json, os
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "DayLens"
CONFIG_PATH = APP_DIR / "config.json"
DEFAULTS = {
    "version": "1.0.9", "theme": "light", "font_engine": "gdi", "drives": ["C:\\", "D:\\", "E:\\"],
    "watch_dirs": [str(Path.home()/"Desktop"),str(Path.home()/"Documents"),str(Path.home()/"Downloads"),str(Path.home()/"Pictures"),str(Path.home()/"Videos"),"D:\\","E:\\"],
    "autostart": False, "retention_days": 30, "ai_mode": "openai",
    "base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4o-mini",
    "ollama_url": "http://localhost:11434", "ollama_model": "qwen2.5:7b",
    "scan_on_first_run": True, "browser_history_enabled": True,
    "browser_excludes": ["localhost", "127.0.0.1"], "idle_minutes": 5,
    "wechat_enabled": True, "wechat_path": "",
    "auto_summary": False, "auto_ai_analysis": True, "auto_summary_time": "22:00", "serverchan_enabled": False,
    "serverchan_key": "", "auto_snapshot": True, "app_categories": {}
}

def load_config():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(CONFIG_PATH.read_text("utf-8"))
    except Exception:
        data = {}
    merged={**DEFAULTS, **data};merged['version']=DEFAULTS['version'];return merged

def save_config(config):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), "utf-8")

def set_autostart(enabled, exe_path):
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "DayLens", 0, winreg.REG_SZ, f'"{exe_path}" --background')
        else:
            try: winreg.DeleteValue(key, "DayLens")
            except FileNotFoundError: pass
