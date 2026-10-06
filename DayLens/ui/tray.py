from PySide6.QtWidgets import QSystemTrayIcon,QMenu,QApplication
from PySide6.QtGui import QAction,QIcon
from pathlib import Path
import sys

def icon():
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
    return QIcon(str(base/'assets'/'logo.png'))
class Tray(QSystemTrayIcon):
    def __init__(self,window):
        super().__init__(icon(),window);self.window=window;self.setToolTip('DayLens 每日镜 · 正在记录')
        m=QMenu();show=QAction('打开 DayLens',m);show.triggered.connect(self.open);m.addAction(show);m.addSeparator();quit=QAction('退出',m);quit.triggered.connect(QApplication.quit);m.addAction(quit);self.setContextMenu(m);self.activated.connect(lambda r:self.open() if r==QSystemTrayIcon.DoubleClick else None)
    def open(self):self.window.show();self.window.raise_();self.window.activateWindow()
