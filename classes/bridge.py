# classes/bridge.py
import cv2
import base64
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer


class Bridge(QObject):

    frame_signal = pyqtSignal(str)

    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref

        # Camera related
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.grab_frame)

    # ------------------- CAMERA -------------------
    @pyqtSlot(result=str)
    def startCamera(self):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("❌ Cannot open camera")
                return
            print("✅ Camera started")
            self.timer.start(30)   # ~33 fps

    @pyqtSlot()
    def stopCamera(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
        print("✅ Camera stopped")

    def grab_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # frame = cv2.flip(frame, 1)  # Uncomment for mirror effect
                self.on_new_frame(frame)

    def on_new_frame(self, frame):
        """Convert frame to base64 and send to JavaScript"""
        if frame is None:
            return
        try:
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            jpg_as_text = base64.b64encode(buffer).decode("utf-8")
            self.frame_signal.emit(jpg_as_text)
        except Exception as e:
            print(f"❌ Error encoding frame: {e}")

    # ------------------- NAVIGATION -------------------
    @pyqtSlot()
    def goHome(self):
        self.app_ref.load_page("index.html")

    @pyqtSlot()
    def goReport(self):
        self.app_ref.open_report_window()

    @pyqtSlot()
    def goTraining(self):
        self.app_ref.load_page("training.html")