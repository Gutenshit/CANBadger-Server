from PyQt4.QtCore import *
from PyQt4.QtGui import *

from ethernet_message import *
from helpers import *

class HijackHandler(QObject):
    def __init__(self, mainwindow, nodehandler):
        super(HijackHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler

    def connect_signals(self):
        self.mainwindow.startSecurityHijackBtn.clicked.connect(self.onStartHijack)

    def setup_ui(self):
        pass

    @pyqtSlot()
    def onStartHijack(self):
        pass