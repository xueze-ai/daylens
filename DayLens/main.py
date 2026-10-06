import sys,os,json
# Select the Windows text renderer before Qt is imported. GDI is the safest
# default for Chinese text on systems where DirectWrite produced mojibake.
try:
    cfg_path=os.path.join(os.environ.get('APPDATA',''),'DayLens','config.json')
    engine=(json.load(open(cfg_path,encoding='utf-8')).get('font_engine','gdi') if os.path.exists(cfg_path) else 'gdi')
    if sys.platform=='win32' and '-platform' not in sys.argv:
        sys.argv.extend(['-platform','windows:fontengine='+('freetype' if engine=='freetype' else 'gdi' if engine=='gdi' else 'directwrite')])
except Exception:pass
from PySide6.QtWidgets import QApplication,QMessageBox,QSystemTrayIcon
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QFont
from PySide6.QtNetwork import QLocalServer,QLocalSocket
from config.manager import load_config
from db.repository import Repository
from core.file_monitor import FileMonitor
from core.window_tracker import WindowTracker
from core.installer_tracker import InstallerTracker
from core.browser_tracker import BrowserTracker
from core.wechat_tracker import WeChatTracker
from core.auto_tasks import AutoTasks
from core.snapshot import capture
from datetime import datetime
import threading,logging
from logging.handlers import TimedRotatingFileHandler
from config.manager import APP_DIR
log_dir=APP_DIR/'logs';log_dir.mkdir(parents=True,exist_ok=True);handler=TimedRotatingFileHandler(log_dir/'daylens.log',when='midnight',backupCount=14,encoding='utf-8');logging.basicConfig(level=logging.INFO,handlers=[handler],format='%(asctime)s %(levelname)s %(message)s')
from ui.main_window import MainWindow
from ui.tray import Tray,icon

class App:
    def __init__(self):
        self.qt=QApplication(sys.argv);self.qt.setFont(QFont('Microsoft YaHei',9));self.qt.setApplicationName('DayLens');self.qt.setApplicationVersion('1.0.9');self.qt.setWindowIcon(icon());self.qt.setQuitOnLastWindowClosed(False)
        self.secondary=False;probe=QLocalSocket();probe.connectToServer('DayLens-V1-SingleInstance')
        if probe.waitForConnected(350):
            probe.write(b'show');probe.waitForBytesWritten(350);probe.disconnectFromServer();self.secondary=True;return
        QLocalServer.removeServer('DayLens-V1-SingleInstance');self.instance_server=QLocalServer(self.qt);self.instance_server.listen('DayLens-V1-SingleInstance');self.pending_show=False;self.instance_server.newConnection.connect(self.show_existing)
        self.config=load_config();self.repo=Repository();self.files=FileMonitor(self.repo);self.windows=WindowTracker(self.repo);self.installs=InstallerTracker(self.repo);self.browser=None;self.wechat=WeChatTracker(self.repo);self.source_generation=0;self.window=MainWindow(self.repo,self.config);self.window.config_changed.connect(self.reconfigure);self.tray=Tray(self.window);self.tray.show();self.auto=AutoTasks(self.repo,lambda:self.config,self.notice);self.auto.start();self.reconfigure(self.config);self.auto_snapshot();self.daily_timer=QTimer(self.qt);self.daily_timer.timeout.connect(self.auto_snapshot);self.daily_timer.start(300000);QTimer.singleShot(5000,lambda:threading.Thread(target=self.repo.cleanup,args=(self.config['retention_days'],),daemon=True).start())
        self.qt.aboutToQuit.connect(self.stop)
        if '--background' not in sys.argv or self.pending_show:self.reveal_window()
    def reconfigure(self,config):
        self.config=config;self.files.start(config.get('watch_dirs') or config['drives']);self.windows.idle_seconds=config.get('idle_minutes',5)*60;self.windows.start();self.installs.start();self.source_generation+=1;generation=self.source_generation
        if self.browser:self.browser.stop()
        self.browser=None;self.wechat.stop();QTimer.singleShot(3000,lambda:self.start_sources(generation))
    def start_sources(self,generation):
        if generation!=self.source_generation:return
        self.browser=BrowserTracker(self.repo,self.config);self.browser.start()
        if self.config.get('wechat_enabled',True):self.wechat.start(self.config.get('wechat_path',''))
    def auto_snapshot(self):
        day=datetime.now().strftime('%Y-%m-%d')
        if self.config.get('auto_snapshot',True) and self.repo.get_kv('auto_snapshot_day')!=day:
            def run():
                try:self.repo.add_snapshot('自动快照 '+datetime.now().strftime('%Y-%m-%d %H:%M'),capture(self.config['drives']));self.repo.set_kv('auto_snapshot_day',day);self.notice('今日自动快照已完成')
                except Exception as e:self.notice('自动快照失败：'+str(e))
            threading.Thread(target=run,daemon=True).start()
    def notice(self,text):self.tray.showMessage('DayLens',text,QSystemTrayIcon.Information,5000)
    def show_existing(self):
        while self.instance_server.hasPendingConnections():
            sock=self.instance_server.nextPendingConnection();sock.waitForReadyRead(100);sock.readAll();sock.disconnectFromServer()
        if not hasattr(self,'window'):self.pending_show=True;return
        self.reveal_window()
    def reveal_window(self):
        self.pending_show=False;self.window.setWindowState((self.window.windowState()&~Qt.WindowMinimized)|Qt.WindowActive);self.window.showNormal();self.window.show();self.window.raise_();self.window.activateWindow()
        try:
            import ctypes;hwnd=int(self.window.winId());ctypes.windll.user32.ShowWindow(hwnd,9);ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:pass
    def stop(self):self.window.shutdown_tasks();self.files.stop();self.windows.stop();self.installs.stop();self.wechat.stop();self.auto.stop();self.browser.stop() if self.browser else None
    def run(self):return 0 if self.secondary else self.qt.exec()
if __name__=='__main__':sys.exit(App().run())
