# MedVisionAI

A research prototype that looks at a small H&E-stained colorectal tissue patch and says whether it looks like **tumor epithelium** or **other tissue**, with a heatmap showing which parts pushed the model toward "tumor". For pathology students and researchers who want to explore what a model pays attention to.

**Not a medical device. Not for clinical use or diagnosis.**

**Live demo:** (https://medvisionai-d29bxykp26rzddgp4bds2c.streamlit.app/)

## What it does
Upload a tissue patch (or pick an example), get a tumor probability and a Grad-CAM heatmap.

## Data and model
- Data: PathMNIST from the MedMNIST collection (derived from NCT-CRC-HE colorectal histology), 64 x 64 images, official train/val/test split.
- Task: the 9 tissue types are turned into 2 labels: tumor epithelium (colorectal adenocarcinoma epithelium) vs everything else.
- Model: ResNet18 with ImageNet weights, fine-tuned for 3 epochs (plain PyTorch, class-weighted loss).
- Explanation: Grad-CAM on the third residual stage. At 64 px the heatmap is coarse.

## Results (test set, 3 seeds, mean +/- standard deviation)
| Metric | Result |
|---|---|
| AUROC | 0.9968 +/- 0.0009 |
| Macro-F1 | 0.9592 +/- 0.0036 |
| Accuracy | 0.9764 +/- 0.0028 |

Seeds 0, 1 and 2. This task is fairly easy (tumor tissue vs 8 other tissue types), so high numbers do not mean the model is ready for real clinical images.

## Limitations
- Trained only on one public colorectal dataset at 64 x 64 resolution. Not tested on other scanners, stains or hospitals.
- One-vs-rest labels: "other tissue" is not the same as "benign".
- Patient-level splits are as provided by the dataset. Not independently checked.
- A non-histology image still gets a prediction, which is meaningless.
- Heatmaps are coarse and show model attention, not proof of medical reasoning.

## Run it locally
```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
To retrain (a GPU such as a free Colab T4 helps):
```
pip install medmnist scikit-learn
python train.py --seed 0
```

## Who built what
- [FILL IN: full name]: [FILL IN: what this person actually did]
- [FILL IN: full name]: [FILL IN]

## Earlier work
This project builds on earlier master's thesis work on medical image classification. [FILL IN: one honest sentence on what is new and what was reused.] The code in this repository was written during the Thirduni programme.

## Tech stack
Python, PyTorch, torchvision, MedMNIST, scikit-learn, Streamlit, Streamlit Community Cloud, GitHub, Google Colab. AI tools: Claude was used to help write code and documentation.

## What next
More cancer types and datasets, higher resolution (128 px or more) for sharper heatmaps, self-supervised pretraining, testing on a second dataset, and feedback from pathologists.
