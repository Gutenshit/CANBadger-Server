from PyQt4.QtCore import *
from PyQt4.QtGui import *
import json

from node_connection import *
from can_logger_table_model import *
from can_parser import *
from helpers import *
from frame_count_sort_model import *

class CanLogger:
    def __init__(self, mainwindow, nodehandler):
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.cnt = 0
        self.model = None
        #self.original_frames = [] # used to store the raw frames before filtering
        self.filterById = False
        self.filterAfterNSamples = False
        self.countSortProxy = None
        self.stopped = False

    def connect_signals(self):
        self.mainwindow.startCanLoggerBtn.clicked.connect(self.onStartCanLogger)
        self.mainwindow.canLogTableView.sendToReplay.connect(self.mainwindow.replayHandler.onAddReplayFrame)
        self.mainwindow.canLogTableView.createRuleForId.connect(self.mainwindow.mitmHandler.onCreateRuleForId)
        self.mainwindow.canLogTableView.createRuleForPayload.connect(self.mainwindow.mitmHandler.onCreateRuleForPayload)
        self.mainwindow.filterFramesByIdCheckbox.stateChanged.connect(self.onFilterByIdStateChanged)
        self.mainwindow.filterFramesByNewFramesAfterCheckbox.stateChanged.connect(self.onFilterAfterNFramesStateChanged)
        self.mainwindow.filterFramesByIdLineEdit.textEdited.connect(self.filterFrames)
        self.mainwindow.filterFramesAfterNSpinBox.valueChanged.connect(self.filterFrames)
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)
        self.mainwindow.mainInitDone.connect(self.setup_gui)
        self.mainwindow.saveCanLogBtn.clicked.connect(self.onSaveFramesToFile)

    @pyqtSlot()
    def setup_gui(self):
        self.mainwindow.canLogTableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mainwindow.canLogTableView.setSelectionMode(QAbstractItemView.SingleSelection)

    @pyqtSlot()
    def filterFrames(self):
        if self.model is None:
            return
        self.countSortProxy.invalidate()

    @pyqtSlot()
    def onStartCanLogger(self):
        node = self.mainwindow.selectedNode

        # reset the ui model first
        self.original_frames = []
        self.model = CanLoggerTableModel(self.mainwindow.canLogTableView)
        self.countSortProxy = FrameCountSortModel(self.mainwindow)
        self.countSortProxy.filteringEnabled = False
        self.countSortProxy.setSourceModel(self.model)
        self.mainwindow.canLogTableView.setModel(self.countSortProxy)
        self.mainwindow.canLogTableView.setSortingEnabled(False)
        self.countSortProxy.setDynamicSortFilter(False)
        # get selected node, set test mode and start logger

        self.stopped = False

        if node is None or "connection" not in node:
            # raise "Error: No node selected!"
            # todo: testing, remove
            self.model.addFrame([0, "07ef", "1122334455667788"])
            self.model.addFrame([1, "07d9", "aabbccddeeff0011"])
        else:
            node['connection'].newDataMessage.connect(self.onNewData)
            node['connection'].runCanloggerTest()
            self.mainwindow.startCanLoggerBtn.clicked.disconnect()
            self.mainwindow.startCanLoggerBtn.clicked.connect(self.onStopCanLogger)
            self.mainwindow.startCanLoggerBtn.setText("Stop")

    @pyqtSlot()
    def onStopCanLogger(self):
        self.cnt = 0
        gracefullyDisconnectSignal(self.mainwindow.selectedNode['connection'].newDataMessage)
        self.mainwindow.selectedNode['connection'].stopCurrentAction()
        self.mainwindow.startCanLoggerBtn.clicked.disconnect()
        self.mainwindow.startCanLoggerBtn.clicked.connect(self.onStartCanLogger)
        self.mainwindow.startCanLoggerBtn.setText("Start")
        self.countSortProxy.filteringEnabled = True
        self.countSortProxy.setDynamicSortFilter(True)
        self.mainwindow.canLogTableView.setSortingEnabled(True)
       # self.filterFrames()

    @pyqtSlot(str)
    def onNewData(self, data):
        self.cnt += 1
        # print self.cnt
        frame = CanParser.parseSingleFrame(data)
        frame_entry = [self.cnt, frame['id'], frame['payload']]
        self.model.addFrame(frame_entry)

    @pyqtSlot(int)
    def onFilterByIdStateChanged(self, state):
        if state == 2:
            self.countSortProxy.filterById = True
        else:
            self.countSortProxy.filterById = False
        self.countSortProxy.invalidate()

    @pyqtSlot(int)
    def onFilterAfterNFramesStateChanged(self, state):
        if state == 2:
            self.countSortProxy.filterAfterNSamples = True
        else:
            self.countSortProxy.filterAfterNSamples = False
        self.countSortProxy.invalidate()

    @pyqtSlot(object, dict)
    def onSelectedNodeChanged(self, previous, current):
        if current is not None:
            if previous is not None:
                if "canlogger" not in previous:
                    previous["canlogger"] = {}
                previous["canlogger"]["model"] = self.model
            if "canlogger" not in current:
                current["canlogger"] = {}
                current["canlogger"]["model"] = CanLoggerTableModel(self.mainwindow.canLogTableView)
            self.model = current["canlogger"]["model"]
            self.countSortProxy = FrameCountSortModel(self.mainwindow)
            self.countSortProxy.setSourceModel(self.model)
            self.mainwindow.canLogTableView.setModel(self.countSortProxy)
            self.mainwindow.canLogTableView.setSortingEnabled(True)
            self.mainwindow.filterFramesByIdCheckbox.setCheckState(0)
            self.mainwindow.filterFramesByNewFramesAfterCheckbox.setCheckState(0)
            self.filterFrames()

    @pyqtSlot()
    def onSaveFramesToFile(self):
        filename = QFileDialog.getSaveFileName(self.mainwindow, 'Save CAN frames', '.', "")
        if len(filename) < 1:
            self.mainwindow.onUpdateDebugLog("Did not save CanLog! Invalid filename!")
            return

        outfile = open(filename, 'wb')
        # stringify all the frames
        frames = self.model.getFrames()
        stringy_frames = map(lambda x: [x[0], x[1], str(x[2])], frames)
        outfile.write(json.dumps(stringy_frames))
        outfile.flush()
        outfile.close()
        self.mainwindow.onUpdateDebugLog("Saved CAN frames to %s !" % filename)