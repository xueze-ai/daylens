import sqlite3, threading, json, os
from datetime import datetime, timedelta
from pathlib import Path
from config.manager import APP_DIR

DB_PATH = APP_DIR / "daylens.db"

class Repository:
    def __init__(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._connect()
        try:
            # Opening a multi-gigabyte database with PRAGMA quick_check blocks
            # startup for seconds. Schema creation is sufficient here; manual
            # maintenance remains available in Settings > Advanced.
            self._init()
        except sqlite3.DatabaseError:
            try:self.db.close()
            except Exception:pass
            stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
            for suffix in ('','-wal','-shm'):
                src=Path(str(DB_PATH)+suffix)
                if src.exists():
                    try:src.rename(Path(str(src)+f'.corrupt-{stamp}'))
                    except OSError:pass
            self._connect();self._init()
    def _connect(self):
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False,timeout=30);self.db.row_factory=sqlite3.Row
    def _init(self):
        self.db.executescript("""
        PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=30000; PRAGMA wal_autocheckpoint=500;
        CREATE TABLE IF NOT EXISTS file_events(id INTEGER PRIMARY KEY, path TEXT, event_type TEXT, is_dir INTEGER, size INTEGER, mtime REAL, ts REAL, root TEXT);
        CREATE INDEX IF NOT EXISTS ix_file_ts ON file_events(ts); CREATE INDEX IF NOT EXISTS ix_file_path ON file_events(path);
        CREATE TABLE IF NOT EXISTS app_sessions(id INTEGER PRIMARY KEY, process TEXT, display_name TEXT, exe_path TEXT, window_title TEXT, started REAL, ended REAL, seconds REAL);
        CREATE INDEX IF NOT EXISTS ix_app_started ON app_sessions(started);
        CREATE TABLE IF NOT EXISTS install_snapshots(scope TEXT PRIMARY KEY, payload TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS install_events(id INTEGER PRIMARY KEY, name TEXT, action TEXT, source TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY, name TEXT, created REAL, payload TEXT);
        CREATE TABLE IF NOT EXISTS ai_summaries(day TEXT PRIMARY KEY, markdown TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS window_samples(id INTEGER PRIMARY KEY, process TEXT, display_name TEXT, exe_path TEXT, window_title TEXT, ts REAL, idle INTEGER, UNIQUE(process,ts));
        CREATE INDEX IF NOT EXISTS ix_samples_ts ON window_samples(ts);
        CREATE TABLE IF NOT EXISTS browser_history(id INTEGER PRIMARY KEY, browser TEXT, profile TEXT, url TEXT, domain TEXT, title TEXT, visit_time REAL, UNIQUE(url,visit_time));
        CREATE INDEX IF NOT EXISTS ix_browser_time ON browser_history(visit_time);
        CREATE TABLE IF NOT EXISTS wechat_files(id INTEGER PRIMARY KEY, path TEXT UNIQUE, name TEXT, size INTEGER, file_type TEXT, received REAL, note TEXT DEFAULT '', summary TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS daily_reports(id INTEGER PRIMARY KEY, date TEXT UNIQUE, summary TEXT, one_liner TEXT, created_at REAL, pushed INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, text TEXT NOT NULL, ts REAL NOT NULL, date TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_notes_date ON notes(date);
        CREATE TABLE IF NOT EXISTS activity_dates(day TEXT PRIMARY KEY);
        """)
        for table in ('file_events','window_samples','browser_history','wechat_files'):
            try:self.db.execute(f"ALTER TABLE {table} ADD COLUMN date TEXT")
            except sqlite3.OperationalError:pass
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_file_events_date ON file_events(date)");self.db.execute("CREATE INDEX IF NOT EXISTS idx_window_samples_date ON window_samples(date)");self.db.execute("CREATE INDEX IF NOT EXISTS idx_browser_history_date ON browser_history(date)");self.db.execute("CREATE INDEX IF NOT EXISTS idx_wechat_files_date ON wechat_files(date)")
        # Never backfill millions of legacy rows on the UI startup path. New rows
        # always receive a date; legacy rows remain queryable through ts indexes.
        try:self.db.execute("ALTER TABLE snapshots ADD COLUMN file_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:pass
        if not self.db.execute("SELECT 1 FROM activity_dates LIMIT 1").fetchone():
            self.db.execute("INSERT OR IGNORE INTO activity_dates SELECT date FROM file_events WHERE date IS NOT NULL GROUP BY date")
            self.db.execute("INSERT OR IGNORE INTO activity_dates SELECT date FROM window_samples WHERE date IS NOT NULL GROUP BY date")
            self.db.execute("INSERT OR IGNORE INTO activity_dates SELECT date FROM browser_history WHERE date IS NOT NULL GROUP BY date")
            self.db.execute("INSERT OR IGNORE INTO activity_dates SELECT date FROM wechat_files WHERE date IS NOT NULL GROUP BY date")
            self.db.execute("INSERT OR IGNORE INTO activity_dates SELECT day FROM ai_summaries")
        self.db.commit()
    def add_file_events(self, rows):
        if not rows:return
        with self.lock:
            cooked=[tuple(r)+(datetime.fromtimestamp(r[5]).strftime('%Y-%m-%d'),) for r in rows];self.db.executemany("INSERT INTO file_events(path,event_type,is_dir,size,mtime,ts,root,date) VALUES(?,?,?,?,?,?,?,?)", cooked);self.db.executemany("INSERT OR IGNORE INTO activity_dates(day) VALUES(?)",{(x[-1],) for x in cooked});self.db.commit()
    def add_session(self, process, display, exe, title, start, end):
        if end-start < 3:return
        with self.lock:
            self.db.execute("INSERT INTO app_sessions(process,display_name,exe_path,window_title,started,ended,seconds) VALUES(?,?,?,?,?,?,?)",(process,display,exe,title,start,end,end-start));self.db.commit()
    def add_sample(self,process,display,exe,title,ts,idle):
        day=datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        with self.lock:self.db.execute("INSERT OR IGNORE INTO window_samples(process,display_name,exe_path,window_title,ts,idle,date) VALUES(?,?,?,?,?,?,?)",(process,display,exe,title,ts,int(idle),day));self.db.execute("INSERT OR IGNORE INTO activity_dates(day) VALUES(?)",(day,));self.db.commit()
    def day_range(self, day):
        start=datetime.strptime(day,"%Y-%m-%d"); return start.timestamp(),(start+timedelta(days=1)).timestamp()
    def file_events(self, day):
        a,b=self.day_range(day);q="""SELECT f.* FROM file_events f JOIN (SELECT path,MAX(id) id FROM file_events WHERE date=? OR (date IS NULL AND ts>=? AND ts<?) GROUP BY path) x ON f.id=x.id ORDER BY f.ts"""
        with self.lock:return [dict(x) for x in self.db.execute(q,(day,a,b))]
    def app_usage(self, day):
        a,b=self.day_range(day);q="""SELECT process,display_name,exe_path,SUM(CASE WHEN idle=0 THEN 5 ELSE 0 END) seconds,COUNT(DISTINCT CAST(ts/30 AS INTEGER)) sessions,MAX(window_title) window_title FROM window_samples WHERE date=? OR (date IS NULL AND ts>=? AND ts<?) GROUP BY process,display_name,exe_path HAVING seconds>0 ORDER BY seconds DESC"""
        with self.lock:return [dict(x) for x in self.db.execute(q,(day,a,b))]
    def samples(self,day):
        a,b=self.day_range(day)
        with self.lock:return [dict(x) for x in self.db.execute("SELECT * FROM window_samples WHERE date=? OR (date IS NULL AND ts>=? AND ts<?) ORDER BY ts",(day,a,b))]
    def add_browser_rows(self,rows):
        if not rows:return
        cooked=[tuple(r)+(datetime.fromtimestamp(r[5]).strftime('%Y-%m-%d'),) for r in rows]
        with self.lock:self.db.executemany("INSERT OR IGNORE INTO browser_history(browser,profile,url,domain,title,visit_time,date) VALUES(?,?,?,?,?,?,?)",cooked);self.db.executemany("INSERT OR IGNORE INTO activity_dates(day) VALUES(?)",{(x[-1],) for x in cooked});self.db.commit()
    def browser_today(self,day):
        with self.lock:return [dict(x) for x in self.db.execute("SELECT domain,COUNT(*) visits,MAX(title) title,MAX(visit_time) last_visit FROM browser_history WHERE date=? GROUP BY domain ORDER BY visits DESC",(day,))]
    def browser_pages(self,day,domain):
        a,b=self.day_range(day)
        with self.lock:return [dict(x) for x in self.db.execute("SELECT title,url,visit_time,browser FROM browser_history WHERE visit_time>=? AND visit_time<? AND domain=? ORDER BY visit_time DESC LIMIT 20",(a,b,domain))]
    def add_wechat(self,path,name,size,file_type,received):
        day=datetime.fromtimestamp(received).strftime('%Y-%m-%d')
        with self.lock:self.db.execute("INSERT OR IGNORE INTO wechat_files(path,name,size,file_type,received,date) VALUES(?,?,?,?,?,?)",(path,name,size,file_type,received,day));self.db.execute("INSERT OR IGNORE INTO activity_dates(day) VALUES(?)",(day,));self.db.commit()
    def wechat_today(self,day):
        with self.lock:return [dict(x) for x in self.db.execute("SELECT * FROM wechat_files WHERE date=? ORDER BY received DESC LIMIT 500",(day,))]
    def update_wechat(self,wid,note=None,summary=None):
        with self.lock:
            if note is not None:self.db.execute("UPDATE wechat_files SET note=? WHERE id=?",(note,wid))
            if summary is not None:self.db.execute("UPDATE wechat_files SET summary=? WHERE id=?",(summary,wid))
            self.db.commit()
    def save_daily_report(self,day,text,one='',pushed=0):
        with self.lock:self.db.execute("REPLACE INTO daily_reports(date,summary,one_liner,created_at,pushed) VALUES(?,?,?,?,?)",(day,text,one,datetime.now().timestamp(),pushed));self.db.commit()
    def daily_report(self,day):return self.db.execute("SELECT * FROM daily_reports WHERE date=?",(day,)).fetchone()
    def add_install_event(self,name,action,source,ts):
        with self.lock:self.db.execute("INSERT INTO install_events(name,action,source,ts) VALUES(?,?,?,?)",(name,action,source,ts));self.db.commit()
    def install_events(self,day):
        a,b=self.day_range(day)
        with self.lock:return [dict(x) for x in self.db.execute("SELECT * FROM install_events WHERE ts>=? AND ts<? ORDER BY ts",(a,b))]
    def get_install_snapshot(self,scope):
        r=self.db.execute("SELECT payload FROM install_snapshots WHERE scope=?",(scope,)).fetchone();return json.loads(r[0]) if r else {}
    def set_install_snapshot(self,scope,payload):
        with self.lock:self.db.execute("REPLACE INTO install_snapshots(scope,payload,ts) VALUES(?,?,?)",(scope,json.dumps(payload,ensure_ascii=False),datetime.now().timestamp()));self.db.commit()
    def add_snapshot(self,name,payload):
        with self.lock:
            cur=self.db.execute("INSERT INTO snapshots(name,created,payload,file_count) VALUES(?,?,?,?)",(name,datetime.now().timestamp(),json.dumps(payload,ensure_ascii=False),len(payload)));self.db.commit();return cur.lastrowid
    def snapshots(self):return [dict(x) for x in self.db.execute("SELECT id,name,created,file_count FROM snapshots ORDER BY created DESC")]
    def snapshot_meta(self,sid):
        r=self.db.execute("SELECT id,name,created,file_count FROM snapshots WHERE id=?",(sid,)).fetchone();return dict(r) if r else None
    def delete_snapshot(self,sid):
        with self.lock:self.db.execute("DELETE FROM snapshots WHERE id=?",(sid,));self.db.commit()
    def snapshot(self,sid):
        r=self.db.execute("SELECT payload FROM snapshots WHERE id=?",(sid,)).fetchone();return json.loads(r[0]) if r else {}
    def save_summary(self,day,text):
        with self.lock:self.db.execute("REPLACE INTO ai_summaries(day,markdown,created) VALUES(?,?,?)",(day,text,datetime.now().timestamp()));self.db.execute("INSERT OR IGNORE INTO activity_dates(day) VALUES(?)",(day,));self.db.commit()
    def summary(self,day):
        r=self.db.execute("SELECT markdown FROM ai_summaries WHERE day=?",(day,)).fetchone();return r[0] if r else ""
    def summaries_between(self,start_day,end_day):
        with self.lock:return [dict(x) for x in self.db.execute("SELECT day,markdown,created FROM ai_summaries WHERE day>=? AND day<=? ORDER BY day DESC",(start_day,end_day))]
    def activity_days(self,limit=30):
        with self.lock:return [x[0] for x in self.db.execute("SELECT day FROM activity_dates ORDER BY day DESC LIMIT ?",(limit,))]
    def cleanup(self,days):
        cutoff=(datetime.now()-timedelta(days=days)).timestamp()
        with self.lock:
            for t,c in [('file_events','ts'),('app_sessions','started'),('install_events','ts'),('window_samples','ts'),('browser_history','visit_time'),('wechat_files','received')]:self.db.execute(f"DELETE FROM {t} WHERE {c}<?",(cutoff,))
            self.db.commit()
    def get_kv(self,key,default=''):
        r=self.db.execute("SELECT value FROM kv WHERE key=?",(key,)).fetchone();return r[0] if r else default
    def set_kv(self,key,value):
        with self.lock:self.db.execute("REPLACE INTO kv(key,value) VALUES(?,?)",(key,str(value)));self.db.commit()
    def checkpoint(self):
        with self.lock:
            try:self.db.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchall()
            except sqlite3.DatabaseError:pass
    def add_note(self,text,ts=None):
        ts=ts or datetime.now().timestamp();day=datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        with self.lock:self.db.execute("INSERT INTO notes(text,ts,date) VALUES(?,?,?)",(text,ts,day));self.db.execute("INSERT OR IGNORE INTO activity_dates(day) VALUES(?)",(day,));self.db.commit()
    def notes(self,day):
        with self.lock:return [dict(x) for x in self.db.execute("SELECT * FROM notes WHERE date=? ORDER BY ts",(day,))]
    def search(self,query,limit=100):
        q='%'+query.strip()+'%';out=[]
        if not query.strip():return out
        with self.lock:
            for x in self.db.execute("SELECT date,datetime(ts,'unixepoch','localtime') stamp,'文件' kind,path title,event_type detail FROM file_events WHERE path LIKE ? ORDER BY ts DESC LIMIT ?",(q,limit//4)):out.append(dict(x))
            for x in self.db.execute("SELECT date,datetime(received,'unixepoch','localtime') stamp,'微信文件' kind,name title,path detail FROM wechat_files WHERE name LIKE ? OR note LIKE ? OR summary LIKE ? ORDER BY received DESC LIMIT ?",(q,q,q,limit//4)):out.append(dict(x))
            for x in self.db.execute("SELECT day date,day stamp,'AI 总结' kind,day title,substr(markdown,1,160) detail FROM ai_summaries WHERE markdown LIKE ? ORDER BY day DESC LIMIT ?",(q,limit//4)):out.append(dict(x))
            for x in self.db.execute("SELECT date,datetime(ts,'unixepoch','localtime') stamp,'速记' kind,substr(text,1,60) title,text detail FROM notes WHERE text LIKE ? ORDER BY ts DESC LIMIT ?",(q,limit//4)):out.append(dict(x))
        return out[:limit]
