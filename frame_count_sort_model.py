from PyQt4.QtCore import *
from PyQt4.QtGui import *

class FrameCountSortModel(QSortFilterProxyModel):
    def __init__(self, mainwindow):
        super(FrameCountSortModel, self).__init__()
        self.filterById = False
        self.filterAfterNSamples = False
        self.filteringEnabled = False
        self.mainwindow = mainwindow

    def lessThan(self, left, right):
        lvalue = left.data().toInt()[0]
        rvalue = right.data().toInt()[0]
        if left.column() in [1,2]:
            lvalue = int(str(left.data().toString()), 16)
            rvalue = int(str(right.data().toString()), 16)

        return lvalue > rvalue

    def filterAcceptsRow(self, sourceRow, sourceParent):
        if not self.filteringEnabled:
            return True

        model = self.sourceModel()
        id = model.index(sourceRow, 1, sourceParent).data().toString()
        flag = True
        if self.filterAfterNSamples:
            numFrames = self.mainwindow.filterFramesAfterNSpinBox.value()
            ids_before = map(lambda x: x[1], model.can_data[:numFrames])
            if id not in ids_before:
                flag = True
            else:
                flag = False
        if self.filterById:
            filter_ids = self.mainwindow.filterFramesByIdLineEdit.text().split(",")
            if id in filter_ids:
                flag = True
            else:
                flag = False
        return flag