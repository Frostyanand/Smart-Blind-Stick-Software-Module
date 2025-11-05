# Smart Blind Stick - Object Detection with TTS

Real-time object detection using YOLOv11s with text-to-speech announcements.

## Quick Start

### 1. Install Dependencies
```bash
pip install ultralytics opencv-python flask pyttsx3 python-dotenv
```

### 2. Run
```bash
python model.py
```

### 3. Open Browser
```
http://127.0.0.1:5000
```

## Configuration (.env file)

Create a `.env` file to configure the system:

```ini
# TTS Mode: "ALL" (announce everything) or "CUSTOM" (announce specific classes)
TTS_MODE=ALL

# Custom classes (only used if TTS_MODE=CUSTOM)
CUSTOM_CLASSES=person,chair,car,dog,cat,laptop,bottle,cup,phone

# TTS Cooldown (seconds between announcements of same object)
TTS_COOLDOWN=3.0

# TTS Settings
TTS_RATE=150
TTS_VOLUME=1.0
TTS_REPEAT=1

# Detection Settings
CONF_THRESHOLD=0.45
INFERENCE_INTERVAL=1.0
FRAME_DELAY=0.03

# Model
MODEL_NAME=yolo11s.pt

# Server
HOST=0.0.0.0
PORT=5000
```

## Using the Web Interface

### Camera Feed
- Default tab shows camera selection
- Choose camera from dropdown
- Click "Set Camera"

### Video File Upload
1. Click the **"🎬 Video File"** tab at the top
2. Click "Choose File"
3. Select MP4/AVI/MOV/MKV/WEBM file
4. Click "Upload & Play"
5. Video will loop automatically with detection

## Expected Console Output

```
[INFO] Loading YOLOv11s model...
[INFO] Model loaded.
TTS Mode: ALL
Announcing: ALL detected objects
TTS Cooldown: 3.0s

[TTS] Engine initialized successfully
[TTS] Worker thread started successfully
[INFO] Starting Flask server on http://127.0.0.1:5000

[DETECTION] person (confidence: 0.87)
[DETECTION] chair (confidence: 0.65)
[TTS] Detected classes to announce: {'person', 'chair'}
[TTS] Checking person: last=0.00, now=123.45, diff=123.45, cooldown=3.0
[INFO] ✓ Speaking: person
[TTS] Enqueuing: person (repeat=1, queue_size=0)
[TTS] Speaking now: person (1/1)
[TTS] Completed in 0.56s
```

## Troubleshooting

### No TTS Announcements
- Check terminal for `[DETECTION]` messages - if missing, no objects detected
- Look for `[INFO] ✓ Speaking:` or `[INFO] ✗ Skipping` 
- If "✗ Skipping" appears, cooldown is active (wait 3 seconds)
- Verify `.env` has `TTS_MODE=ALL`
- **If logs show "Completed in 0.08s":** This means TTS is failing silently. Restart the app - the engine now reinitializes for each speech (Windows fix)
- Test TTS: `python -c "import pyttsx3; e=pyttsx3.init(); e.say('test'); e.runAndWait()"`

### No Detections
- Lower confidence threshold: `CONF_THRESHOLD=0.3` in `.env`
- Point camera at common objects (person, chair, bottle, phone)
- Check if camera is working in other applications

### Video Upload Not Visible
- Click the **"🎬 Video File" TAB** at the top of the page
- The upload controls are hidden by default (camera tab is active)
- Hard refresh browser: `Ctrl + Shift + R`

## Project Structure

```
smart_blind_stick/
├── model.py              # Flask app, YOLO inference, TTS integration
├── main.py               # TTS worker thread management
├── config.py             # Configuration loader (.env parser)
├── .env                  # User configuration
├── yolo11s.pt           # YOLOv11 model weights
├── templates/
│   └── index.html       # Web interface
├── static/
│   └── style.css        # Styling
├── uploads/             # Video file storage (auto-created)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Available COCO Classes

You can detect and announce any of these 80 classes:

person, bicycle, car, motorcycle, airplane, bus, train, truck, boat, traffic light, fire hydrant, stop sign, parking meter, bench, bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe, backpack, umbrella, handbag, tie, suitcase, frisbee, skis, snowboard, sports ball, kite, baseball bat, baseball glove, skateboard, surfboard, tennis racket, bottle, wine glass, cup, fork, knife, spoon, bowl, banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza, donut, cake, chair, couch, potted plant, bed, dining table, toilet, tv, laptop, mouse, remote, keyboard, cell phone, microwave, oven, toaster, sink, refrigerator, book, clock, vase, scissors, teddy bear, hair drier, toothbrush

## Recent Updates

### Latest Changes (October 2025)
- ✅ Added `.env` configuration file support
- ✅ TTS now announces ALL detected objects (configurable via TTS_MODE)
- ✅ Added video file upload feature
- ✅ Added detailed detection printing to terminal
- ✅ Added extensive TTS debug logging
- ✅ Improved TTS reliability with auto-recovery
- ✅ Added queue monitoring to prevent backlog
- ✅ Added per-class cooldown tracking
- ✅ Added tab-based UI (Camera/Video)
- ✅ Added modern responsive design

### Key Features
- **Flexible TTS:** Announce all objects or custom list via `.env`
- **Video Upload:** Test with video files (perfect for demos)
- **Persistent Boxes:** Bounding boxes stay visible between inference cycles
- **Auto-Recovery:** TTS worker restarts automatically on errors
- **Debug Logging:** See every detection and TTS decision in console

## Technical Notes

- Uses YOLOv11s for object detection (CPU inference ~70-150ms)
- pyttsx3 for offline text-to-speech (Windows SAPI5)
  - **Windows Fix:** Engine is reinitialized for each speech to avoid runAndWait() bug
- Flask for web interface
- OpenCV for video processing
- Detections printed to terminal in real-time
- TTS runs in separate thread to avoid blocking

## License

Educational and accessibility purposes.
