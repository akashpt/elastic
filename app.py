# app.py
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QUrl

from classes.bridge import Bridge
from path import TEMPLATES_DIR


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Elastic Design System")
        self.resize(1200, 800)

        # WebEngine View
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)

        # Bridge & WebChannel
        self.bridge = Bridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        # Load finished handler
        self.view.loadFinished.connect(self.on_load_finished)

        # Load initial page
        self.load_page("index.html")

    def load_page(self, page_name: str):
        print(f"Switching to page: {page_name}")

        file_path = (TEMPLATES_DIR / page_name).resolve()

        if file_path.exists():
            self.view.setUrl(QUrl("about:blank"))
            self.view.load(QUrl.fromLocalFile(str(file_path)))
        else:
            print(f"❌ Page not found: {file_path}")

    

    def closeEvent(self, event):
        self.bridge.stopCamera()  # Ask bridge to cleanup camera
        super().closeEvent(event)

    def on_load_finished(self):
        print("✅ Page loaded successfully")


# ------------------- MAIN -------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
