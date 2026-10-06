import os,time
from pathlib import Path
from core.file_monitor import allowed

def capture(roots,progress=None):
    result={};count=0
    for root in roots:
        if not os.path.exists(root):continue
        for base,dirs,files in os.walk(root):
            dirs[:]=[d for d in dirs if allowed(os.path.join(base,d))]
            for name in files:
                p=os.path.join(base,name)
                if not allowed(p):continue
                try:s=os.stat(p);result[p]=[s.st_size,int(s.st_mtime)]
                except OSError:continue
                count+=1
                if progress and count%1000==0:progress(count,p)
    return result
def compare(a,b):
    ak,bk=set(a),set(b)
    return {'added':[{'path':p,'size':b[p][0]} for p in sorted(bk-ak)],'deleted':[{'path':p,'size':a[p][0]} for p in sorted(ak-bk)],'modified':[{'path':p,'before':a[p],'after':b[p]} for p in sorted(ak&bk) if a[p]!=b[p]]}
