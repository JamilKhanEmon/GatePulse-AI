from ultralytics import YOLO
import os

def main():
    print("🚀 Starting ULTRA-HIGH ACCURACY (90%+ Target) YOLO Training...")
    
    # 1. Use YOLO11 Extra Large (yolo11x.pt) - Highest parameters and feature capacity
    model = YOLO('yolo11x.pt')
    
    # 2. Path to dataset yaml
    dataset_yaml = 'archive/traffic_update.yaml' 
    
    if not os.path.exists(dataset_yaml):
        print(f"❌ Error: '{dataset_yaml}' not found!")
        return

    print(f"✅ Found dataset configuration at: {dataset_yaml}")
    print("⏳ Starting 90%+ Target SOTA Training (1280px Ultra-Res + Heavy CopyPaste)...")
    
    # 3. Hyperparameters engineered for 90%+ mAP50
    results = model.train(
        data=dataset_yaml,
        epochs=150,            # 150 Epochs for maximum convergence
        imgsz=1280,            # 1280 Ultra-High Resolution (Full Detail on small vehicles)
        batch=4,               # Batch 4 for 1280px on 16GB GPU (prevents OOM)
        optimizer='AdamW',     # AdamW Optimizer
        lr0=0.0015,            # Initial LR
        lrf=0.01,              # Final LR ratio
        warmup_epochs=5,
        cos_lr=True,
        
        # --- Loss Weights for Precision & Box Fitting ---
        box=8.5,               # Strong Bounding Box Penalty
        cls=2.5,               # High Class Penalty to fix Minivan/Pickup/Van confusion
        dfl=2.0,               # Distribution Focal Loss for occluded vehicles
        label_smoothing=0.05,
        
        # --- Extreme Augmentation to Boost Rare Classes (Garbagevan, Scooter, Policecar) ---
        copy_paste=0.50,       # 50% Copy-Paste (forces model to learn rare vehicles)
        mosaic=1.0,            # 100% Mosaic
        mixup=0.25,            # 25% Mixup
        scale=0.6,             # Multi-scale
        degrees=12.0,          # Rotation
        perspective=0.0008,    # 3D perspective shift
        hsv_h=0.02,
        hsv_s=0.7,
        hsv_v=0.4,
        fliplr=0.5,
        
        patience=40,
        name='bd_traffic_custom'
    )
    
    print("🎉 90%+ Target Training Completed!")
    print("✅ Best Model saved at: runs/detect/bd_traffic_custom/weights/best.pt")

if __name__ == '__main__':
    main()



