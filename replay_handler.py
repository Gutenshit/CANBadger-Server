from PyQt4.QtCore import *
from PyQt4.QtGui import *
from copy import *

from node_connection import *
from helpers import *
from can_logger_table_model import *

class ReplayHandler(QObject):
    def __init__(self, mainwindow, nodehandler):
        super(ReplayHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.model = CanLoggerTableModel(self.mainwindow.replayFramesTableView)
        self.currentRowModelIndex = None
        self.selectionModel = None

    def connect_signals(self):
        self.mainwindow.mainInitDone.connect(self.setup_gui)
        self.mainwindow.tabWidget_2.tabBar().currentChanged.connect(self.onTabChanged)
        self.mainwindow.replayRemoveFrameBtn.clicked.connect(self.onRemoveFrame)
        self.mainwindow.startReplayBtn.clicked.connect(self.onStartReplay)
        self.mainwindow.replayFrameIdLineEdit.textEdited.connect(self.onFrameIdEdited)
        self.mainwindow.replayPayloadLineEdit.textEdited.connect(self.onFramePayloadEdited)
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)
        self.mainwindow.addReplayFrameBtn.clicked.connect(self.onAddReplayFrameClicked)
        self.mainwindow.replayMoveUpBtn.clicked.connect(self.onMoveUpFrame)
        self.mainwindow.replayMoveDownBtn.clicked.connect(self.onMoveDownFrame)

    @pyqtSlot()
    def setup_gui(self):
        self.mainwindow.replayFramesTableView.setModel(self.model)
        self.mainwindow.replayFramesTableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mainwindow.replayFramesTableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.selectionModel = self.mainwindow.replayFramesTableView.selectionModel()
        self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)


    @pyqtSlot(QModelIndex, QModelIndex)
    def onCurrentRowChanged(self, current, prev):
        if self.currentRowModelIndex is None:
            self.setEditingEnabled(True)
        if current is None:
            self.setEditingEnabled(False)
            self.mainwindow.replayFrameIdLineEdit.setText('')
            self.mainwindow.replayPayloadLineEdit.setText('')
        else:
            # update values
            self.setEditingEnabled(True)
            frame = self.model.getFrame(current)
            self.mainwindow.replayFrameIdLineEdit.setText(frame[1])
            self.mainwindow.replayPayloadLineEdit.setText(str(frame[2]))
        self.currentRowModelIndex = current


    def setEditingEnabled(self, value):
        self.mainwindow.replayFrameIdLineEdit.setEnabled(value)
        self.mainwindow.replayPayloadLineEdit.setEnabled(value)
        self.mainwindow.replayRemoveFrameBtn.setEnabled(value)

    @pyqtSlot()
    def onRemoveFrame(self):
        self.model.removeFrame(self.currentRowModelIndex)

    @pyqtSlot()
    def onStartReplay(self):
        node = self.mainwindow.selectedNode
        connection = node['connection']
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.onReplayAcked)
        connection.nackReceived.connect(self.onReplayError)

        # preformat and put frames into queue
        formatted_frames = []
        for frame in self.model.getFrames():
            id = struct.pack('h', int(str(frame[1]), 16))
            frame_payload_raw = str(QByteArray.fromHex(frame[2]))
            payload = struct.pack("%ds" % len(frame_payload_raw), frame_payload_raw)
            formatted_frames.append(id + payload)

        connection.sendMessage(EthernetMessage('ACTION', 'START_REPLAY', 0, ''))
        connection.fillFrameQueue(formatted_frames)
        connection.sendNextFrame()

    @pyqtSlot()
    def onReplayAcked(self):
        node = self.mainwindow.selectedNode
        connection = node['connection']
        if not connection.sendNextFrame():
            self.mainwindow.onUpdateDebugLog("Replay finished!")
            gracefullyDisconnectSignal(connection.ackReceived)
            gracefullyDisconnectSignal(connection.nackReceived)
            connection.sendMessage(EthernetMessage('ACTION', 'STOP_CURRENT_ACTION', 0, ''))

    @pyqtSlot()
    def onReplayError(self):
        self.mainwindow.onUpdateDebugLog("Error replaying!")

    @pyqtSlot(QString)
    def onFrameIdEdited(self, text):
        self.model.updateFrame(self.currentRowModelIndex, {'ID': text})

    @pyqtSlot(QString)
    def onFramePayloadEdited(self, text):
        self.model.updateFrame(self.currentRowModelIndex, {'Payload': text})

    @pyqtSlot(list)
    def onAddReplayFrame(self, frame):
        self.model.addFrame(deepcopy(frame))
        self.selectionModel.select(self.model.createIndex(self.model.rowCount()-1, 0), QItemSelectionModel.SelectCurrent)
        self.mainwindow.tabWidget_2.tabBar().setTabTextColor(1, Qt.yellow)

    @pyqtSlot()
    def onAddReplayFrameClicked(self):
        if self.mainwindow.selectedNode is not None:
            self.model.addFrame([0, "", ""])
            self.selectionModel.select(self.model.createIndex(self.model.rowCount() - 1, 0),
                                       QItemSelectionModel.SelectCurrent)

    @pyqtSlot(int)
    def onTabChanged(self, index):
        if index == 1:
            self.mainwindow.tabWidget_2.tabBar().setTabTextColor(1, Qt.black)

    @pyqtSlot(object, dict)
    def onSelectedNodeChanged(self, previous, current):
        if current is not None:
            if previous is not None:
                if "replay" not in previous:
                    previous["replay"] = {}
                previous["replay"]["model"] = self.model
            if "replay" not in current:
                current["replay"] = {}
                current["replay"]["model"] = CanLoggerTableModel()
            self.model = current["replay"]["model"]
            self.mainwindow.replayFramesTableView.setModel(self.model)
            self.selectionModel = self.mainwindow.replayFramesTableView.selectionModel()
            gracefullyDisconnectSignal(self.selectionModel.currentRowChanged)
            self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)

        self.setEditingEnabled(False)

    @pyqtSlot()
    def onMoveUpFrame(self):
        if self.model.moveUpFrame(self.currentRowModelIndex):
            newindex = self.model.createIndex(self.currentRowModelIndex.row() - 1, 0)
            self.selectionModel.select(newindex, QItemSelectionModel.SelectCurrent)
            self.currentRowModelIndex = newindex

    @pyqtSlot()
    def onMoveDownFrame(self):
        if self.model.moveDownFrame(self.currentRowModelIndex):
            newindex = self.model.createIndex(self.currentRowModelIndex.row() + 1, 0)
            self.selectionModel.select(newindex, QItemSelectionModel.SelectCurrent)
            self.currentRowModelIndex = newindex