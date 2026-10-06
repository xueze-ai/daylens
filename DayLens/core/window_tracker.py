import time, threading, os, ctypes
import psutil, win32gui, win32process

SYSTEM = {'explorer.exe','searchhost.exe','shellexperiencehost.exe','textinputhost.exe','startmenuexperiencehost.exe','lockapp.exe','applicationframehost.exe','dwm.exe'}
NAMES = {'chrome.exe':'Google Chrome','msedge.exe':'Microsoft Edge','code.exe':'Visual Studio Code','devenv.exe':'Visual Studio','notepad.exe':'记事本','wps.exe':'WPS 文字','et.exe':'WPS 表格','wpp.exe':'WPS 演示','winword.exe':'Microsoft Word','excel.exe':'Microsoft Excel','powerpnt.exe':'Microsoft PowerPoint','wechat.exe':'微信','qq.exe':'QQ','quicker.exe':'Quicker','python.exe':'Python','pycharm64.exe':'PyCharm','idea64.exe':'IntelliJ IDEA','photoshop.exe':'Adobe Photoshop','explorer.exe':'文件资源管理器'}

class WindowTracker:
    def __init__(self,repo,interval=5):self.repo=repo;self.interval=interval;self.stop_event=threading.Event();self.thread=None;self.current=None
    def start(self):
        if self.thread and self.thread.is_alive():return
        self.stop_event.clear();self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def stop(self):
        self.stop_event.set();self._flush(time.time())
    def _sample(self):
        hwnd=win32gui.GetForegroundWindow()
        if not hwnd:return None
        title=win32gui.GetWindowText(hwnd).strip()
        if not title or title in {'Program Manager','Windows 输入体验'}:return None
        _,pid=win32process.GetWindowThreadProcessId(hwnd)
        try:
            p=psutil.Process(pid);name=p.name().lower();exe=p.exe()
        except Exception:return None
        if name in SYSTEM and name!='explorer.exe':return None
        display=NAMES.get(name) or os.path.splitext(os.path.basename(exe))[0].replace('_',' ').title()
        return name,display,exe,title
    def _flush(self,end):
        if self.current:
            k,start,title=self.current;self.repo.add_session(k[0],k[1],k[2],title,start,end);self.current=None
    def _run(self):
        while not self.stop_event.wait(self.interval):
            now=time.time();s=self._sample()
            if not s:continue
            class LASTINPUTINFO(ctypes.Structure):_fields_=[('cbSize',ctypes.c_uint),('dwTime',ctypes.c_uint)]
            lii=LASTINPUTINFO();lii.cbSize=ctypes.sizeof(lii);ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii));idle_ms=(ctypes.windll.kernel32.GetTickCount()-lii.dwTime)&0xffffffff
            idle=idle_ms>getattr(self,'idle_seconds',300)*1000
            self.repo.add_sample(s[0],s[1],s[2],s[3],now,idle)
            key=s[:3]
            if not self.current:self.current=(key,now,s[3])
            elif self.current[0]!=key:self._flush(now);self.current=(key,now,s[3])
            else:self.current=(key,self.current[1],s[3])
