from PyQt4.QtCore import *
from PyQt4.QtGui import *

from ethernet_message import *
from helpers import *

# TODO: scan valid ids
# TODO: read some info (vin etc.)
class UDSHandler(QObject):
    udsFunctions = [ 'SWITCH_SESSION', 'SCAN_FOR_AVAILABLE_SESSION_TYPES', # diag session ctrl
                     'READ_ALL_DATA', 'READ_VIN', 'READ_ECU_HW', 'READ_SUPPLIER_ECU_HW', 'READ_ECU_HW_VERSION', # read data by id
                     'READ_SUPPLIER_ECU_SW', 'READ_ECU_SW_VERSION', 'READ_CUSTOM_ID', 'READ_SCAN_FOR_SUPPORTED_IDS',
                     'SA_USE_KNOWN_ALGO', 'SA_MANUAL_AUTH', # sec access
                     'ECU_RESET_HARD', 'ECU_RESET_IGNITION_ONOFF_RESET', 'ECU_RESET_OFF', 'ECU_RESET_CUSTOM', # ecu reset
                     'READ_MEMORY_BY_ADR', 'WRITE_MEMORY_BY_ADR', 'FAST_SCAN_FOR_READABLE_OFFSETS' # memory menu
                     ]

    def __init__(self, mainwindow, nodehandler):
        super(UDSHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.printAscii = False

    def connect_signals(self):
        self.mainwindow.mainInitDone.connect(self.setup_gui)
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onEstablishNewSession)

    def writeUdsLogMsg(self, msg):
        self.mainwindow.udsLogPlainTextEdit.appendPlainText(QString(msg))

    @pyqtSlot()
    def setup_gui(self):
        self.mainwindow.udsActionsComboBox.addItem("Diag Session Control")
        self.mainwindow.udsActionsComboBox.addItem("Read Data by ID")  #  <- somewhat important
        self.mainwindow.udsActionsComboBox.addItem("Security Access")
        self.mainwindow.udsActionsComboBox.addItem("ECU Reset")
        self.mainwindow.udsActionsComboBox.addItem("Memory Operations")
        self.mainwindow.udsActionsComboBox.addItem("Terminate Session")
        self.mainwindow.udsActionsComboBox.addItem("UDS Channel Setup Scan")  # <- important
        self.mainwindow.udsActionsComboBox.currentIndexChanged.connect(self.onActionsComboBoxChange)

    @pyqtSlot(int)
    def onActionsComboBoxChange(self, index):
        # clear ui items first
        for i in reversed(range(self.mainwindow.udsActionContentsLayout.count())):
            self.mainwindow.udsActionContentsLayout.itemAt(i).widget().deleteLater()

        if index == 0:  # diag session control
            self.mainwindow.udsActionContentsLayout.addWidget(QLabel("Switch to Session:"))
            sessionTypesComboBox = QComboBox(self.mainwindow)
            sessionTypesComboBox.addItems(QStringList(["Default", "Programming", "Extended", "Custom"]))
            self.mainwindow.udsActionContentsLayout.addWidget(sessionTypesComboBox)
            self.scanForAvailableSessionsBtn = QPushButton("Scan for available Sessions")
            self.scanForAvailableSessionsBtn.clicked.connect(self.onScanForAvailableSessions)
            self.mainwindow.udsActionContentsLayout.addWidget(self.scanForAvailableSessionsBtn)
        elif index == 1:  # read data by id
            self.mainwindow.udsActionContentsLayout.addWidget(QLabel("Select what data to read:"))
            self.readDataType = QComboBox(self.mainwindow)
            self.readDataType.addItems(QStringList(["All Data", "VIN", "ECU HW", "Supplier ECU HW", "ECU HW Version", "Supplier ECU SW", "ECU SW Version", "Custom ID", "Scan for Supported IDs"]))
            self.readDataBtn = QPushButton("Read")
            self.readDataBtn.clicked.connect(self.onReadData)
            self.mainwindow.udsActionContentsLayout.addWidget(self.readDataType)
            self.mainwindow.udsActionContentsLayout.addWidget(self.readDataBtn)
        elif index == 4:  # memory operations
            self.mainwindow.udsActionContentsLayout.addWidget(QLabel("Select memory operation:"))
            self.memoryReadType = QComboBox(self.mainwindow)
            self.memoryReadType.addItems(QStringList(["Read Memory by Address", "Write Memory by Address", "Fast Scan for readable offsets"]))
            self.readMemoryBtn = QPushButton("Run")
            self.memoryAddressLineEdit = QLineEdit(self.mainwindow)
            self.memoryAddressLineEdit.setText("address to read/write - ignored for fast scan")
            self.readMemoryBtn.clicked.connect(self.onMemoryOperation)
            self.mainwindow.udsActionContentsLayout.addWidget(self.memoryReadType)
            self.mainwindow.udsActionContentsLayout.addWidget(self.memoryAddressLineEdit)
            self.mainwindow.udsActionContentsLayout.addWidget(self.readMemoryBtn)


    @pyqtSlot()
    def onEstablishNewSession(self):
        own_id = int(str(self.mainwindow.udsOwnIdLineEdit.text()), 16)
        target_id = int(str(self.mainwindow.udsTargetIdLineEdit.text()), 16)
        gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].ackReceived)
        gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].nackReceived)
        gracefullyDisconnectSignal(self.mainwindow.newUDSSessionBtn.clicked)

        self.mainwindow.selectedNode["connection"].ackReceived.connect(self.onSuccessfullyEstablishedSession)
        self.mainwindow.selectedNode["connection"].nackReceived.connect(self.onErrorEstablishingSession)
        self.mainwindow.newUDSSessionBtn.setText("Cancel")
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onCancelEstablishingSession)
        self.writeUdsLogMsg("Trying to establish new UDS session..")
        self.mainwindow.selectedNode["connection"].startUDS(own_id, target_id)

    @pyqtSlot()
    def onCancelEstablishingSession(self):
        self.mainwindow.selectedNode["connection"].stopCurrentAction()

    @pyqtSlot()
    def onSuccessfullyEstablishedSession(self):
        self.writeUdsLogMsg("Successfully established UDS session!")
        self.mainwindow.newUDSSessionBtn.clicked.disconnect()
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onCloseCurrentSession)
        self.mainwindow.newUDSSessionBtn.setText("Close Session")
        self.mainwindow.udsActionsComboBox.setEnabled(True)
        self.onActionsComboBoxChange(0)


    @pyqtSlot()
    def onErrorEstablishingSession(self):
        self.writeUdsLogMsg("Error establishing session!")
        self.mainwindow.newUDSSessionBtn.clicked.disconnect()
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onEstablishNewSession)
        self.mainwindow.newUDSSessionBtn.setText("New Session")
        self.mainwindow.udsActionsComboBox.setEnabled(False)

    @pyqtSlot(dict)
    def onTakeOverSession(self, session):
        pass

    @pyqtSlot()
    def onCloseCurrentSession(self):
        # do stuff ..
        self.mainwindow.newUDSSessionBtn.clicked.disconnect()
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onEstablishNewSession)
        self.mainwindow.newUDSSessionBtn.setText("New Session")
        self.mainwindow.udsActionsComboBox.setEnabled(False)

    @pyqtSlot()
    def onScanForAvailableSessions(self):
        gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].newDataMessage)

        self.printAscii = True
        self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
        self.mainwindow.selectedNode["connection"].callUDSFunction(0x02)

    @pyqtSlot()
    def onReadData(self):
        # get index
        index = self.readDataType.currentIndex()
        if index == 1: # read vin
            self.printAscii = False
            self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
            self.mainwindow.selectedNode["connection"].callUDSFunction(0x01)
        elif index == 8: # scan for supported ids
            self.printAscii = True
            self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
            self.mainwindow.selectedNode["connection"].callUDSFunction(0x03)

    @pyqtSlot()
    def onMemoryOperation(self):
        index = self.memoryReadType.currentIndex()
        if index == 0:  # read memory by address
            self.printAscii = False
            gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].newDataMessage)
            self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
            self.mainwindow.selectedNode["connection"].callUDSFunction(0x05) # TODO: add params
        elif index == 1:  # write memory by address
            self.mainwindow.onUpdateDebugLog("Write memory by address not yet implemented..")
            #self.printAscii = True
            #self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
            #self.mainwindow.selectedNode["connection"].callUDSFunction(0x06)
        elif index == 2:  # fast scan for offsets
            self.printAscii = True
            gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].newDataMessage)
            self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
            self.mainwindow.selectedNode["connection"].callUDSFunction(0x04)

    @pyqtSlot(str)
    def onReadDataReceived(self, msg):
        if self.printAscii:
            self.mainwindow.udsLogPlainTextEdit.appendPlainText(str(msg))
        else:
            self.mainwindow.udsLogPlainTextEdit.appendPlainText(str(QByteArray.fromRawData(msg).toHex()))