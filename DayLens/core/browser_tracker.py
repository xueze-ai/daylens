import os,glob,time,threading,tempfile,shutil,sqlite3,fnmatch,logging
from pathlib import Path
from urllib.parse import urlparse

EPOCH=11644473600000000
class BrowserTracker:
    def __init__(self,repo,config):self.repo=repo;self.config=config;self.stop_event=threading.Event();self.thread=None
    def start(self):self.stop_event.clear();self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def stop(self):self.stop_event.set()
    def _excluded(self,d):return not d or d in {'localhost','127.0.0.1'} or any(fnmatch.fnmatch(d,x) for x in self.config.get('browser_excludes',[]))
    def _sources(self):
        local=os.environ.get('LOCALAPPDATA','');roam=os.environ.get('APPDATA','');out=[]
        for browser,base in [('chrome',Path(local)/'Google/Chrome/User Data'),('edge',Path(local)/'Microsoft/Edge/User Data')]:
            if base.exists():
                for p in base.iterdir():
                    if p.is_dir() and (p.name=='Default' or p.name.startswith('Profile ')) and (p/'History').exists():out.append((browser,p.name,p/'History','chromium'))
        for f in glob.glob(str(Path(roam)/'Mozilla/Firefox/Profiles/*.default-release/places.sqlite')):out.append(('firefox',Path(f).parent.name,Path(f),'firefox'))
        return out
    def scan(self):
        if not self.config.get('browser_history_enabled',True):return
        since=(time.time()-86400)*1e6;rows=[]
        for browser,profile,src,kind in self._sources():
            tmpdir=None;db=None
            try:
                # Chrome and Edge lock History while running. Copy the database
                # and its WAL sidecars first, then query the private snapshot.
                tmpdir=Path(tempfile.mkdtemp(prefix='daylens_browser_'));tmp=tmpdir/src.name
                for suffix in ('','-wal','-shm'):
                    source=Path(str(src)+suffix)
                    if source.exists():shutil.copy2(source,Path(str(tmp)+suffix))
                db=sqlite3.connect(str(tmp),timeout=3)
                q=("SELECT u.url,u.title,v.visit_time FROM visits v JOIN urls u ON u.id=v.url WHERE v.visit_time>? ORDER BY v.visit_time DESC",since+EPOCH) if kind=='chromium' else ("SELECT p.url,p.title,v.visit_date FROM moz_historyvisits v JOIN moz_places p ON p.id=v.place_id WHERE v.visit_date>? ORDER BY v.visit_date DESC",since)
                for url,title,t in db.execute(q[0],(q[1],)):
                    domain=urlparse(url).hostname or ''
                    if self._excluded(domain):continue
                    ts=(t-EPOCH)/1e6 if kind=='chromium' else t/1e6;rows.append((browser,profile,url,domain,title or domain,ts))
            except Exception as e:logging.warning('Browser history scan failed: %s/%s: %s',browser,profile,e)
            finally:
                if db:
                    try:db.close()
                    except Exception:pass
                if tmpdir:shutil.rmtree(tmpdir,ignore_errors=True)
        self.repo.add_browser_rows(rows)
    def _run(self):
        self.scan()
        while not self.stop_event.wait(15):self.scan()
