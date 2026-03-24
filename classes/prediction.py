import cv2
import numpy as np
import joblib
from PIL import Image

import torch
import torch.nn as nn
from torchvision import models, transforms
from path import MODELS_DIR

# ================= MODEL =================
class EffB7_CAM(nn.Module):
    def __init__(self):
        super().__init__()

        model = models.efficientnet_b7(weights="IMAGENET1K_V1")

        self.features = model.features
        self.pool = nn.AdaptiveAvgPool2d((1,1))

    def forward(self, x):
        feat_map = self.features(x)        # 🔥 spatial features
        pooled = self.pool(feat_map)
        flat = torch.flatten(pooled, 1)

        return flat, feat_map


# ================= PREPROCESS =================
def process_image(img):
    w, h = img.size
    x1 = int(w * 0.30)
    x2 = int(w * 0.48)
    img = img.crop((x1, 0, x2, h))

    img = img.rotate(90, expand=True)
    img = img.resize((800, 200))

    return img


tf = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std =[0.229, 0.224, 0.225]
    )
])


# ================= LOAD =================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = EffB7_CAM().to(device)
model.eval()


# good_features = joblib.load("effb7_good_features.joblib")
# good_mean = np.mean(good_features, axis=0)
model_path = MODELS_DIR / "effb7_good_features.joblib"

if not model_path.exists():
    print("⚠️ Model not found, please run training first")
    good_features = None
else:
    good_features = joblib.load(str(model_path))



# ================= DEFECT HEATMAP =================
def detect_defect_final(image_path, dist_thresh=0.3, pixel_thresh=0.45):

    import cv2
    import numpy as np
    from PIL import Image

    # ===== LOAD =====
    img_pil = Image.open(image_path).convert("RGB")

    # ===== PROCESS =====
    w, h = img_pil.size
    x1 = int(w * 0.30)
    x2 = int(w * 0.48)
    img_pil = img_pil.crop((x1, 0, x2, h))

    img_pil = img_pil.rotate(90, expand=True)
    img_pil = img_pil.resize((800, 200))

    img_tensor = tf(img_pil).unsqueeze(0).to(device)

    # ===== MODEL =====
    with torch.no_grad():
        feat, fmap = model(img_tensor)

    feat = feat.cpu().numpy()[0]
    fmap = fmap.squeeze().cpu().numpy()

    # =========================================================
    # 🔥 STEP 1: GLOBAL CHECK (VERY IMPORTANT)
    # =========================================================
    distances = np.linalg.norm(good_features - feat, axis=1)
    min_dist = np.min(distances)

    print("Distance:", min_dist)

    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    if min_dist < dist_thresh:
        print("✅ GOOD")
        return img_cv

    print("❌ DEFECT → localizing...")

   
  # =========================================================
# 🔥 HYBRID HEATMAP (FINAL FIX)
# =========================================================

    # --- Feature heatmap ---
    feat_map = np.std(fmap, axis=0) + 1.5 * np.max(fmap, axis=0)
    feat_map = cv2.resize(feat_map, (800, 200))

    # --- Image gradient (detect scratches / edges) ---
    gray = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2GRAY)
    grad = cv2.Laplacian(gray, cv2.CV_64F)
    grad = np.abs(grad)
    grad = cv2.GaussianBlur(grad, (5,5), 0)

    # normalize both
    feat_map = (feat_map - feat_map.min()) / (feat_map.max() + 1e-8)
    grad = (grad - grad.min()) / (grad.max() + 1e-8)

    # 🔥 COMBINE (VERY IMPORTANT)
    heatmap = 0.6 * feat_map + 0.4 * grad

    # smooth
    heatmap = cv2.GaussianBlur(heatmap, (7,7), 0)

    # =========================================================
    # 🔥 STEP 3: REMOVE NON-DEFECT REGIONS (CRITICAL)
    # =========================================================
    h, w = heatmap.shape

    # remove top/bottom borders
    heatmap[0:30, :] = 0
    heatmap[h-30:h, :] = 0

    # remove left/right edges
    heatmap[:, 0:30] = 0
    heatmap[:, w-30:w] = 0

    # =========================================================
    # 🔥 STEP 4: THRESHOLD
    # =========================================================
    mask = heatmap > pixel_thresh
    mask = np.uint8(mask * 255)

    # =========================================================
    # 🔥 STEP 5: CLEAN NOISE
    # =========================================================
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # =========================================================
    # 🔥 STEP 6: FIND DEFECT AREA
    # =========================================================
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    found = False

    for cnt in contours:
        area = cv2.contourArea(cnt)

        if area < 20 or area > 3000:
            continue

        x, y, w_box, h_box = cv2.boundingRect(cnt)

        # 🔥 REMOVE LONG STRIPS (edge false detection)
        aspect_ratio = w_box / (h_box + 1e-5)
        if aspect_ratio > 5:
            continue

        # draw box
        cv2.rectangle(img_cv, (x, y), (x+w_box, y+h_box), (0, 0, 255), 2)
        found = True

    if not found:
        print("⚠️ Weak defect (not clearly localized)")

    return img_cv, found

# ================= TEST =================
# if __name__ == "__main__":

#     # test_img = r"D:\econ\royal_cut\frame_00011.bmp"

   

#     # result = detect_defect_fast(r"D:\econ\royal_cut\frame_00012.bmp", thresh=0.75)
#     result = detect_defect_final(
#     r"D:\econ\bad_images\frame_00029.bmp",
#     dist_thresh=0.3,
#     pixel_thresh=0.45
# )

#     cv2.imshow("Result", result)
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()