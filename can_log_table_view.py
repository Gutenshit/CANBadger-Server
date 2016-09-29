from PyQt4.QtCore import *
from PyQt4.QtGui import *

class CanLogTableView(QTableView):
    sendToReplay = pyqtSignal(list)
    createRuleForId = pyqtSignal(list)
    createRuleForPayload = pyqtSignal(list)

    def __init__(self, parent):
        super(CanLogTableView, self).__init__(parent)
        self.verticalHeader().setVisible(False)

    def contextMenuEvent(self, event):
        # get current selection
        index = self.indexAt(event.pos())
        if index.row() >= 0 and index.column() >= 0:
            menu = QMenu()
            replayAction = menu.addAction("Send to Replay")
            replayAction.triggered.connect(self.onReplayActionTriggered)
            createRuleByIdAction = menu.addAction("Create Rule for ID")
            createRuleByIdAction.triggered.connect(self.onCreateRuleByIdActionTriggered)
            createRuleByPayloadAction = menu.addAction("Create Rule for Payload")
            createRuleByPayloadAction.triggered.connect(self.onCreateRuleByPayloadActionTriggered)

            action = menu.exec_(event.globalPos())

    @pyqtSlot()
    def onReplayActionTriggered(self):
#        frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().getFrame(self.currentIndex())
        self.sendToReplay.emit(frame)

    @pyqtSlot()
    def onCreateRuleByIdActionTriggered(self):
        #frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().getFrame(self.currentIndex())
        self.createRuleForId.emit(frame)

    @pyqtSlot()
    def onCreateRuleByPayloadActionTriggered(self):
        #frame = self.model().sourceModel().getFrame(self.currentIndex())
        frame = self.model().sourceModel().getFrame(self.currentIndex())
        self.createRuleForPayload.emit(frame)

