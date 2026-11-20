"""Track a selected camera target and preview relative mecanum commands."""

from __future__ import annotations

import argparse
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

BASE = Path(__file__).resolve().parent
WINDOW = "Robot Tracking - Simulasi Mecanum"


def mecanum_command(box, shape, reference, strafe):
    """Return relative chassis and X-layout wheel commands, capped at 60 percent."""
    height, width = shape[:2]
    x1, y1, x2, y2 = box
    error = np.array([(reference - (y2 - y1) / height) / reference, 1 - (x1 + x2) / width])
    error[np.abs(error) <= (0.12, 0.10)] = 0
    forward, lateral = np.clip(error, -1, 1)
    left, turn = (lateral, 0) if strafe else (0, lateral)
    wheels = np.array([forward - left - turn, forward + left + turn, forward + left - turn, forward - left + turn])
    scale = 0.6 / max(1.0, float(np.max(np.abs(wheels))))
    return np.array([forward, left, turn]) * scale, wheels * scale


class RobotSimulation:
    """Own target selection, visual feedback, and simulated wheel output."""

    def __init__(self):
        """Start with no selected target and zero commands."""
        self.target_id = None
        self.reference = None
        self.paused = False
        self.strafe = True
        self.tracks = {}
        self.shape = (480, 640)
        self.trail = deque(maxlen=30)
        self.velocity = np.zeros(3)
        self.wheels = np.zeros(4)
        self.status = "KLIK TARGET UNTUK MEMILIH"

    def mouse(self, event, x, y, flags, param):
        """Select the smallest tracked box under a left click."""
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        matches = [
            (track_id, box) for track_id, box in self.tracks.items() if box[0] <= x <= box[2] and box[1] <= y <= box[3]
        ]
        if matches:
            self.target_id, box = min(matches, key=lambda item: (item[1][2] - item[1][0]) * (item[1][3] - item[1][1]))
            self.reference = (box[3] - box[1]) / self.shape[0]
            self.trail.clear()

    def key(self, key):
        """Handle pause, deselection, size calibration, and lateral mode."""
        if key == ord(" "):
            self.paused = not self.paused
        elif key == ord("c"):
            self.target_id = None
            self.reference = None
            self.trail.clear()
        elif key == ord("r") and self.target_id in self.tracks:
            box = self.tracks[self.target_id]
            self.reference = (box[3] - box[1]) / self.shape[0]
        elif key == ord("m"):
            self.strafe = not self.strafe

    def update(self, tracks, shape):
        """Calculate commands only from the selected target in the current frame."""
        self.tracks, self.shape = tracks, shape
        self.velocity[:] = 0
        self.wheels[:] = 0
        if self.target_id is None:
            self.status = "KLIK TARGET UNTUK MEMILIH"
        elif self.paused:
            self.status = "JEDA - STOP"
        elif self.target_id not in tracks:
            self.status = "TARGET HILANG - STOP"
            self.trail.clear()
        else:
            box = tracks[self.target_id]
            self.velocity, self.wheels = mecanum_command(box, shape, self.reference, self.strafe)
            self.trail.append((int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)))
            self.status = "TARGET TERKUNCI"

    def draw(self, frame, fps):
        """Draw selection guides, a top view of four wheels, and keyboard controls."""
        height, width = frame.shape[:2]
        canvas = np.full((max(600, height + 90), width + 360, 3), (30, 25, 21), dtype=np.uint8)
        canvas[:height, :width] = frame

        def text(value, x, y, color=(220, 225, 230), scale=0.5):
            cv2.putText(canvas, value, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)

        green, amber = (130, 220, 80), (70, 185, 255)
        for x in (int(width * 0.45), int(width * 0.55)):
            cv2.line(canvas, (x, 0), (x, height), (110, 100, 90), 1)
        cv2.drawMarker(canvas, (width // 2, height // 2), green, cv2.MARKER_CROSS, 22, 1)
        box = self.tracks.get(self.target_id)
        if box is not None:
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), green, 3)
            text(f"TARGET ID {self.target_id}", x1, min(height - 8, y2 + 18), green)
        if len(self.trail) > 1:
            cv2.polylines(canvas, [np.array(self.trail, dtype=np.int32)], False, green, 2)

        x = width + 18
        text("ROBOT TRACKING", x, 34, green, 0.7)
        text("TAHAP 1 + 2 | SIMULASI MECANUM", x, 60)
        text(self.status, x, 99, green if box is not None and not self.paused else amber, 0.48)
        text(f"Target ID: {self.target_id if self.target_id is not None else '--'}", x, 130)
        text(f"Mode: {'GESER SAMPING' if self.strafe else 'PUTAR BADAN'}", x, 158)
        actions = []
        for value, positive, negative in zip(
            self.velocity, ("MAJU", "KIRI", "PUTAR KIRI"), ("MUNDUR", "KANAN", "PUTAR KANAN")
        ):
            if abs(value) > 1e-6:
                actions.append(positive if value > 0 else negative)
        text(" + ".join(actions) or "STOP", x, 188, amber, 0.55)
        if box is not None:
            text(f"Ukuran: {(box[3] - box[1]) / height:.0%} | Acuan: {self.reference:.0%}", x, 217)
        text("DEPAN ROBOT", width + 126, 252)
        cv2.rectangle(canvas, (width + 131, 276), (width + 229, 410), (120, 115, 110), 2)
        for label, value, wx, wy in zip(
            ("FL", "FR", "RL", "RR"), self.wheels, (90, 270, 90, 270), (300, 300, 390, 390)
        ):
            cx = width + wx
            cv2.rectangle(canvas, (cx - 12, wy - 22), (cx + 12, wy + 22), (90, 85, 80), -1)
            if abs(value) > 1e-6:
                cv2.arrowedLine(canvas, (cx, wy), (cx, wy - int(value * 35 / 0.6)), green, 2, tipLength=0.35)
            text(f"{label} {value:+.0%}", cx - 40, wy - 31, green, 0.45)
        forward, left, turn = self.velocity
        cv2.arrowedLine(
            canvas, (width + 180, 345), (width + 180 - int(left * 75), 345 - int(forward * 75)), amber, 3, tipLength=0.3
        )
        text(f"MAJU {forward:+.2f}  KIRI {left:+.2f}", x, 451)
        text(f"PUTAR KIRI {turn:+.2f}", x, 478)
        text("Roda relatif: -60% sampai +60%", x, 511)
        text("FL/FR: depan | RL/RR: belakang", x, 537)
        text("Acuan ukuran gambar, belum meter", x, 568, amber, 0.45)
        text("KLIK target | SPACE: jeda/lanjut", 12, height + 24)
        text("R: acuan ukuran | C: lepas target | M: geser/putar", 12, height + 48, scale=0.43)
        text(f"S: screenshot | Q/ESC: keluar | {fps:.1f} FPS", 12, height + 72)
        return canvas


def main():
    """Run camera or video tracking with a simulated mecanum dashboard."""
    weights = BASE / "yolo26n.pt"
    if not weights.is_file():
        weights = BASE.parent / "yolo26n.pt"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0", help="Indeks kamera (0/1) atau path video")
    parser.add_argument("--model", type=Path, default=weights, help="Path bobot YOLO lokal")
    parser.add_argument("--class-id", type=int, default=0, help="Kelas COCO target; 0 = person")
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error(f"Bobot tidak ditemukan: {args.model}. Gunakan --model PATH.")

    import torch

    from ultralytics import YOLO

    device = 0 if torch.cuda.is_available() else "cpu"
    model = YOLO(str(args.model))
    if args.class_id not in model.names:
        parser.error(f"Class ID {args.class_id} tidak tersedia pada model ini.")
    camera = args.source.isdecimal()
    source = int(args.source) if camera else args.source
    cap = cv2.VideoCapture(source, cv2.CAP_DSHOW if camera and os.name == "nt" else cv2.CAP_ANY)
    simulation = RobotSimulation()
    try:
        if not cap.isOpened():
            raise SystemExit(f"Sumber tidak dapat dibuka: {args.source}. Coba --source 1 untuk kamera lain.")
        if camera:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        source_fps = cap.get(cv2.CAP_PROP_FPS) if not camera else 0
        cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(WINDOW, simulation.mouse)
        print(f"SIMULASI MECANUM | device={device} | target={model.names[args.class_id]}", flush=True)
        print("Klik target. SPACE jeda, R acuan ukuran, C lepas, M mode, S screenshot, Q keluar.", flush=True)
        previous = time.perf_counter()
        while True:
            started = time.perf_counter()
            success, frame = cap.read()
            if not success:
                print("Sumber selesai atau frame kamera tidak dapat dibaca. STOP.", flush=True)
                break
            scale = min(1.0, 800 / frame.shape[1], 600 / frame.shape[0])
            if scale < 1:
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
            result = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[args.class_id],
                device=device,
                imgsz=640,
                conf=0.25,
                verbose=False,
            )[0]
            boxes = result.boxes
            tracks = dict(zip(boxes.id.int().cpu().tolist(), boxes.xyxy.cpu().tolist())) if boxes.is_track else {}
            simulation.update(tracks, frame.shape)
            now = time.perf_counter()
            canvas = simulation.draw(result.plot(), 1 / (now - previous))
            previous = now
            cv2.imshow(WINDOW, canvas)
            delay = max(1, round((1 / source_fps - (time.perf_counter() - started)) * 1000)) if source_fps > 0 else 1
            key = cv2.waitKey(delay) & 0xFF
            if key in (ord("q"), 27) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            simulation.key(key)
            if key == ord("s"):
                output = BASE / "runs" / "robot_tracking"
                output.mkdir(parents=True, exist_ok=True)
                path = output / f"robot_{datetime.now():%Y%m%d_%H%M%S_%f}.jpg"
                if not cv2.imwrite(str(path), canvas):
                    raise OSError(f"Screenshot gagal disimpan: {path}")
                print(f"Screenshot: {path}", flush=True)
    finally:
        simulation.velocity[:] = 0
        simulation.wheels[:] = 0
        cap.release()
        cv2.destroyAllWindows()
        print("Simulasi berhenti. Semua perintah roda = 0.", flush=True)


if __name__ == "__main__":
    main()
