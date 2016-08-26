from PyQt4.QtCore import *

from helpers import *

class SettingsHandler(QObject):
    def __init__(self, mainwindow, nodehandler):
        super(SettingsHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler

    def connect_signals(self):
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)

    @pyqtSlot(dict)
    def onSaveNodeSettings(self, node):
        text = self.mainwindow.nodeIdLineEdit.text()
        if text != node["id"] and len(text) > 0:
            # update settings
            gracefullyDisconnectSignal(node['connection'].ackReceived)
            gracefullyDisconnectSignal(node['connection'].nackReceived)
            node['connection'].ackReceived.connect(self.onSettingsAck)
            node['connection'].nackReceived.connect(self.onSettingsNack)
            node['connection'].updateSettings({ 'id': self.mainwindow.nodeIdLineEdit.text()})

    @pyqtSlot()
    def onSettingsAck(self):
        node = self.mainwindow.selectedNode
        gracefullyDisconnectSignal(node['connection'].ackReceived)
        gracefullyDisconnectSignal(node['connection'].nackReceived)
        self.mainwindow.onUpdateDebugLog("Settings saved!")

    @pyqtSlot()
    def onSettingsNack(self):
        node = self.mainwindow.selectedNode
        gracefullyDisconnectSignal(node['connection'].ackReceived)
        gracefullyDisconnectSignal(node['connection'].nackReceived)
        self.mainwindow.onUpdateDebugLog("Error saving settings!")

    @pyqtSlot(dict)
    def onSelectedNodeChanged(self, node):
        self.mainwindow.nodeIdLineEdit.setText("")
