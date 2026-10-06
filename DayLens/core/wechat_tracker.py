import os,time,hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def file_type(p):
    e=Path(p).suffix.lower()
    if e in {'.txt','.md','.doc','.docx','.pdf','.rtf'}:return '文档'
    if e in {'.png','.jpg','.jpeg','.gif','.webp','.bmp'}:return '图片'
    if e in {'.zip','.rar','.7z','.tar','.gz'}:return '压缩包'
    if e in {'.mp4','.mov','.avi','.mkv','.mp3','.wav','.flac'}:return '音视频'
    return '其他'
def is_noise(p):
    n=Path(p).name.lower();e=Path(p).suffix.lower()
    return n.startswith('etilqs_') or '_thumb' in n or n.endswith('_temp') or n.endswith('_t.dat') or e in {'.tmp','.temp','.part','.crdownload','.htm','.html'}
def friendly_dat(path):
    """Recognise common files hidden behind WeChat's .dat extension."""
    try:
        with open(path,'rb') as f:head=f.read(16)
    except OSError:return Path(path).name,'其他'
    sigs=((b'\xff\xd8\xff','疑似图片','图片'),(b'\x89PNG','疑似图片','图片'),(b'GIF8','疑似图片','图片'),(b'RIFF','疑似媒体','音视频'),(b'PK\x03\x04','疑似压缩包','压缩包'),(b'%PDF','疑似 PDF','文档'))
    short=hashlib.sha1((str(path)+str(os.path.getsize(path))).encode('utf-8','ignore')).hexdigest()[:6].upper()
    for magic,label,typ in sigs:
        if head.startswith(magic):return f'{label} #{short}',typ
    return f'未知文件 #{short}','其他'
class Handler(FileSystemEventHandler):
    def __init__(self,repo):self.repo=repo
    def on_created(self,e):
        if e.is_directory or is_noise(e.src_path):return
        try:
            s=os.stat(e.src_path);name=Path(e.src_path).name;typ=file_type(e.src_path)
            if Path(e.src_path).suffix.lower()=='.dat':name,typ=friendly_dat(e.src_path)
            self.repo.add_wechat(e.src_path,name,s.st_size,typ,time.time())
        except OSError:pass
class WeChatTracker:
    def __init__(self,repo):self.repo=repo;self.observer=None
    def detect(self):
        # Generic auto-discovery only; no machine-specific paths are hardcoded.
        candidates=[Path.home()/'Documents'/'WeChat Files',
                    Path.home()/'Documents'/'xwechat_files']
        import string
        for letter in string.ascii_uppercase[2:]:
            candidates += [Path(f'{letter}:/xwechat_files'),
                           Path(f'{letter}:/WeChat Files')]
        for p in candidates:
            if p.exists():return str(p)
        return ''
    def start(self,path):
        self.stop();path=path or self.detect()
        if not path or not os.path.exists(path):return False
        self.observer=Observer();self.observer.schedule(Handler(self.repo),path,recursive=True);self.observer.start();return True
    def stop(self):
        if self.observer:
            self.observer.stop();self.observer.join(2);self.observer=None
