from PySide6.QtWidgets import QWidget,QToolTip
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtCore import Qt,QRectF,Signal
from datetime import datetime
class TimelineWidget(QWidget):
    rangeSelected=Signal(float,float)
    colors=['#2D7FF9','#14B8A6','#8B5CF6','#F59E0B','#EF4444','#06B6D4','#84CC16','#EC4899']
    def __init__(self):super().__init__();self.setMinimumHeight(104);self.setMouseTracking(True);self.setFocusPolicy(Qt.StrongFocus);self.setCursor(Qt.OpenHandCursor);self.sessions=[];self.drag=None;self.view_hours=24.0;self.center_hour=12.0
    def set_sessions(self,s):self.sessions=s;self.update()
    def bounds(self):
        width=min(24.0,max(1.0,self.view_hours));half=width/2;self.center_hour=max(half,min(24-half,self.center_hour));return self.center_hour-half,self.center_hour+half
    def paintEvent(self,_):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=self.rect().adjusted(12,20,-12,-24);track=QRectF(r.x(),r.y(),r.width(),r.height()-20);p.setPen(QColor('#CBD2DF'));p.drawRoundedRect(track,6,6)
        if not self.sessions:p.setPen(QColor('#8A94A7'));p.drawText(r,Qt.AlignCenter,'今天还没有活动记录')
        start,end=self.bounds();span=end-start
        grid=0.25 if span<=3 else 0.5 if span<=8 else 1 if span<=14 else 2
        first=int(start/grid)*grid
        h=first
        while h<=end+0.001:
            x=r.x()+r.width()*(h-start)/span
            major=abs(h-round(h))<0.001;p.setPen(QColor('#D8DEE8') if major else QColor('#EDF0F5'));p.drawLine(int(x),int(track.top()+3),int(x),int(track.bottom()-3))
            if major or span<=4:p.setPen(QColor('#7D8798'));p.drawText(int(x-18),r.bottom(),36,18,Qt.AlignCenter,f'{int(h)%24:02d}:{int(round((h%1)*60))%60:02d}')
            h+=grid
        for x in self.sessions:
            d=datetime.fromtimestamp(x[2]);e=datetime.fromtimestamp(x[3]);ah=d.hour+d.minute/60+d.second/3600;bh=e.hour+e.minute/60+e.second/3600
            if bh<start or ah>end:continue
            a=(max(start,ah)-start)/span;b=(min(end,bh)-start)/span;col='#B8BEC9' if x[0]=='__idle__' else self.colors[hash(x[0])%len(self.colors)];p.fillRect(QRectF(r.x()+r.width()*a,track.top()+6,max(2,r.width()*(b-a)),track.height()-12),QColor(col))
        p.setPen(QColor('#8A94A7'));p.drawText(r.x(),14,f'可视范围 {start:05.2f}–{end:05.2f} · {span:g} 小时')
    def hour_at(self,x):
        start,end=self.bounds();return start+max(0,min(1,(x-12)/max(1,self.width()-24)))*(end-start)
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton:self.drag=(e.position().x(),self.center_hour);self.setCursor(Qt.ClosedHandCursor);e.accept()
    def mouseMoveEvent(self,e):
        if self.drag:
            dx=e.position().x()-self.drag[0];self.center_hour=self.drag[1]-dx/max(1,self.width()-24)*self.view_hours;self.bounds();self.update();return
        if not self.sessions:return
        sec=self.hour_at(e.position().x())*3600;day=datetime.fromtimestamp(self.sessions[0][2]).replace(hour=0,minute=0,second=0,microsecond=0).timestamp();t=day+sec
        for x in self.sessions:
            if x[2]<=t<=x[3]:
                seconds=max(0,int(x[3]-x[2]));mins,secs=divmod(seconds,60);QToolTip.showText(e.globalPosition().toPoint(),f"{x[1]}\n{datetime.fromtimestamp(x[2]):%H:%M:%S} – {datetime.fromtimestamp(x[3]):%H:%M:%S}\n持续 {mins} 分 {secs} 秒",self);break
    def mouseReleaseEvent(self,e):
        if e.button()==Qt.LeftButton:self.drag=None;self.setCursor(Qt.OpenHandCursor);e.accept()
    def mouseDoubleClickEvent(self,_):self.view_hours=24;self.center_hour=12;self.update();self.rangeSelected.emit(0,0)
    def wheelEvent(self,e):
        old_start,old_end=self.bounds();fraction=max(0,min(1,(e.position().x()-12)/max(1,self.width()-24)));anchor=old_start+fraction*(old_end-old_start);factor=.75 if e.angleDelta().y()>0 else 1/.75;new_hours=max(1.0,min(24.0,self.view_hours*factor));new_start=anchor-fraction*new_hours;new_start=max(0,min(24-new_hours,new_start));self.view_hours=new_hours;self.center_hour=new_start+new_hours/2;self.update();e.accept()
