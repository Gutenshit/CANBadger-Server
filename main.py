import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from canbadger_mainwindow import Ui_MainWindow
from node_handler import *
from event_processing_thread import *
from can_logger import *
from uds_handler import *
from tp_handler import *
from hijack_handler import *
from mitm_handler import *
from sd_handler import *
from replay_handler import *
from settings_handler import *
from helpers import *

class MainWindow(QMainWindow, Ui_MainWindow):
    connectToNode = pyqtSignal(dict)
    disconnectNode = pyqtSignal(dict)
    selectedNodeChanged = pyqtSignal(object, dict)

    mainInitDone = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        # set up node handler
        self.nodeHandlerThread = EventProcessingThread()
        self.nodeHandler = NodeHandler(self)
        self.nodeHandler.moveToThread(self.nodeHandlerThread)
        self.nodeHandlerThread.started.connect(self.nodeHandler.onRun)
        self.nodeHandlerThread.start()

        # set up action classes
        self.canLogger = CanLogger(self, self.nodeHandler)
        self.udsHandler = UDSHandler(self, self.nodeHandler)
        self.tpHandler = TPHandler(self, self.nodeHandler)
        self.hijackHandler = HijackHandler(self, self.nodeHandler)
        self.mitmHandler = MITMHandler(self, self.nodeHandler)
        self.sdHandler = SdHandler(self, self.nodeHandler)
        self.replayHandler = ReplayHandler(self, self.nodeHandler)
        self.settingsHandler = SettingsHandler(self, self.nodeHandler)

        self.connectSignals()
        self.show()

        self.selectedNode = None
        self.mainInitDone.emit()

    def connectSignals(self):
        self.actionExit.triggered.connect(self.onExit)
        self.connectedNodesListWidget.itemClicked.connect(self.onNodeItemClicked)
        self.visibleNodesListWidget.itemClicked.connect(self.onNodeItemClicked)
        self.connectDisconnectNodeBtn.clicked.connect(self.onConnectDisconnectBtnClicked)
        self.nodeHandler.newNodeDiscovered.connect(self.onNewNodeDiscovered)
        self.nodeHandler.nodeDisappeared.connect(self.onNodeDisappeared)
        self.nodeHandler.nodeDisconnected.connect(self.onNodeDisconnected)
        self.nodeHandler.nodeConnected.connect(self.onNodeConnected)
        self.connectToNode.connect(self.nodeHandler.onConnectToNode)
        self.disconnectNode.connect(self.nodeHandler.onDisconnectNode)
        self.selectedNodeChanged.connect(self.nodeHandler.onSelectedNodeChanged)
        self.tabWidget.tabBar().currentChanged.connect(self.onTabChanged)
        self.nodeHandler.nodeAliveMessage.connect(self.onUpdateNodeAlive)

        self.canLogger.connect_signals()
        self.udsHandler.connect_signals()
        self.tpHandler.connect_signals()
        self.hijackHandler.connect_signals()
        self.mitmHandler.connect_signals()
        self.sdHandler.connect_signals()
        self.replayHandler.connect_signals()
        self.settingsHandler.connect_signals()

    @pyqtSlot(NodeListItem)
    def onNodeItemClicked(self, item):
        # clear selection from other list so only one item can be active
        # emit signal accordingly
        caller = QObject.sender(self)
        if caller.objectName() == "connectedNodesListWidget":
            self.visibleNodesListWidget.clearSelection()
            self.connectDisconnectNodeBtn.setText("Disconnect")

            # connect node-specific signals
            gracefullyDisconnectSignal(self.saveNodeSettingsBtn.clicked)
            self.saveNodeSettingsBtn.clicked.connect(lambda: self.settingsHandler.onSaveNodeSettings(item.node))
            self.lastIdBroadcastIndicator.setText("N/A")

            prev_node = self.selectedNode
            self.selectedNode = item.node
            self.selectedNodeChanged.emit(prev_node, item.node)
        else:
            self.connectedNodesListWidget.clearSelection()
            self.connectDisconnectNodeBtn.setText("Connect")


    @pyqtSlot()
    def onConnectDisconnectBtnClicked(self):
        # get selected item from unconnected/disconnected list
        # if nothing is selected: do nonothing
        if (len(self.connectedNodesListWidget.selectedItems())) < 1 and\
           (len(self.visibleNodesListWidget.selectedItems()) < 1):
            return
        if len(self.connectedNodesListWidget.selectedItems()) < 1:
            # connect
            item = self.visibleNodesListWidget.currentItem()
            self.connectToNode.emit(item.getNode())
        else:
            # disconnect
            item = self.connectedNodesListWidget.currentItem()
            self.disconnectNode.emit(item.getNode())
            self.onNodeDisconnected(item.getNode())

    @pyqtSlot(dict)
    def onNewNodeDiscovered(self, node):
        item = NodeListItem(self.visibleNodesListWidget, node)
        self.visibleNodesListWidget.addItem(item)

    @pyqtSlot(dict)
    def onNodeDisappeared(self, node):
        # go through all items, find the matching one and remove it
        for item in self.visibleNodesListWidget.findItems("%s:%s" % (node["id"], node["ip"]), Qt.MatchContains):
            row = self.visibleNodesListWidget.row(item)
            self.visibleNodesListWidget.takeItem(row)
            self.debugLogPlainTextEdit.appendPlainText("--- Node %s disappeared" % node["id"])

    @pyqtSlot(dict)
    def onNodeDisconnected(self, node):
        # go through all items, find the matching one and remove it
        for item in self.connectedNodesListWidget.findItems("%s:%s" % (node["id"], node["ip"]), Qt.MatchContains):
            row = self.connectedNodesListWidget.row(item)
            self.connectedNodesListWidget.takeItem(row)
            self.debugLogPlainTextEdit.appendPlainText("--- Node %s disconnected" % node["id"])

    @pyqtSlot(dict)
    def onNodeConnected(self, node):
        self.connectedNodesListWidget.addItem(NodeListItem(self.connectedNodesListWidget, node))
        # remove from visible list
        for item in self.visibleNodesListWidget.findItems("%s:%s" % (node["id"], node["ip"]), Qt.MatchContains):
            row = self.visibleNodesListWidget.row(item)
            self.visibleNodesListWidget.takeItem(row)

    @pyqtSlot(str)
    def onUpdateDebugLog(self, msg):
        self.debugLogPlainTextEdit.appendPlainText(QString(msg))
        self.tabWidget.tabBar().setTabTextColor(0, Qt.yellow)
        self.statusbar.showMessage(QString(msg))

    @pyqtSlot(int)
    def onTabChanged(self, index):
        if index == 0:
            self.tabWidget.tabBar().setTabTextColor(0, Qt.black)

    @pyqtSlot(dict)
    def onUpdateNodeAlive(self, node):
        if self.selectedNode == node:
            self.lastIdBroadcastIndicator.setText(str(node["last_seen"]))

    @pyqtSlot()
    def onExit(self):
        exit(0)

if __name__ == '__main__':
   app = QApplication(sys.argv)
   mainWin = MainWindow()
   ret = app.exec_()
   sys.exit( ret )
