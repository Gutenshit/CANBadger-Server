from PyQt4.QtCore import *
from PyQt4.QtGui import *

from ethernet_message import *
from helpers import *

class SdHandler(QObject):
    def __init__(self, mainwindow, nodehandler):
        super(SdHandler, self).__init__()
        self.mainwindow = mainwindow
        self.nodehandler = nodehandler
        self.listWidget = mainwindow.sdCardListWidget
        self.listItems = []
        self.currentItem = None
        self.downloadedData = QByteArray()
        self.stillDownloading = False

    def connect_signals(self):
        self.mainwindow.updateSdCardBtn.clicked.connect(self.onUpdateSd)
        self.mainwindow.downloadFileBtn.clicked.connect(self.onDownloadFile)
        self.mainwindow.deleteFileBtn.clicked.connect(self.onDeleteFile)
        self.mainwindow.sdCardListWidget.itemClicked.connect(self.onItemClicked)

    # START ACTIONS

    @pyqtSlot()
    def onUpdateSd(self):
        folder = str(self.mainwindow.sdCardFolderLineEdit.text())
        if len(folder) < 2:
            return

        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.newDataMessage)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.newDataMessage.connect(self.onGotUpdateResponse)
        connection.nackReceived.connect(self.onErrorListingDirectory)
        connection.sendMessage(EthernetMessage("ACTION", "UPDATE_SD", len(folder), folder))

    @pyqtSlot()
    def onDownloadFile(self):
        # file = folder from line edit + selected file name
        if self.currentItem is None:
            return

        path = str(self.mainwindow.sdCardFolderLineEdit.text()).replace('/sd', '/')
        if len(path) > 0 and path[-1] != '/':
            path += '/'
        path += self.currentItem.text()

        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.newDataMessage)
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.newDataMessage.connect(self.onNewDownloadData)
        connection.ackReceived.connect(self.onDownloadAck)
        connection.nackReceived.connect(self.onDownloadError)
        self.stillDownloading = True

        self.downloadedData = QByteArray()
        connection.sendMessage(EthernetMessage("ACTION", "DOWNLOAD_FILE", len(path), str(path)))
        self.mainwindow.onUpdateDebugLog("Downloading..")

    @pyqtSlot()
    def onDeleteFile(self):
        if self.currentItem is None:
            return

        path = str(self.mainwindow.sdCardFolderLineEdit.text()).replace('/sd', '/')
        if len(path) > 0 and path[0] != '/':
            path += '/'
        path += self.currentItem.text()

        connection = self.mainwindow.selectedNode["connection"]
        gracefullyDisconnectSignal(connection.ackReceived)
        gracefullyDisconnectSignal(connection.nackReceived)
        connection.ackReceived.connect(self.onDeleteAck)
        connection.nackReceived.connect(self.onDeleteError)

        connection.sendMessage(EthernetMessage("ACTION", "DELETE_FILE", len(path), str(path)))
        self.mainwindow.onUpdateDebugLog("Deleting file %s.." % path)

    # DATA RECEIVERS

    @pyqtSlot(object)
    def onGotUpdateResponse(self, data):
        # clear all elements
        self.listWidget.clear()
        # data is a str so cast it
        data_split = str(data[:-2]).split('|')
        if len(data_split) > 0:
            # do shit
            for i in data_split:
                self.listWidget.addItem(i)

    @pyqtSlot()
    def onErrorListingDirectory(self):
        self.mainwindow.onUpdateDebugLog("Error listing files! Invalid directory?")

    @pyqtSlot(QListWidgetItem)
    def onItemClicked(self, item):
        self.currentItem = item

    @pyqtSlot(object)
    def onNewDownloadData(self, data):
        if self.stillDownloading:
            self.downloadedData += data

    @pyqtSlot()
    def onDownloadAck(self):
        # download finishedFalse
        self.stillDownloading = False
        # display file chooser and save file
        self.mainwindow.onUpdateDebugLog("Download finished!")
        filename = QFileDialog.getSaveFileName(self.mainwindow, 'Save file', '.',"Any files")
        if len(filename) < 1:
            self.mainwindow.onUpdateDebugLog("Did not save downloaded file! Invalid filename!")
            return
        outfile = open(filename, 'wb')
        outfile.write(str(self.downloadedData))
        outfile.flush()
        outfile.close()

    @pyqtSlot()
    def onDownloadError(self):
        self.mainwindow.onUpdateDebugLog("Error downloading file! Invalid path? Check the folder line edit!")
        self.stillDownloading = False

    @pyqtSlot()
    def onDeleteAck(self):
        self.mainwindow.onUpdateDebugLog("Successfully deleted file!")

    @pyqtSlot()
    def onDeleteError(self):
        self.mainwindow.onUpdateDebugLog("Error deleting file! Invalid path? Check the folder!")