import os,time,threading,queue
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SKIP_NAMES={'$Recycle.Bin','System Volume Information','.git','node_modules','__pycache__','WinSxS','WindowsApps','Temp','Cache','Caches','Code Cache','GPUCache'}
ALLOW_EXT={'.docx','.xlsx','.pptx','.pdf','.txt','.md','.py','.js','.ts','.go','.rs','.java','.jpg','.jpeg','.png','.gif','.mp4','.mov','.zip','.rar','.7z','.exe','.msi'}
HARD_PARTS=('\\appdata\\local\\temp\\','\\windows\\temp\\','\\programdata\\microsoft\\windows\\caches\\','\\.git\\objects\\','\\node_modules\\','\\__pycache__\\')

def allowed(path):
    p=Path(path);low=('\\'+str(p).lower().replace('/','\\').strip('\\')+'\\')
    if any(x in low for x in HARD_PARTS) or ('\\google\\chrome\\user data\\' in low and '\\cache\\' in low):return False
    if any(x in SKIP_NAMES for x in p.parts):return False
    if p.suffix and p.suffix.lower() not in ALLOW_EXT:return False
    return p.name.lower() not in {'pagefile.sys','hiberfil.sys','swapfile.sys'}

class Handler(FileSystemEventHandler):
    def __init__(self,collector,root):self.collector=collector;self.root=root
    def on_any_event(self,e):
        if e.event_type not in {'created','modified','deleted','moved'}:return
        p=getattr(e,'dest_path',None) if e.event_type=='moved' else e.src_path
        if p and allowed(p):self.collector.put(p,e.event_type,e.is_directory,self.root)

class FileMonitor:
    def __init__(self,repo):self.repo=repo;self.observers=[];self.q=queue.Queue();self.stop_event=threading.Event();self.writer=None;self.dir_rate={}
    def put(self,path,event,is_dir,root):
        if is_dir:return
        now=time.time();folder=str(Path(path).parent).lower();start,count,reported=self.dir_rate.get(folder,(now,0,False))
        if now-start>=60:start,count,reported=now,0,False
        count+=1;self.dir_rate[folder]=(start,count,reported)
        if count>100:
            if not reported:
                marker=str(Path(path).parent/'[短时大量变更]');self.dir_rate[folder]=(start,count,True);self.q.put((marker,'聚合变更',0,0,now,now,root))
            return
        size=0;mtime=0
        try:s=os.stat(path);size=s.st_size;mtime=s.st_mtime
        except OSError:pass
        self.q.put((path,event,0,size,mtime,now,root))
    def start(self,roots):
        self.stop();self.stop_event.clear();self.writer=threading.Thread(target=self._write,daemon=True);self.writer.start()
        for root in roots:
            if not os.path.exists(root):continue
            try:o=Observer();o.schedule(Handler(self,root),root,recursive=True);o.start();self.observers.append(o)
            except Exception:pass
        today=datetime.now().strftime('%Y-%m-%d')
        if self.repo.get_kv('baseline_day')!=today:
            threading.Thread(target=self._baseline,args=(roots,today),daemon=True).start()
    def stop(self):
        self.stop_event.set()
        for o in self.observers:
            try:o.stop();o.join(2)
            except Exception:pass
        self.observers=[]
    def _write(self):
        batch=[];last=time.time()
        while not self.stop_event.is_set():
            try:batch.append(self.q.get(timeout=1))
            except queue.Empty:pass
            if batch and (len(batch)>=50 or time.time()-last>=10):self.repo.add_file_events(batch);batch=[];last=time.time()
        while not self.q.empty():batch.append(self.q.get_nowait())
        self.repo.add_file_events(batch)
    def _baseline(self,roots,today):
        start=datetime.strptime(today,'%Y-%m-%d').timestamp();end=start+86400;batch=[]
        for root in roots:
            if self.stop_event.is_set():return
            if not os.path.exists(root):continue
            for base,dirs,files in os.walk(root):
                if self.stop_event.is_set():return
                dirs[:]=[d for d in dirs if allowed(os.path.join(base,d))]
                for name in files:
                    p=os.path.join(base,name)
                    if not allowed(p):continue
                    try:s=os.stat(p)
                    except OSError:continue
                    if start<=s.st_mtime<end:
                        batch.append((p,'baseline',0,s.st_size,s.st_mtime,s.st_mtime,root))
                    if len(batch)>=500:self.repo.add_file_events(batch);batch=[]
        self.repo.add_file_events(batch);self.repo.set_kv('baseline_day',today);self.repo.checkpoint()
