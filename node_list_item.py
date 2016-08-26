from PyQt4.QtCore import *
from PyQt4.QtGui import *

##
# will store the node dict internally and also display the text in the list widget
class NodeListItem(QListWidgetItem):
    def __init__(self, parent, node):
        # 1001 is nodeListItem type
        self.node = node
        self.display_text = "%s:%s:v%s" % (node["id"], node["ip"], node["version"])
        super(QListWidgetItem, self).__init__(self.display_text, parent, 1001)

    def getNode(self):
        return self.node
