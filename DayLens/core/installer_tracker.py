import winreg,time,threading

LOCATIONS=[(winreg.HKEY_LOCAL_MACHINE,r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),(winreg.HKEY_LOCAL_MACHINE,r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),(winreg.HKEY_CURRENT_USER,r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")]
def installed():
    out={}
    for hive,path in LOCATIONS:
        try:
            with winreg.OpenKey(hive,path) as k:
                for i in range(winreg.QueryInfoKey(k)[0]):
                    try:
                        sub=winreg.EnumKey(k,i)
                        with winreg.OpenKey(k,sub) as s:
                            name=winreg.QueryValueEx(s,'DisplayName')[0]
                            try:version=winreg.QueryValueEx(s,'DisplayVersion')[0]
                            except OSError:version=''
                            out[f'{name}|{sub}']={'name':name,'version':version}
                    except OSError:pass
        except OSError:pass
    return out
class InstallerTracker:
    def __init__(self,repo):self.repo=repo;self.stop_event=threading.Event();self.thread=None
    def start(self):self.stop_event.clear();self.check();self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def stop(self):self.stop_event.set()
    def check(self):
        now=installed();old=self.repo.get_install_snapshot('registry')
        if old:
            for k in now.keys()-old.keys():self.repo.add_install_event(now[k]['name'],'installed','registry',time.time())
            for k in old.keys()-now.keys():self.repo.add_install_event(old[k]['name'],'uninstalled','registry',time.time())
            for k in now.keys()&old.keys():
                if now[k].get('version')!=old[k].get('version'):self.repo.add_install_event(now[k]['name'],'updated','registry',time.time())
        self.repo.set_install_snapshot('registry',now)
    def _run(self):
        while not self.stop_event.wait(3600):self.check()
