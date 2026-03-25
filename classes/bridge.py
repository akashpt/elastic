import cv2
import base64
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer
import threading
from path import TRAINING_IMAGES_DIR ,PREDICTION_IMAGES_DIR
import time
import os
import joblib
import numpy as np

from path import MODELS_DIR
from classes.training import GoodImageFolder, EffB7_FeatureNet, extract_embeddings
from classes.prediction import detect_defect_final


class Bridge(QObject):

    frame_signal = pyqtSignal(str)
    defect_signal = pyqtSignal(str)

    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref

        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.grab_frame)

        self.last_frame = None  # ✅ store last frame

        self.training_running = False
        self.capture_interval = 0.2   # 5 FPS
        self.last_capture_time = 0
        self.training_count = 0
        self.detection_running = False   # 🔥 NEW
    # ------------------- CAMERA -------------------
    @pyqtSlot()
    def startCamera(self):

        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

            if not self.cap.isOpened():
                print("❌ Cannot open camera")
                return

        print("✅ Camera started")
        self.timer.start(30)

    # @pyqtSlot()
    # def stopCamera(self):
    #     if self.timer.isActive():
    #         self.timer.stop()

    #     if self.cap and self.cap.isOpened():
    #         self.cap.release()
    #         self.cap = None

    #     print("✅ Camera stopped")

    @pyqtSlot()
    def stopCamera(self):

        if self.timer.isActive():
            self.timer.stop()

        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

        # 🔥 CLEAR FRAME
        self.frame_signal.emit("")

        print("✅ Camera stopped")

    def grab_frame(self):

        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()

        if not ret or frame is None:
            return

        # ============================================
        # 🔥 DETECTION MODE
        # ============================================
        if self.detection_running:

            try:
                # 🔥 SAVE FRAME
                save_path = PREDICTION_IMAGES_DIR / "current_frame.bmp"
                cv2.imwrite(str(save_path), frame)

                # 🔥 RUN PREDICTION
                result_img, is_defect = detect_defect_final(
                    str(save_path),
                    dist_thresh=0.3,
                    pixel_thresh=0.45
                )

                frame = result_img

                # 🔥 SAVE DEFECT IMAGE
                if is_defect:
                    defect_path = PREDICTION_IMAGES_DIR / f"defect_{int(time.time()*1000)}.bmp"
                    cv2.imwrite(str(defect_path), frame)

                    print("❌ Defect saved:", defect_path)

                    # 🔥 SEND TO UI
                    try:
                        success, buffer = cv2.imencode(".jpg", frame)
                        jpg = base64.b64encode(buffer).decode("utf-8")
                        # self.defect_signal.emit(jpg)
                        self.defect_signal.emit(str(defect_path))
                    except Exception as e:
                        print("UI send error:", e)

            except Exception as e:
                print("Prediction error:", e)

        # ============================================
        # 🔥 SEND FRAME TO UI (MAIN FEED)
        # ============================================
        try:
            success, buffer = cv2.imencode(".jpg", frame)
            jpg = base64.b64encode(buffer).decode("utf-8")
            self.frame_signal.emit(jpg)
        except Exception as e:
            print("Frame send error:", e)

        # ============================================
        # 🔥 TRAINING CAPTURE
        # ============================================
        if self.training_running:
            current_time = time.time()

            if (current_time - self.last_capture_time) >= self.capture_interval:

                save_dir = str(TRAINING_IMAGES_DIR)
                os.makedirs(save_dir, exist_ok=True)

                filename = os.path.join(
                    save_dir, f"frame_{self.training_count:05d}.bmp"
                )

                cv2.imwrite(filename, frame)

                self.training_count += 1
                self.last_capture_time = current_time

                print(f"Saved: {filename}")

        # ------------------- NAVIGATION -------------------
    @pyqtSlot()
    def goHome(self):
        self.app_ref.load_page("index.html")

    @pyqtSlot()
    def goTraining(self):
        self.app_ref.load_page("training.html")



    
    @pyqtSlot()
    def startTraining(self):
        print("🚀 Training Started")

        self.training_running = True
        self.training_count = 0

        # start camera if not running
        self.startCamera()

    @pyqtSlot()
    def stopTraining(self):
        print("🛑 Training Stopped")

        self.training_running = False

        # 🔥 STOP CAMERA (IMPORTANT FIX)
        self.stopCamera()

        # run training AFTER stop
        thread = threading.Thread(target=self.run_training_model_wrapper)
        thread.start()


    @pyqtSlot()
    def startDetection(self):
        print("🚀 Detection Started")

        self.detection_running = True
        self.startCamera()


    @pyqtSlot()
    def stopDetection(self):
        print("🛑 Detection Stopped")

        self.detection_running = False
        self.stopCamera()



    @pyqtSlot(str)
    def openImageViewer(self, image_path):
        try:
            import os

            # 🔥 HANDLE Path object also
            image_path = str(image_path)

            # 🔥 CHECK FILE
            if not os.path.exists(image_path):
                print("❌ File not found:", image_path)
                return

            # 🔥 IMPORT VIEWER
            from classes.zoom import ImageViewerDialog

            # 🔥 PASS PARENT (IMPORTANT)
            dlg = ImageViewerDialog(image_path, parent=None)

            dlg.exec_()

        except Exception as e:
            print("❌ Viewer error:", e)


    def capture_training_images(self):
        save_dir = str(TRAINING_IMAGES_DIR)
        os.makedirs(save_dir, exist_ok=True)

        FPS = 10
        frame_interval = 2 / FPS

        frame_count = 0
        last_time = time.time()

        print("📸 Capturing training images...")

        while self.training_running:
            ret, frame = self.training_cap.read()

            if not ret:
                continue

            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

            current_time = time.time()
            if (current_time - last_time) >= frame_interval:
                filename = os.path.join(save_dir, f"frame_{frame_count:05d}.bmp")
                cv2.imwrite(filename, frame)

                frame_count += 1
                last_time = current_time

                print(f"Saved: {filename}")

    def run_training_model_wrapper(self):
        print("🧠 Training started...")

        save_dir = str(TRAINING_IMAGES_DIR)
        self.run_training_model(save_dir)

   

    def run_training_model(self, train_dir):
        import torch
        from torch.utils.data import DataLoader

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        dataset = GoodImageFolder(train_dir)
        loader = DataLoader(dataset, batch_size=4, shuffle=False)

        model = EffB7_FeatureNet().to(device)
        model.eval()

        features = extract_embeddings(loader, model, device)

        # 🔥 SAVE HERE (IMPORTANT FIX)
        model_path = MODELS_DIR / "effb7_good_features.joblib"

        joblib.dump(features, str(model_path))

        print("✅ Training completed")
        print("Saved:", model_path)

