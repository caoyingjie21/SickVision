from ultralytics import YOLO

model = YOLO("best.pt")

results = model("image.png", save=True)

print(results)
