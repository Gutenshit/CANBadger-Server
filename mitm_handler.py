from PyQt4.QtCore import *
from PyQt4.QtGui import *
from bitstring import *
from copy import *

from ethernet_message import *
from mitm_table_model import *
from helpers import *

class MITMHandler(QObject):

    rule_types = ["Swap Payload", "Swap Specific Bytes", "Add fixed Value to specific bytes",
                  "Substract fixed Value from specific bytes", "Multiply specific bytes", "Divide specific bytes",
                  "Increase specific bytes by fixed percentage", "Decrease specific bytes by fixed percentage",
                  "Drop Frame"]
    cond_types = ["Entire payload matches", "Specific bytes match",
                  "Specific bytes are greater", "Specific bytes are less"]

    def __init__(self, mainwindow, nodehandler):
        super(MITMHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.rulesEnabled = False
        self.model = MITMTableModel()
        self.currentRowModelIndex = None
        self.max2ndCondChars = 8
        self.rules_to_send = []

    def connect_signals(self):
        self.mainwindow.mainInitDone.connect(self.setup_ui)
        self.mainwindow.ruleTypeComboBox.currentIndexChanged.connect(self.onRuleTypeChanged)
        self.mainwindow.ruleCondComboBox.currentIndexChanged.connect(self.onCondChanged)
        self.mainwindow.addRuleBtn.clicked.connect(self.onAddRule)
        self.mainwindow.removeRuleBtn.clicked.connect(self.onRemoveRule)
        self.mainwindow.saveRulesBtn.clicked.connect(self.onSaveRules)
        self.mainwindow.startMitmModeBtn.clicked.connect(self.onStartMitm)
        self.mainwindow.conditionMessageIdLineEdit.textEdited.connect(self.onConditionMessageIdTextChanged)
        self.mainwindow.conditionValueLineEdit.textEdited.connect(self.onConditionValueTextChanged)
        self.mainwindow.conditionMaskLineEdit.textEdited.connect(self.onConditionMaskTextChanged)
        self.mainwindow.actionArgumentLineEdit.textEdited.connect(self.onActionArgumentTextChanged)
        self.mainwindow.actionMaskLineEdit.textEdited.connect(self.onActionMaskTextChanged)
        self.mainwindow.tabWidget_2.tabBar().currentChanged.connect(self.onTabChanged)
        self.mainwindow.selectedNodeChanged.connect(self.onSelectedNodeChanged)
        self.mainwindow.loadRulesFromFileBtn.clicked.connect(self.onLoadRules)
        self.mainwindow.saveRulesToFileBtn.clicked.connect(self.onSaveRulesToFile)

    @pyqtSlot()
    def setup_ui(self):
        self.mainwindow.rulesTableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.mainwindow.rulesTableView.setModel(self.model)
        self.selectionModel = self.mainwindow.rulesTableView.selectionModel()
        self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)
        # actions
        for rule_type in MITMHandler.rule_types:
            self.mainwindow.ruleTypeComboBox.addItem(rule_type)
        # conditions
        for cond_type in MITMHandler.cond_types:
            self.mainwindow.ruleCondComboBox.addItem(cond_type)

    @pyqtSlot(QModelIndex, QModelIndex)
    def onCurrentRowChanged(self, current, prev):
        if not current is None:
            self.currentRowModelIndex = current
            self.setRuleEditingEnabled(True)
            rule = self.model.getRule(self.currentRowModelIndex)
            self.mainwindow.ruleTypeComboBox.setCurrentIndex(MITMHandler.rule_types.index(rule[0]))
            self.mainwindow.ruleCondComboBox.setCurrentIndex(MITMHandler.cond_types.index(rule[1]))
            self.mainwindow.conditionMessageIdLineEdit.setText(rule[2])
            if type(rule[3]) == QByteArray:
                self.mainwindow.conditionValueLineEdit.setText(str(rule[3]))
            else:
                self.mainwindow.conditionValueLineEdit.setText(rule[3])
            self.mainwindow.conditionMaskLineEdit.setText(rule[4])
            self.mainwindow.actionArgumentLineEdit.setText(rule[5])
            self.mainwindow.actionMaskLineEdit.setText(rule[6])
        else:
            self.setRuleEditingEnabled(False)


    @pyqtSlot(int)
    def onRuleTypeChanged(self, index):
        if self.currentRowModelIndex is not None:
            self.model.updateRule(self.currentRowModelIndex, {'Rule Type': MITMHandler.rule_types[index]})

    @pyqtSlot(int)
    def onCondChanged(self, index):
        if self.currentRowModelIndex is not None:
            self.model.updateRule(self.currentRowModelIndex, {'Rule Condition': MITMHandler.cond_types[index]})

    @pyqtSlot(QString)
    def onConditionMessageIdTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex, {'Target ID': newText})

    @pyqtSlot(QString)
    def onConditionValueTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex,
                              {'Cond Value': newText})

    @pyqtSlot(QString)
    def onConditionMaskTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex,
                              {'Cond Mask': newText})

    @pyqtSlot(QString)
    def onActionArgumentTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex, {'Argument': newText})

    @pyqtSlot(QString)
    def onActionMaskTextChanged(self, newText):
        self.model.updateRule(self.currentRowModelIndex, {'Action Mask': newText})

    @pyqtSlot()
    def onAddRule(self):
        if self.mainwindow.selectedNode is None:
            return

        self.model.addRule(["Swap Payload", "Specific bytes match", QString(""), QString(""),
                            QString("00000000"), QString(""), QString("00000000")])
        self.currentRowModelIndex = self.selectionModel.currentIndex()
        if self.selectionModel.hasSelection():
            self.setRuleEditingEnabled(True)
        else:
            self.setRuleEditingEnabled(False)
        self.mainwindow.conditionMaskLineEdit.setInputMask('B'*8)
        self.mainwindow.actionMaskLineEdit.setInputMask('B'*8)
        self.onCurrentRowChanged(self.currentRowModelIndex, QModelIndex())

    @pyqtSlot()
    def onRemoveRule(self):
        self.model.removeRule(self.currentRowModelIndex)
        self.currentRowModelIndex = None
        if self.selectionModel.hasSelection():
            self.currentRowModelIndex = self.selectionModel.currentIndex()
            self.setRuleEditingEnabled(True)
        else:
            self.setRuleEditingEnabled(False)

        if self.model.isEmpty():
            self.setRuleEditingEnabled(False)

    @pyqtSlot()
    def onSaveRules(self):
        node = self.mainwindow.selectedNode
        connection = node['connection']
        # first, clear stuff
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.onSendRules)
        connection.nackReceived.connect(self.onErrorClearingRules)
        connection.sendMessage(EthernetMessage('ACTION', 'CLEAR_RULES', 0, ''))

    @pyqtSlot()
    def onErrorClearingRules(self):
        self.mainwindow.onUpdateDebugLog("Error clearing rules!")

    @pyqtSlot()
    def onSendRules(self):
        # pyqt overrides hex() so we want the python one
        from __builtin__ import hex
        node = self.mainwindow.selectedNode
        connection = node['connection']
        rules = self.model.getRules()
        formatted_rules = []
        for rule in rules:
            # crazily format the rule string
            rule_str = str()
            condition_type = str(self.cond_types.index(rule[1]))
            condition_mask = BitArray(8)
            condition_mask.set(True, [i for i, ltr in enumerate(str(rule[4])) if ltr == '1'])
            condition_mask.reverse()
            rule_str += str(condition_mask)[2:] + '0' + str(condition_type) + ','
            #rule_str += str(condition_mask)[2:] + str(condition_type) + ','
            rule_str += str(rule[2]) + ','
            cond_pl_string = ''
            for i in range(0, 16, 2):
                if i+1 > len(rule[3]):
                    cond_pl_string += '00,'  # pad with 0s
                else:
                    cond_pl_string += str(rule[3][i]) + str(rule[3][i+1]) + ','
            rule_str += cond_pl_string
            action_mask = BitArray(8)
            action_mask.set(True, [i for i, ltr in enumerate(str(rule[6])) if ltr == '1'])
            action_mask.reverse()
            rule_str += str(action_mask)[2:] + '0' + str(self.rule_types.index(rule[0])) + ','
            action_pl_string = ''
            for i in range(0, 16, 2):
                if i+1 > len(rule[5]):
                    action_pl_string += '00,'  # pad with 0s
                else:
                    action_pl_string += str(rule[5][i]) + str(rule[5][i+1]) + ','
            rule_str += action_pl_string[:-1]
            formatted_rules.append(rule_str)
        if len(formatted_rules) > 0:
            self.rules_to_send = formatted_rules
            gracefullyDisconnectSignal(connection.ackReceived)
            gracefullyDisconnectSignal(connection.nackReceived)
            connection.ackReceived.connect(self.onSendNextRule)
            connection.nackReceived.connect(self.onErrorSendingRules)
            self.mainwindow.onUpdateDebugLog("Starting to send rules..")
            self.onSendNextRule()

    @pyqtSlot()
    def onErrorSendingRules(self):
        self.mainwindow.onUpdateDebugLog("Error sending rule!")

    @pyqtSlot()
    def onSendNextRule(self):
        node = self.mainwindow.selectedNode
        connection = node['connection']
        if len(self.rules_to_send) > 0:
            rule_str = self.rules_to_send[0]
            connection.sendMessage(EthernetMessage("ACTION", "ADD_RULE", len(rule_str), rule_str))
            del self.rules_to_send[0]
        else:
            self.mainwindow.onUpdateDebugLog("Successfully sent rules!")

    @pyqtSlot()
    def onStartMitm(self):
        # if ack: self.rulesEnabled = True
        self.mainwindow.startMitmModeBtn.setText("Stop")
        gracefullyDisconnectSignal(self.mainwindow.startMitmModeBtn.clicked)
        self.mainwindow.startMitmModeBtn.clicked.connect(self.onStopMitm)
        node = self.mainwindow.selectedNode
        connection = node['connection']
        connection.sendMessage(EthernetMessage("ACTION", "ENABLE_MITM_MODE", 0, ''))

    @pyqtSlot()
    def onStopMitm(self):
        node = self.mainwindow.selectedNode
        connection = node['connection']
        connection.sendMessage(EthernetMessage("ACTION", "STOP_CURRENT_ACTION", 0, ''))
        self.mainwindow.startMitmModeBtn.setText("Start MITM")
        gracefullyDisconnectSignal(self.mainwindow.startMitmModeBtn.clicked)
        self.mainwindow.startMitmModeBtn.clicked.connect(self.onStartMitm)

    def setRuleEditingEnabled(self, value):
        self.mainwindow.removeRuleBtn.setEnabled(value)
        self.mainwindow.ruleTypeComboBox.setEnabled(value)
        self.mainwindow.ruleCondComboBox.setEnabled(value)
        self.mainwindow.conditionValueLineEdit.setEnabled(value)
        self.mainwindow.conditionMaskLineEdit.setEnabled(value)
        self.mainwindow.conditionMessageIdLineEdit.setEnabled(value)
        self.mainwindow.actionArgumentLineEdit.setEnabled(value)
        self.mainwindow.actionMaskLineEdit.setEnabled(value)

    ##
    # these two methods are used to pass frames between modules

    @pyqtSlot(list)
    def onCreateRuleForId(self, frame):
        if self.mainwindow.selectedNode is None:
            return
        self.onAddRule()
        self.currentRowModelIndex = self.selectionModel.currentIndex()
        self.model.updateRule(self.currentRowModelIndex, {'Rule Condition': MITMHandler.cond_types[1]})
        self.model.updateRule(self.currentRowModelIndex, {'Target ID': deepcopy(frame[1])})
        self.onCurrentRowChanged(self.currentRowModelIndex, 0)
        self.mainwindow.tabWidget_2.tabBar().setTabTextColor(5, Qt.yellow)

    @pyqtSlot(list)
    def onCreateRuleForPayload(self, frame):
        if self.mainwindow.selectedNode is None:
            return
        self.onAddRule()
        self.currentRowModelIndex = self.selectionModel.currentIndex()
        self.model.updateRule(self.currentRowModelIndex, {'Cond Value': deepcopy(frame[2])})
        self.model.updateRule(self.currentRowModelIndex, {'Cond Mask': "11111111"})
        self.onCurrentRowChanged(self.currentRowModelIndex, 0)
        self.mainwindow.tabWidget_2.tabBar().setTabTextColor(5, Qt.yellow)

    @pyqtSlot(int)
    def onTabChanged(self, index):
        if index == 5:
            self.mainwindow.tabWidget_2.tabBar().setTabTextColor(5, Qt.black)

    @pyqtSlot(object, dict)
    def onSelectedNodeChanged(self, previous, current):
        if current is not None:
            if previous is not None:
                if "mitm" not in previous:
                    previous["mitm"] = {}
                previous["mitm"]["model"] = self.model
            if "mitm" not in current:
                current["mitm"] = {}
                current["mitm"]["model"] = MITMTableModel()
            self.model = current["mitm"]["model"]
            self.mainwindow.rulesTableView.setModel(self.model)
            self.selectionModel = self.mainwindow.rulesTableView.selectionModel()
            gracefullyDisconnectSignal(self.selectionModel.currentRowChanged)
            self.selectionModel.currentRowChanged.connect(self.onCurrentRowChanged)

        self.setRuleEditingEnabled(False)

    @pyqtSlot()
    def onLoadRules(self):
        filename = QFileDialog.getOpenFileName(self.mainwindow, 'Open rules file', '.', "")
        if len(filename) < 1:
            return

        infile = open(filename, 'r')
        rules_str = infile.read()
        if len(rules_str) < 1:
            self.mainwindow.onUpdateDebugLog("Error loading rules! File is empty!")
            return
        infile.close()
        self.model.setRulesJson(rules_str)

    @pyqtSlot()
    def onSaveRulesToFile(self):
        filename = QFileDialog.getSaveFileName(self.mainwindow, 'Save rules file', '.', "")
        if len(filename) < 1:
            self.mainwindow.onUpdateDebugLog("Did not save rules! Invalid filename!")
            return

        outfile = open(filename, 'wb')
        outfile.write(self.model.getRulesJson())
        outfile.flush()
        outfile.close()
