from PySide6.QtCore import Qt,QDate,QPoint,Signal
from PySide6.QtGui import QColor,QFont,QKeyEvent,QPainter
from PySide6.QtWidgets import (QComboBox,QDialog,QGraphicsDropShadowEffect,QGridLayout,
    QHBoxLayout,QLabel,QPushButton,QVBoxLayout,QWidget)

WEEKDAYS=('一','二','三','四','五','六','日')

class DayCell(QWidget):
    clicked=Signal(QDate)
    def __init__(self,date,current_month,selected,has_record,parent=None):
        super().__init__(parent);self.date=date;self.current_month=current_month;self.selected=selected;self.has_record=has_record
        self.setFixedSize(42,38);self.setCursor(Qt.PointingHandCursor if current_month else Qt.ArrowCursor)
    def mousePressEvent(self,event):
        if self.current_month:self.clicked.emit(self.date)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=self.rect().adjusted(2,1,-2,-1)
        if self.selected:p.setBrush(QColor('#2D7FF9'));p.setPen(Qt.NoPen);p.drawRoundedRect(r,8,8)
        elif self.date==QDate.currentDate():p.setPen(QColor('#2D7FF9'));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r,8,8)
        p.setFont(QFont('Microsoft YaHei',10,QFont.DemiBold if self.selected else QFont.Normal))
        p.setPen(QColor('#FFFFFF') if self.selected else QColor('#172033') if self.current_month else QColor('#B8C0CE'))
        p.drawText(r,Qt.AlignCenter,str(self.date.day()))
        if self.has_record:
            p.setPen(Qt.NoPen);p.setBrush(QColor('#FFFFFF') if self.selected else QColor('#2D7FF9'));p.drawEllipse(r.center().x()-2,r.bottom()-5,4,4)

class CustomDatePicker(QDialog):
    date_selected=Signal(QDate)
    def __init__(self,repo,date,parent=None):
        super().__init__(parent,Qt.Popup|Qt.FramelessWindowHint);self.repo=repo;self.selected=date;self.view=QDate(date.year(),date.month(),1)
        self.setAttribute(Qt.WA_TranslucentBackground);self.setFixedWidth(342);self.records=set(repo.activity_days(400))
        shadow=QGraphicsDropShadowEffect(self);shadow.setBlurRadius(28);shadow.setOffset(0,8);shadow.setColor(QColor(0,0,0,50))
        panel=QWidget();panel.setObjectName('datePanel');panel.setGraphicsEffect(shadow);root=QVBoxLayout(self);root.setContentsMargins(18,18,18,24);root.addWidget(panel)
        lay=QVBoxLayout(panel);lay.setContentsMargins(16,14,16,14);lay.setSpacing(10)
        nav=QHBoxLayout();prev=QPushButton('‹');prev.setFixedSize(32,32);prev.clicked.connect(lambda:self.shift(-1));nav.addWidget(prev)
        self.year=QComboBox();self.year.addItems([str(y) for y in range(2000,2101)]);self.year.setCurrentText(str(date.year()));self.year.currentTextChanged.connect(self.combo_changed);nav.addWidget(self.year)
        self.month=QComboBox();self.month.addItems([f'{m} 月' for m in range(1,13)]);self.month.setCurrentIndex(date.month()-1);self.month.currentIndexChanged.connect(self.combo_changed);nav.addWidget(self.month)
        nxt=QPushButton('›');nxt.setFixedSize(32,32);nxt.clicked.connect(lambda:self.shift(1));nav.addWidget(nxt);lay.addLayout(nav)
        week=QGridLayout();week.setHorizontalSpacing(1)
        for i,w in enumerate(WEEKDAYS):lab=QLabel(w);lab.setAlignment(Qt.AlignCenter);lab.setObjectName('weekday');week.addWidget(lab,0,i)
        lay.addLayout(week);self.grid=QGridLayout();self.grid.setSpacing(1);lay.addLayout(self.grid)
        foot=QHBoxLayout();today=QPushButton('今天');today.clicked.connect(lambda:self.choose(QDate.currentDate()));foot.addWidget(today);foot.addStretch();self.hint=QLabel('蓝点表示有记录');self.hint.setObjectName('muted');foot.addWidget(self.hint);lay.addLayout(foot)
        panel.setStyleSheet("""#datePanel{background:#fff;border:1px solid #DDE3ED;border-radius:12px} QPushButton{border:0;background:#F2F5F9;border-radius:7px;padding:6px 10px} QPushButton:hover{background:#E7EEFA} QComboBox{border:1px solid #DDE3ED;border-radius:7px;padding:5px 9px;background:#fff} #weekday{color:#7B879B;font-weight:600} #muted{color:#8A94A6;font-size:11px}""")
        self.render();self.setFocusPolicy(Qt.StrongFocus)
    def combo_changed(self,*_):
        if not self.year.currentText():return
        self.view=QDate(int(self.year.currentText()),self.month.currentIndex()+1,1);self.render()
    def shift(self,months):
        self.view=self.view.addMonths(months);self.year.blockSignals(True);self.month.blockSignals(True);self.year.setCurrentText(str(self.view.year()));self.month.setCurrentIndex(self.view.month()-1);self.year.blockSignals(False);self.month.blockSignals(False);self.render()
    def render(self):
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget():item.widget().deleteLater()
        start=self.view.addDays(1-self.view.dayOfWeek())
        for i in range(42):
            d=start.addDays(i);cell=DayCell(d,d.month()==self.view.month(),d==self.selected,d.toString('yyyy-MM-dd') in self.records);cell.clicked.connect(self.choose);self.grid.addWidget(cell,i//7,i%7)
    def choose(self,date):self.selected=date;self.date_selected.emit(date);self.accept()
    def keyPressEvent(self,event:QKeyEvent):
        moves={Qt.Key_Left:-1,Qt.Key_Right:1,Qt.Key_Up:-7,Qt.Key_Down:7}
        if event.key() in moves:self.selected=self.selected.addDays(moves[event.key()]);self.view=QDate(self.selected.year(),self.selected.month(),1);self.render()
        elif event.key() in (Qt.Key_Return,Qt.Key_Enter):self.choose(self.selected)
        elif event.key()==Qt.Key_Escape:self.reject()
        else:super().keyPressEvent(event)
