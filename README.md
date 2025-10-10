# Stopping the Spaghetti — MakerFair 2025 (OctoPrint + Edge Impulse)

One-file script that:
- Pulls MJPEG from OctoPrint
- Runs an Edge Impulse `.eim` model (Linux target)
- Pauses/cancels when an anomaly threshold is exceeded for N consecutive frames

## Quick start


#!/usr/bin/env python3
"""

Clone the Edge Impulse project here first
https://studio.edgeimpulse.com/studio/785891/

OctoPrint stop the spagetti example using the Linux Python SDK and calling a service api to stop the printer. All running within the same pi as octoprint.
- Runs .eim model
- Pauses/cancels when anomaly exceeds threshold for N consecutive frames
"""

```bash
git clone https://github.com/edgeimpulse/example-octoprint-spaghetti-detector
cd example-octoprint-spaghetti-detector
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
nano .env   # set OCTO_KEY, etc.

# Get your model:
# In Edge Impulse Studio > Deploy > Linux (x86_64 / aarch64) > Download .eim
# Save as ./model.eim or point MODEL_FILE in .env

python classify.py
```


