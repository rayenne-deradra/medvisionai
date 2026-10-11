"""MedVisionAI first baseline: tumor vs other tissue on PathMNIST, ResNet18.
Run: python train.py            (add --seed 1 for another run)
Research prototype only. Not for clinical use."""
import argparse, json, random
import numpy as np
import torch, torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
from medmnist import PathMNIST, INFO

p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, default=0)
p.add_argument("--size", type=int, default=64)      # try 128 later
p.add_argument("--epochs", type=int, default=3)
p.add_argument("--batch", type=int, default=128)
a = p.parse_args()

random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
dev = "cuda" if torch.cuda.is_available() else "cpu"
print("Using:", dev)

# Find the tumor class number from the official label names (do not guess)
labels = INFO["pathmnist"]["label"]
print("Classes:", labels)
TUM = [int(k) for k, v in labels.items() if "adenocarcinoma" in v.lower()][0]
print("Tumor class number:", TUM, "=", labels[str(TUM)])

norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
train_tf = transforms.Compose([transforms.RandomHorizontalFlip(),
                               transforms.RandomVerticalFlip(),
                               transforms.ToTensor(), norm])
eval_tf = transforms.Compose([transforms.ToTensor(), norm])

class Binary(Dataset):
    """Turns the 9 tissue labels into 1 = tumor, 0 = other tissue."""
    def __init__(self, split, tf):
        self.base = PathMNIST(split=split, download=True, size=a.size, transform=tf)
        self.y = (self.base.labels[:, 0] == TUM).astype(int)
    def __len__(self): return len(self.base)
    def __getitem__(self, i): return self.base[i][0], int(self.y[i])

train, val, test = (Binary("train", train_tf), Binary("val", eval_tf), Binary("test", eval_tf))
print("Sizes:", len(train), len(val), len(test), "| tumor share in train:", train.y.mean().round(3))

mk = lambda d, sh: DataLoader(d, batch_size=a.batch, shuffle=sh, num_workers=2)
tl, vl, sl = mk(train, True), mk(val, False), mk(test, False)

model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
model.fc = nn.Linear(model.fc.in_features, 2)
model.to(dev)

# Tumor is the rarer class, so give it more weight
w = torch.tensor([1.0, (1 - train.y.mean()) / train.y.mean()], dtype=torch.float32).to(dev)
loss_fn = nn.CrossEntropyLoss(weight=w)
opt = torch.optim.AdamW(model.parameters(), lr=1e-3 * 0.3, weight_decay=1e-4)

def evaluate(loader):
    model.eval(); ys, ps = [], []
    with torch.no_grad():
        for x, y in loader:
            pr = torch.softmax(model(x.to(dev)), 1)[:, 1].cpu().numpy()
            ps.append(pr); ys.append(y.numpy())
    y, pr = np.concatenate(ys), np.concatenate(ps)
    pred = (pr > 0.5).astype(int)
    return {"auroc": float(roc_auc_score(y, pr)),
            "macro_f1": float(f1_score(y, pred, average="macro")),
            "accuracy": float(accuracy_score(y, pred))}

best = -1
for ep in range(a.epochs):
    model.train()
    for i, (x, y) in enumerate(tl):
        x, y = x.to(dev), y.to(dev)
        opt.zero_grad(); loss = loss_fn(model(x), y); loss.backward(); opt.step()
        if i % 100 == 0: print(f"epoch {ep+1} step {i}/{len(tl)} loss {loss.item():.4f}")
    v = evaluate(vl); print(f"epoch {ep+1} VALIDATION:", v)
    if v["auroc"] > best:
        best = v["auroc"]; torch.save(model.state_dict(), "model.pt")

model.load_state_dict(torch.load("model.pt", map_location=dev))
res = {"seed": a.seed, "size": a.size, "epochs": a.epochs, "test": evaluate(sl)}
print("FINAL TEST RESULT:", res)
json.dump(res, open(f"results_seed{a.seed}.json", "w"), indent=2)
