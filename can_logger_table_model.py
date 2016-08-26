from PyQt4.QtCore import *
from PyQt4.QtGui import *


class CanLoggerTableModel(QAbstractTableModel):
    def __init__(self, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.can_data = []
        self.header_labels = ['Frame Count', 'ID', 'Payload']
        self.setSupportedDragActions(Qt.MoveAction)

    def rowCount(self, parent = QModelIndex()):
        return len(self.can_data)

    def columnCount(self, parent):
        return 3

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()
        return QVariant(self.can_data[index.row()][index.column()])

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def addFrame(self, frame):
        self.can_data.append(frame)
        self.layoutChanged.emit()

    def getFrame(self, index):
        return self.can_data[index.row()]

    def getFrames(self):
        return self.can_data

    def setFrames(self, frames):
        self.can_data = frames
        self.layoutChanged.emit()

    def removeFrame(self, index):
        self.beginRemoveRows(index, index.row(), 1)
        del self.can_data[index.row()]
        self.endRemoveRows()
        self.layoutChanged.emit()

    def updateFrame(self, index, update_values):
        frame = self.can_data[index.row()]
        for k, v in update_values.iteritems():
            frame[self.header_labels.index(k)] = v
        self.layoutChanged.emit()

    def moveUpFrame(self, index):
        if index.row() == 0 or index.row() > len(self.can_data)-1:
            return False

        frame = self.can_data[index.row()]
        self.can_data[index.row()] = self.can_data[index.row() - 1]
        self.can_data[index.row() - 1] = frame
        self.layoutChanged.emit()
        return True


    def moveDownFrame(self, index):
        if index.row() == (len(self.can_data) - 1):
            return False

        frame = self.can_data[index.row()]
        self.can_data[index.row()] = self.can_data[index.row() + 1]
        self.can_data[index.row() + 1] = frame
        self.layoutChanged.emit()
        return True
