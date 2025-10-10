#!/usr/bin/env python3
"""
OctoPrint stop the spagetti example using the Linux Python SDK and calling a service api to stop the printer. All running within the same pi as octoprint.
- Runs .eim model
- Pauses/cancels when anomaly exceeds threshold for N consecutive frames
"""

import os, time, cv2, requests, math, signal
from collections import deque
from dotenv import load_dotenv
from datetime import datetime

from edge_impulse_linux.image import ImageImpulseRunner

# ───── Config ────────────────────────────────────────────────────────────────
load_dotenv()

OCTO_URL   = os.getenv("OCTO_URL",   "http://octopi.local").rstrip("/")
OCTO_KEY   = os.getenv("OCTO_KEY",   "")
MJPEG_URL  = os.getenv("MJPEG_URL",  f"{OCTO_URL}/webcam/?action=stream")
MODEL_FILE = os.getenv("MODEL_FILE", "./model.eim")

ANOM_THRESH      = max(0.0, min(1.0, float(os.getenv("ANOM_THRESH", "0.70"))))
CONSEC_REQUIRED  = max(1, int(os.getenv("CONSEC_REQUIRED", "5")))
WINDOW_SIZE      = max(CONSEC_REQUIRED, int(os.getenv("WINDOW_SIZE", "8")))
COOLDOWN_SEC     = max(0, int(os.getenv("COOLDOWN_SEC", "30")))
ACTION           = os.getenv("ACTION", "pause")  # pause | cancel | gcode
GCODE            = os.getenv("GCODE", "M25")
DRY_RUN          = os.getenv("DRY_RUN", "1") == "1"
TARGET_FPS       = float(os.getenv("TARGET_FPS", "30"))   # adaptive sleep
DEBUG_OVERLAY    = os.getenv("DEBUG_OVERLAY", "0") == "1"

# ───── Helpers ───────────────────────────────────────────────────────────────
def log(*args):
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), *args, flush=True)

def call_octoprint(action: str) -> bool:
    if DRY_RUN:
        log(f"[DRY-RUN] Would {action}")
        return True
    headers = {"X-Api-Key": OCTO_KEY, "Content-Type": "application/json"}
    url = f"{OCTO_URL}/api/job" if action in ("pause", "cancel") else f"{OCTO_URL}/api/printer/command"
    payload = (
        {"command":"pause","action":"pause"} if action=="pause" else
        {"command":"cancel"} if action=="cancel" else
        {"command": GCODE}
    )
    # small retry loop
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=5)
            ok = r.ok
            log(f"OctoPrint {action} -> {r.status_code} {r.text[:120]}")
            if ok: return True
        except Exception as e:
            log(f"OctoPrint call failed (attempt {attempt+1}/3): {e}")
        time.sleep(0.5 * (attempt + 1))
    return False

def consecutive_above_threshold(scores, thr, need):
    consec = 0
    for s in reversed(scores):
        if s >= thr: consec += 1
        else: break
    return consec >= need

# ───── Main ─────────────────────────────────────────────────────────────────
def main():
    # Basic validation
    if not os.path.exists(MODEL_FILE):
        log(f"ERROR: MODEL_FILE not found: {MODEL_FILE}")
        return
    if not OCTO_KEY and not DRY_RUN:
        log("WARNING: OCTO_KEY is empty and DRY_RUN=0. Requests will fail.")

    # Don’t oversubscribe CPU on small boards
    try:
        cv2.setNumThreads(1)
    except Exception:
        pass

    runner = ImageImpulseRunner(MODEL_FILE)
    cap = None
    buf = deque(maxlen=WINDOW_SIZE)
    last_action_ts = 0
    stop_flag = {"stop": False}

    def handle_sigint(sig, frame):
        stop_flag["stop"] = True
        log("Stopping... (Ctrl+C)")
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    try:
        info = runner.init()
        params = info.get("modelParameters", {})
        in_w = params.get("image_input_width") or 320
        in_h = params.get("image_input_height") or 240
        resize_to = (int(in_w), int(in_h))
        log("[Model] Loaded", info.get("project", {}))
        log(f"[Model] Input: {resize_to}, Threshold: {ANOM_THRESH}, "
            f"Consec: {CONSEC_REQUIRED}, Cooldown: {COOLDOWN_SEC}s, DRY_RUN={DRY_RUN}")

        # MJPEG open with reconnect/backoff
        backoff = 1.0
        while not stop_flag["stop"]:
            if cap is None or not cap.isOpened():
                log(f"[Camera] Opening {MJPEG_URL}")
                cap = cv2.VideoCapture(MJPEG_URL)
                if not cap.isOpened():
                    log(f"[Camera] Failed, retry in {backoff:.1f}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 10.0)
                    continue
                backoff = 1.0

            t0 = time.monotonic()
            ok, frame_bgr = cap.read()
            if not ok:
                log("[Camera] Read failed, reopening...")
                cap.release()
                cap = None
                time.sleep(0.5)
                continue

            # Convert BGR->RGB and resize for EI
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            inp = cv2.resize(frame_rgb, resize_to, interpolation=cv2.INTER_AREA)

            # Inference
            try:
                res = runner.classify(inp)
            except Exception as e:
                log("Classify error:", e)
                time.sleep(0.05)
                continue

            # Score selection
            if "anomaly" in res:
                score = float(res["anomaly"])
            elif "result" in res and "classification" in res["result"]:
                ok_prob = float(res["result"]["classification"].get("ok", 0.0))
                score = max(0.0, 1.0 - ok_prob)
            else:
                score = 0.0

            buf.append(score)

            # Debug overlay (local tune sessions only)
            if DEBUG_OVERLAY:
                disp = frame_bgr.copy()
                cv2.putText(disp, f"score:{score:.2f} thr:{ANOM_THRESH:.2f}",
                            (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0) if score<ANOM_THRESH else (0,0,255), 2)
                cv2.imshow("spaghetti-guard", disp)
                if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
                    break

            # Cooldown & decision
            if (time.monotonic() - last_action_ts) >= COOLDOWN_SEC:
                if consecutive_above_threshold(buf, ANOM_THRESH, CONSEC_REQUIRED):
                    log(f"[TRIGGER] score={score:.3f} >= thr={ANOM_THRESH} for {CONSEC_REQUIRED} frames. ACTION={ACTION}")
                    if call_octoprint(ACTION):
                        last_action_ts = time.monotonic()
                        buf.clear()  # reset after action to avoid immediate re-trigger

            # Pace to TARGET_FPS
            if TARGET_FPS > 0:
                loop = time.monotonic() - t0
                target_dt = 1.0 / TARGET_FPS
                if loop < target_dt:
                    time.sleep(target_dt - loop)

            if stop_flag["stop"]:
                break

    finally:
        try:
            if cap is not None:
                cap.release()
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            runner.stop()
        except Exception:
            pass
        log("Stopped cleanly.")

if __name__ == "__main__":
    main()
