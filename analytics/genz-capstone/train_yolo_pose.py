"""L2: fine-tune a YOLO pose model to find tragus + C7 (run on a machine with a GPU).

  pip install ultralytics
  python -m cva.yolo_pose_data  (or call build()) to create datasets/cva/data.yaml
  python train_yolo_pose.py --data datasets/cva/data.yaml --epochs 150

Starts from COCO-pretrained pose weights (transfer learning) — COCO has ears
but no C7, so the head learns the new keypoint from your labels.
Realistic data target before expecting stable results: ~150–300 subjects.
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True); ap.add_argument("--model", default="yolo11n-pose.pt")
ap.add_argument("--epochs", type=int, default=150); ap.add_argument("--imgsz", type=int, default=640)
a = ap.parse_args()

from ultralytics import YOLO
model = YOLO(a.model)
model.train(data=a.data, epochs=a.epochs, imgsz=a.imgsz, patience=30,
            fliplr=0.5,            # safe: CVA uses |dx|, facing direction does not matter
            degrees=3.0,           # keep rotation small — rotation changes the true angle!
            mosaic=0.0)            # whole-person context matters more than mosaic variety
metrics = model.val(split="test")
print(metrics)
