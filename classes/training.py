# import os, glob, joblib
# import numpy as np
# from tqdm import tqdm
# from PIL import Image

# import torch
# import torch.nn as nn
# from torch.utils.data import Dataset, DataLoader
# from torchvision import models, transforms


# # ================= DATASET =================
# class GoodImageFolder(Dataset):
#     def __init__(self, root, img_size=600):
#         self.paths = []
#         for ext in ("*.jpg", "*.png", "*.bmp"):
#             self.paths += glob.glob(os.path.join(root, ext))

#         if len(self.paths) == 0:
#             raise RuntimeError("No images found!")

#         self.img_size = img_size

#         self.tf = transforms.Compose([
#             transforms.Resize((img_size, img_size)),
#             transforms.ToTensor(),
#             transforms.Normalize(
#                 mean=[0.485, 0.456, 0.406],
#                 std =[0.229, 0.224, 0.225]
#             )
#         ])

#     def crop_roi(self, img):
#         """Crop your required region"""
#         w, h = img.size

#         x1 = int(w * 0.30)
#         x2 = int(w * 0.48)
#         y1 = 0
#         y2 = h

#         return img.crop((x1, y1, x2, y2))

#     def __len__(self):
#         return len(self.paths)

#     def __getitem__(self, idx):
#         img = Image.open(self.paths[idx]).convert("RGB")

#         # 🔥 APPLY CROP HERE
#         img = self.crop_roi(img)

#         # Transform
#         img = self.tf(img)

#         return img


# # ================= MODEL =================
# class EffB7_FeatureNet(nn.Module):
#     def __init__(self):
#         super().__init__()

#         model = models.efficientnet_b7(weights="IMAGENET1K_V1")
#         self.features = model.features
#         self.pool = nn.AdaptiveAvgPool2d((1,1))

#         for p in self.parameters():
#             p.requires_grad = False

#     def forward(self, x):
#         x = self.features(x)
#         x = self.pool(x)
#         return torch.flatten(x, 1)


# # ================= FEATURE EXTRACTION =================
# def extract_embeddings(loader, model, device):
#     feats = []

#     with torch.no_grad():
#         for imgs in tqdm(loader):
#             imgs = imgs.to(device)
#             emb = model(imgs).cpu().numpy()
#             feats.append(emb)

#     return np.vstack(feats)


# # ================= MAIN =================
# def main():

#     train_dir = r"D:\econ\royal_cut"   # 🔥 RAW IMAGES ONLY
#     output_file = "effb7_features_auto_crop.joblib"

#     device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

#     dataset = GoodImageFolder(train_dir)
#     loader = DataLoader(dataset, batch_size=4, shuffle=False)

#     model = EffB7_FeatureNet().to(device)
#     model.eval()

#     features = extract_embeddings(loader, model, device)

#     print("Feature shape:", features.shape)

#     joblib.dump(features, output_file)
#     print("✅ Saved:", output_file)


# if __name__ == "__main__":
#     main()



import os, glob, joblib
import numpy as np
from PIL import Image
from tqdm import tqdm

import torch
import torch.nn as nn
from torch.utils.data import Dataset
from torchvision import models, transforms



# ================= DATASET =================
class GoodImageFolder(Dataset):
    def __init__(self, root):
        self.paths = []

        for ext in ("*.jpg", "*.png", "*.bmp"):
            self.paths += glob.glob(os.path.join(root, ext))

        # 🔥 IMPORTANT
        self.paths = sorted(self.paths)

        if len(self.paths) == 0:
            raise RuntimeError("❌ No images found!")

        self.tf = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std =[0.229, 0.224, 0.225]
            )
        ])

    def process(self, img):
        # ===== CROP =====
        w, h = img.size
        x1 = int(w * 0.30)
        x2 = int(w * 0.48)
        img = img.crop((x1, 0, x2, h))

        # ===== ROTATE =====
        img = img.rotate(90, expand=True)

        # ===== RESIZE =====
        img = img.resize((800, 200))

        return img

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        try:
            img = Image.open(self.paths[idx]).convert("RGB")
        except:
            print("⚠️ Skipping bad image:", self.paths[idx])
            return self.__getitem__((idx + 1) % len(self.paths))

        img = self.process(img)
        img = self.tf(img)

        return img


# ================= MODEL =================
class EffB7_FeatureNet(nn.Module):   # ✅ NAME FIXED
    def __init__(self):
        super().__init__()

        model = models.efficientnet_b7(weights="IMAGENET1K_V1")

        self.features = model.features
        self.pool = nn.AdaptiveAvgPool2d((1,1))

        for p in self.parameters():
            p.requires_grad = False

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        return torch.flatten(x, 1)


# ================= FEATURE EXTRACTION =================
def extract_embeddings(loader, model, device):   # ✅ NAME FIXED
    all_features = []

    with torch.no_grad():
        for imgs in tqdm(loader):
            imgs = imgs.to(device)
            feats = model(imgs).cpu().numpy()
            all_features.append(feats)

    return np.vstack(all_features)