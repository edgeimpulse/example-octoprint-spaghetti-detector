# Stopping the Spaghetti — MakerFair 2025 (OctoPrint + Edge Impulse)

OctoPrint stop the spagetti example using the Linux Python SDK (https://github.com/edgeimpulse/linux-sdk-python) and calling a service api to stop the printer. All running within the same pi as octoprint:
- Pulls MJPEG from OctoPrint
- Runs an Edge Impulse `.eim` model (Linux target)
- Pauses/cancels when an anomaly threshold is exceeded for N consecutive frames


## Quick start

- Sign up for Edge Impulse - https://studio.edgeimpulse.com/signup

- Install and configure a pi to control your printer with Octoprint - https://octoprint.org/

- Enable API Key control (create one called OCTO_KEY)
- <img width="912" height="882" alt="image" src="https://github.com/user-attachments/assets/791591f2-d4f6-4288-9956-babe9ed3e4a8" />


Install the Edge Impulse runner (optional)
- Install NodeJS
  ```
  sudo apt install nodejs
  ```
- Install the Edge Impulse runner (optional) - npm install -g edge-impulse-linux
 ```
npm install -g edge-impulse-linux
  ```

- Clone the Edge Impulse project here first https://studio.edgeimpulse.com/studio/785891/

- <img width="1328" height="539" alt="image" src="https://github.com/user-attachments/assets/378775cf-4ef8-419a-91c4-3f0599678c36" />


  <img width="843" height="419" alt="image" src="https://github.com/user-attachments/assets/8d800156-f449-49da-b6bd-31c8cb5362b3" />


- ENV Vars are set in the env file to default to not interfer with your printer by setting the DRY_RUN variable to 1 change this to 0 when you are ready to use the project.

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


## Once Running correctly you should see the following output:

<img width="1352" height="199" alt="image" src="https://github.com/user-attachments/assets/bac5137a-2226-4b58-8163-4aac5f2ab787" />



