from PyQt4.QtCore import *

# thread that just executes the event loop
# attach functions to this thread using qobject.moveToThread(..)
class EventProcessingThread(QThread):
    def __init__(self):
        super(EventProcessingThread, self).__init__()

    def run(self):
        self.exec_()
