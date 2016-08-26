from PyQt4.QtCore import *
from PyQt4.QtGui import *

from ethernet_message import *
from helpers import *

class TPHandler(QObject):
    tpFunctions = [ 'SWITCH_TO_SESSION', 'SCAN_FOR_AVAILABLE_SESSION_TYPES', # diag session ctrl,
                    'READ_ALL_DATA', 'READ_VIN', 'READ_ECU_HW', 'READ_SUPPLIER_ECU_HW', 'READ_ECU_HW_VERSION', # read data by id
                    'READ_SUPPLIER_ECU_SW', 'READ_ECU_SW_VERSION', 'READ_CUSTOM_ID', 'READ_SCAN_FOR_SUPPORTED_IDS',
                    'SA_USE_KNOWN_ALGO', 'SA_MANUAL_AUTH', # sec access
                    'ECU_RESET_HARD', 'ECU_RESET_IGNITION_ONOFF_RESET', 'ECU_RESET_OFF', 'ECU_RESET_CUSTOM', # ecu reset
                    'READ_MEMORY_BY_ADR', 'WRITE_MEMORY_BY_ADR', 'FAST_SCAN_FOR_READABLE_OFFSETS' # memory menu
    ]

    def __init__(self, mainwindow, nodehandler):
        super(TPHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler

    def connect_signals(self):
        self.mainwindow.mainInitDone.connect(self.setup_gui)
        self.mainwindow.newTPSessionBtn.clicked.connect(self.onEstablishNewSession)

    def writeTPLogMsg(self, msg):
        self.mainwindow.tpLogPlainTextEdit.appendPlainText(QString(msg))

    @pyqtSlot()
    def setup_gui(self):
        self.mainwindow.udsActionsComboBox.addItem("Diag Session Control")
        self.mainwindow.udsActionsComboBox.addItem("Read Data by ID")  # <- somewhat important
        self.mainwindow.udsActionsComboBox.addItem("Security Access")
        self.mainwindow.udsActionsComboBox.addItem("ECU Reset")
        self.mainwindow.udsActionsComboBox.addItem("Memory Operations")
        self.mainwindow.udsActionsComboBox.addItem("Terminate Session")
        self.mainwindow.udsActionsComboBox.addItem("TP Channel Setup Scan")  # <- important
        self.mainwindow.udsActionsComboBox.currentIndexChanged.connect(self.onActionsComboBoxChange)

    @pyqtSlot(int)
    def onActionsComboBoxChange(self, index):
        if index == 0: # session ctrl
            self.mainwindow.udsActionContentsLayout.addWidget(QLabel("Switch to Session:"))
            sessionTypesComboBox = QComboBox(self.mainwindow)
            sessionTypesComboBox.addItems(QStringList(["Default", "Programming", "Extended", "Custom"]))
            self.mainwindow.udsActionContentsLayout.addWidget(sessionTypesComboBox)
            self.scanForAvailableSessionsBtn = QPushButton("Scan for available Sessions")
            self.scanForAvailableSessionsBtn.clicked.connect(self.onScanForAvailableSessions)
            self.mainwindow.udsActionContentsLayout.addWidget(self.scanForAvailableSessionsBtn)
        elif index == 1: # read data by id
            self.mainwindow.udsActionContentsLayout.addWidget(QLabel("Select what data to read:"))
            self.readDataType = QComboBox(self.mainwindow)
            self.readDataType.addItems(QStringList(
                ["All Data", "VIN", "ECU HW", "Supplier ECU HW", "ECU HW Version", "Supplier ECU SW", "ECU SW Version",
                 "Custom ID", "Scan for Supported IDs"]))
            self.readDataBtn = QPushButton("Read")
            self.readDataBtn.clicked.connect(self.onReadData)
            self.mainwindow.tpActionContentsLayout.addWidget(self.readDataType)
            self.mainwindow.tpActionContentsLayout.addWidget(self.readDataBtn)

    @pyqtSlot()
    def onEstablishNewSession(self):
        module_id = int(str(self.mainwindow.tpModuleIdLineEdit.text()), 16)
        channel_negot_id = int(str(self.mainwindow.tpChannelNegotIdLineEdit.text()), 16)
        gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].ackReceived)
        gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].nackReceived)
        gracefullyDisconnectSignal(self.mainwindow.newUDSSessionBtn.clicked)

        self.mainwindow.selectedNode["connection"].ackReceived.connect(self.onSuccessfullyEstablishedSession)
        self.mainwindow.selectedNode["connection"].nackReceived.connect(self.onErrorEstablishingSession)
        self.mainwindow.newUDSSessionBtn.setText("Cancel")
        self.mainwindow.newUDSSessionBtn.clicked.connect(self.onCancelEstablishingSession)
        self.writeUdsLogMsg("Trying to establish new UDS session..")
        self.mainwindow.selectedNode["connection"].startTP(module_id, channel_negot_id)

    @pyqtSlot()
    def onScanForAvailableSessions(self):
        gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].newDataMessage)
        self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
        self.printAscii = True
        self.mainwindow.selectedNode["connection"].callUDSFunction(0x02)

    @pyqtSlot()
    def onReadData(self):
        index = self.readDataType.currentIndex()
        if index == 1:  # read vin
            self.printAscii = False
            gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].newDataMessage)
            self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
            self.mainwindow.selectedNode["connection"].callTPFunction(0x01)
        elif index == 8:  # scan for supported ids
            self.printAscii = True
            gracefullyDisconnectSignal(self.mainwindow.selectedNode["connection"].newDataMessage)
            self.mainwindow.selectedNode["connection"].newDataMessage.connect(self.onReadDataReceived)
            self.mainwindow.selectedNode["connection"].callUDSFunction(0x03)

    @pyqtSlot()
    def onSuccessfullyEstablishedSession(self):
        self.writeTPLogMsg("Successfully established UDS session!")
        gracefullyDisconnectSignal(self.mainwindow.newTPSessionBtn.clicked)
        self.mainwindow.newTPSessionBtn.clicked.disconnect()
        self.mainwindow.newTPSessionBtn.clicked.connect(self.onCloseCurrentSession)
        self.mainwindow.newTPSessionBtn.setText("Close Session")
        self.mainwindow.tpActionsComboBox.setEnabled(True)
        self.onActionsComboBoxChange(0)

    @pyqtSlot()
    def onErrorEstablishingSession(self):
        self.writeTPLogMsg("Error establishing session!")
        gracefullyDisconnectSignal(self.mainwindow.newTPSessionBtn.clicked)
        self.mainwindow.newTPSessionBtn.clicked.connect(self.onEstablishNewSession)
        self.mainwindow.newTPSessionBtn.setText("New Session")
        self.mainwindow.tpActionsComboBox.setEnabled(False)

    @pyqtSlot()
    def onCancelEstablishingSession(self):
        gracefullyDisconnectSignal(self.mainwindow.newTPSessionBtn.clicked)
        self.mainwindow.newTPSessionBtn.clicked.connect(self.onEstablishNewSession)
        self.mainwindow.newTPSessionBtn.setText("New Session")
        self.mainwindow.tpActionsComboBox.setEnabled(False)