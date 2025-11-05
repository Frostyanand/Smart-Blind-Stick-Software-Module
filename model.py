# model.py
from flask import Flask, render_template, Response, jsonify, request
from werkzeug.utils import secure_filename
import cv2
import time
import os
from pathlib import Path
from ultralytics import YOLO
import main as tts_main   # our TTS module
import config  # configuration management

# ---------------- APP ----------------
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = str(config.UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# ---------------- GLOBALS ----------------
_camera_index = 0
_video_file = None  # Path to uploaded video file (if any)
_use_video_file = False
_last_detections = []  # [(xyxy, name, conf), ...]
_last_infer_time = 0.0
_last_announced = {}   # {class_name: last_time}

# ---------------- LOAD MODEL ----------------
print("[INFO] Loading YOLOv11s model...")
model = YOLO(config.MODEL_NAME)
print("[INFO] Model loaded.")

# Print configuration
config.print_config()

# ---------------- CAMERA UTILITIES ----------------
def list_cameras(max_idx=config.CAMERA_PROBE_MAX):
    available = []
    for i in range(max_idx):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
        if cap is None or not cap.isOpened():
            try: cap.release()
            except Exception: pass
            continue
        ret, _ = cap.read()
        if ret: available.append(i)
        try: cap.release()
        except Exception: pass
    return available

@app.route("/cameras")
def cameras():
    cams = list_cameras()
    return jsonify({"cameras": cams, "default": _camera_index})

@app.route("/set_camera/<int:idx>", methods=["POST"])
def set_camera(idx):
    global _camera_index, _use_video_file, _video_file
    cams = list_cameras()
    if idx not in cams:
        return jsonify({"ok": False, "error": "camera index not available", "available": cams}), 400
    _camera_index = idx
    _use_video_file = False
    _video_file = None
    return jsonify({"ok": True, "camera": idx})

@app.route("/upload_video", methods=["POST"])
def upload_video():
    global _video_file, _use_video_file
    
    if 'video' not in request.files:
        return jsonify({"ok": False, "error": "No video file provided"}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({"ok": False, "error": "No file selected"}), 400
    
    if file and config.allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        _video_file = filepath
        _use_video_file = True
        
        print(f"[INFO] Video uploaded: {filename}")
        return jsonify({"ok": True, "filename": filename, "path": filepath})
    
    return jsonify({"ok": False, "error": "Invalid file type"}), 400

@app.route("/use_camera", methods=["POST"])
def use_camera():
    global _use_video_file
    _use_video_file = False
    return jsonify({"ok": True, "mode": "camera"})

def should_announce_class(class_name):
    """Check if a detected class should be announced based on TTS_MODE"""
    if config.TTS_MODE == 'ALL':
        return True
    elif config.TTS_MODE == 'CUSTOM':
        return class_name in config.CUSTOM_CLASSES
    return False

# ---------------- FRAME GENERATOR ----------------
def gen_frames():
    global _camera_index, _video_file, _use_video_file, _last_detections, _last_infer_time, _last_announced
    cap = None
    
    while True:
        # (re)open video source if needed
        if cap is None or not cap.isOpened():
            if _use_video_file and _video_file and os.path.exists(_video_file):
                print(f"[INFO] Opening video file: {_video_file}")
                cap = cv2.VideoCapture(_video_file)
            else:
                cap = cv2.VideoCapture(_camera_index, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
            
            if not cap.isOpened():
                if _use_video_file:
                    print(f"[ERROR] Unable to open video file {_video_file}, retrying in 1s.")
                else:
                    print(f"[ERROR] Unable to open camera {_camera_index}, retrying in 1s.")
                time.sleep(1.0)
                continue
            time.sleep(0.2)  # warmup

        ret, frame = cap.read()
        if not ret:
            # If video file ended, loop it
            if _use_video_file:
                print("[INFO] Video ended, restarting...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                cap.release()
                cap = None
                continue

        now = time.time()
        # Run inference periodically
        if now - _last_infer_time >= config.INFERENCE_INTERVAL:
            results = model(frame, verbose=False)
            _last_detections = []  # reset detections
            detected_classes = set()

            for box in results[0].boxes:
                try:
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    xy = box.xyxy[0]
                except Exception:
                    conf = float(box.conf)
                    cls_id = int(box.cls)
                    xy = box.xyxy

                if conf < config.CONF_THRESHOLD:
                    continue

                name = model.names.get(cls_id, str(cls_id))
                _last_detections.append((xy, name, conf))
                
                # Print detection to terminal
                print(f"[DETECTION] {name} (confidence: {conf:.2f})")

                # Add to detected classes if it should be announced
                if should_announce_class(name):
                    detected_classes.add(name)

            # TTS with cooldown
            if len(detected_classes) > 0:
                print(f"[TTS] Detected classes to announce: {detected_classes}")
            
            for cls in detected_classes:
                last = _last_announced.get(cls, 0.0)
                time_since_last = now - last
                print(f"[TTS] Checking {cls}: last={last:.2f}, now={now:.2f}, diff={time_since_last:.2f}, cooldown={config.TTS_COOLDOWN}")
                
                if time_since_last >= config.TTS_COOLDOWN:
                    print(f"[INFO] ✓ Speaking: {cls}")
                    tts_main.enqueue_speak(cls)
                    _last_announced[cls] = now
                else:
                    print(f"[INFO] ✗ Skipping {cls} (cooldown: {time_since_last:.1f}s / {config.TTS_COOLDOWN}s)")

            _last_infer_time = now

        # Draw last detections every frame (persistent boxes)
        for xy, name, conf in _last_detections:
            x1, y1, x2, y2 = map(int, xy)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
            cv2.putText(frame, f"{name} {conf:.2f}", (x1, max(10, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)

        ret2, jpeg = cv2.imencode('.jpg', frame)
        if not ret2:
            continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        
        # Small delay to prevent CPU overload and stabilize streaming
        time.sleep(config.FRAME_DELAY)

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html", tts_mode=config.TTS_MODE, 
                          custom_classes=', '.join(config.CUSTOM_CLASSES) if config.TTS_MODE == 'CUSTOM' else 'ALL')

@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/config")
def get_config():
    """Return current configuration"""
    return jsonify({
        "tts_mode": config.TTS_MODE,
        "custom_classes": config.CUSTOM_CLASSES,
        "cooldown": config.TTS_COOLDOWN,
        "conf_threshold": config.CONF_THRESHOLD,
        "inference_interval": config.INFERENCE_INTERVAL
    })

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    print("[INFO] Starting TTS worker thread...")
    tts_main.start_tts_worker()
    print("[INFO] Starting Flask server on http://127.0.0.1:5000")
    app.run(host=config.HOST, port=config.PORT, threaded=True, debug=config.DEBUG)
