from PyQt4.QtCore import *
from PyQt4.QtGui import *
import json


class MITMTableModel(QAbstractTableModel):
    def __init__(self, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.rules = []
        self.header_labels = ['Rule Type', 'Rule Condition', 'Target ID', 'Cond Value',
                              'Cond Mask', 'Argument', 'Action Mask']

    def rowCount(self, parent):
        return len(self.rules)

    def columnCount(self, parent):
        return 7

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()
        return QVariant(self.rules[index.row()][index.column()])

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_labels[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def addRule(self, rule):
        self.rules.append(rule)
        self.layoutChanged.emit()

    def removeRule(self, index):
        self.beginRemoveRows(index, index.row(), 1)
        del self.rules[index.row()]
        self.endRemoveRows()
        self.layoutChanged.emit()

    def getRule(self, index):
        return self.rules[index.row()]

    def getRules(self):
        return self.rules

    def getRulesJson(self):
        # transform qstrings -> str
        cleaned_list = map(lambda rule: map(lambda x: str(x) if type(x) == QString else x, rule), self.rules)
        return json.dumps(cleaned_list)

    def setRulesJson(self, rules_json):
        rules = map(lambda rule: map(lambda x: QString(x) if type(x) == str else x, rule), json.loads(rules_json))
        self.rules = rules
        self.layoutChanged.emit()

    # expects a dict as update_values containing the new rule/ changed values
    def updateRule(self, index, update_values):
        rule = self.rules[index.row()]
        for k,v in update_values.iteritems():
            rule[self.header_labels.index(k)] = v
        self.layoutChanged.emit()

    def isEmpty(self):
        if len(self.rules) > 0: return False
        else: return True