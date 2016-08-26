from PyQt4.QtCore import *
from PyQt4.QtNetwork import *
from PyQt4.QtGui import *
import datetime
from node_list_item import *
from node_connection import *
from canbadger_mainwindow import *
from helpers import *

##
# handle discovery and connection of nodes
class NodeHandler(QObject):

    newNodeDiscovered = pyqtSignal(dict)
    nodeConnected = pyqtSignal(dict)
    nodeDisconnected = pyqtSignal(dict)
    nodeDisappeared = pyqtSignal(dict)
    nodeAliveMessage = pyqtSignal(dict)

    threadReady = pyqtSignal()

    def __init__(self, mainwindow):
        super(QObject, self).__init__()
        self.visibleNodes = {}
        self.connectedNodes = {}
        self.nodeListMutex = QMutex()
        self.mainwindow = mainwindow

    @pyqtSlot()
    def onRun(self):
        # multithreading hack to prevent threading sigsev conditions
        # all the stuff should be executed in this threads event loop
        # if we do stuff here, the thread context could be different
        self.threadReady.connect(self.onThreadReady)
        self.threadReady.emit()

    @pyqtSlot()
    def onThreadReady(self):
        self.udpSocket = QUdpSocket(self)
        self.udpSocket.bind(13370, QUdpSocket.ShareAddress)
        self.udpSocket.readyRead.connect(self.onSocketReadyRead)

        # check every second
        self.disconnectTimer = QTimer(self)
        self.disconnectTimer.moveToThread(self.thread())
        self.disconnectTimer.timeout.connect(self.onDisconnectTimerFire)
        self.disconnectTimer.start(1*1000)


    @pyqtSlot()
    def onSocketReadyRead(self):
        msg = self.udpSocket.readDatagram(self.udpSocket.pendingDatagramSize())
        if msg[0][0:2] == "CB":
            msg_split = msg[0].split('|')
            device_id = msg_split[1]
            device_version = msg_split[2]
            now = datetime.datetime.now()
            device = {"id": device_id, "version": device_version, "ip": str(msg[1].toString()), "last_seen": now}
            self.nodeListMutex.lock()
            if (device_id not in self.connectedNodes.iterkeys()) and \
                    (device_id not in self.visibleNodes.iterkeys()):
                self.visibleNodes[device_id] = device
                self.newNodeDiscovered.emit(device)
            # update timestamps for known visible/connected devices
            if device_id in self.visibleNodes.iterkeys():
                self.visibleNodes[device_id]["last_seen"] = now
                self.nodeAliveMessage.emit(self.visibleNodes[device_id])
            if device_id in self.connectedNodes.iterkeys():
                self.connectedNodes[device_id]["last_seen"] = now
                self.nodeAliveMessage.emit(self.connectedNodes[device_id])
            self.nodeListMutex.unlock()


    @pyqtSlot()
    def onDisconnectTimerFire(self):
        now = datetime.datetime.now()
        self.nodeListMutex.lock()
        ids_to_delete = []
        for id, node in self.visibleNodes.iteritems():
            # check time difference
            if (now - node["last_seen"]) > datetime.timedelta(seconds=5):
                ids_to_delete.append(id)
                self.nodeDisappeared.emit(node)
        for id in ids_to_delete:
            del self.visibleNodes[id]
        ids_to_delete = []
        for id, node in self.connectedNodes.iteritems():
            # check time difference
            if (now - node["last_seen"]) > datetime.timedelta(seconds=5):
                ids_to_delete.append(id)
                self.nodeDisconnected.emit(node)
        for id in ids_to_delete:
            del self.connectedNodes[id]
        self.nodeListMutex.unlock()


    @pyqtSlot(dict)
    def onConnectToNode(self, node):
        thread = QThread()
        node["thread"]  = thread
        con = NodeConnection(node)
        node["connection"] = con
        con.moveToThread(thread)
        node["thread"].started.connect(node["connection"].onRun)
        con.connectionSucceeded.connect(self.onConnectionSucceeded)
        con.newDebugMessage.connect(self.mainwindow.onUpdateDebugLog)
        thread.start()

    @pyqtSlot()
    def onConnectionSucceeded(self):
        node = self.sender()
        del self.visibleNodes[node.node["id"]]
        self.connectedNodes[node.node["id"]] = node.node
        self.nodeConnected.emit(node.node)
        node.node["connection"].nodeDisconnected.connect(self.onDisconnectNode)

    @pyqtSlot(dict)
    def onDisconnectNode(self, node):
        # for now, just reset node and remove it from internal list
        node["connection"].resetNode()
        if node["id"] in self.connectedNodes:
            del self.connectedNodes[node["id"]]
        if node["id"] in self.visibleNodes:
            del self.visibleNodes[node["id"]]
        if self.mainwindow.selectedNode == node:
            self.mainwindow.connectDisconnectNodeBtn.setText("Connect")

    @pyqtSlot(dict)
    def onSelectedNodeChanged(self, node):
        pass