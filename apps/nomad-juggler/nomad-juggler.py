from flask import Flask, Response, request, jsonify
import os
import logging
import urllib.parse
import requests
import time
import base64
from datetime import datetime

app = Flask(__name__)
poll_interval = 2

# Suppress Werkzeug request logs
log = logging.getLogger("werkzeug")
log.setLevel(logging.WARN)  # or logging.CRITICAL to suppress even more

# Get a logging instance
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s", datefmt="%Y-%m-%d %H:%M:%S %z"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set the desired logging level


class ColorCodes:
    RESET = "\033[0m"
    DEBUG = "\033[90m"  # Grey
    INFO = "\033[0m"  # Default (no color change)
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"  # Red
    CRITICAL = "\033[31;1m"  # Bold Red


class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: ColorCodes.DEBUG + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.INFO: ColorCodes.INFO + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.WARNING: ColorCodes.WARNING + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.ERROR: ColorCodes.ERROR + "%(levelname)s: %(message)s" + ColorCodes.RESET,
        logging.CRITICAL: ColorCodes.CRITICAL + "%(levelname)s: %(message)s" + ColorCodes.RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Create a stream handler to output to the console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Set the custom formatter for the handler
ch.setFormatter(ColoredFormatter())

# Add the handler to the logger
logger.addHandler(ch)

NOMAD_ADDR = os.getenv("NOMAD_ADDR", "http://localhost:4646")

# Shared cancel signals
cancel_flags = {}


def timestamped_message(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    return f"data: {ts} {message}\n"


@app.route("/api/<token>/<namespace>/dispatch/<job>", methods=["GET"])
def dispatch_wait_and_tail(token, namespace, job):
    headers = {"X-Nomad-Token": token}
    meta_params = request.args.to_dict()
    timeout = int(meta_params.pop("timeout", 1200))  # default to 1200 seconds
    task_id = f"{token}:{namespace}:{job}"
    cancel_flags[task_id] = False

    # exclude 'tail' as special key.
    data = {"meta": {k: str(v) for k, v in meta_params.items() if k != "tail"}}

    dispatch_url = f"{NOMAD_ADDR}/v1/job/{job}/dispatch?namespace={namespace}"
    logger.info(f"starting {dispatch_url} ")
    response = requests.post(dispatch_url, headers=headers, json=data)

    if response.status_code != 200:
        return Response(f"Dispatch failed: {response.text}", status=response.status_code)

    if "tail" not in meta_params:
        return jsonify({"status": "dispatched", "url": dispatch_url}), 200

    job_id = urllib.parse.quote(response.json()["DispatchedJobID"], safe="")
    alloc_url = f"{NOMAD_ADDR}/v1/job/{job_id}/allocations?namespace={namespace}"

    def generate():
        start_time = time.time()
        stdout_offset = 0
        stderr_offset = 0

        # Wait for allocation
        alloc_id = None
        task_name = None
        for _ in range(10):
            alloc_resp = requests.get(alloc_url, headers=headers)
            if alloc_resp.status_code == 200 and alloc_resp.json():
                alloc = alloc_resp.json()[0]
                alloc_id = alloc["ID"]
                logger.debug(alloc["TaskStates"])
                if "TaskStates" in alloc and alloc["TaskStates"]:
                    task_name = list(alloc["TaskStates"].keys())[0]
                    break
                logger.info(f"task_name: {task_name}")
            time.sleep(poll_interval)

        if not task_name:
            yield timestamped_message("data: Failed to get allocation")
            return

        stdout_url = f"{NOMAD_ADDR}/v1/client/fs/logs/{alloc_id}?namespace={namespace}&task={task_name}&type=stdout"
        stderr_url = f"{NOMAD_ADDR}/v1/client/fs/logs/{alloc_id}?namespace={namespace}&task={task_name}&type=stderr"
        status_url = f"{NOMAD_ADDR}/v1/job/{job_id}/allocations?namespace={namespace}"

        while time.time() - start_time < timeout:
            if cancel_flags.get(task_id):
                logger.info("data: Cancelled by user")
                yield timestamped_message("data: Cancelled by user")
                break

            # Check job status
            status_resp = requests.get(status_url, headers=headers)
            if status_resp.status_code == 200:
                logger.debug(f"status_url {status_url} ")
                status = status_resp.json()[0].get("ClientStatus", "")
                if "running" not in status:
                    yield timestamped_message(f"data: [STATUS] {status}")
                if status.lower() not in ("pending", "running"):
                    logger.info(f"completed status_url {status_url} ")
                    yield timestamped_message(f"data: Job completed {status_url}")
                    return Response(generate(), mimetype="text/event-stream")
                    break

            # Poll stdout
            stdout_resp = requests.get(f"{stdout_url}&offset={stdout_offset}", headers=headers)
            logger.debug(f"polling stdout_url {stdout_url} offset:{stdout_offset}")
            if stdout_resp.status_code == 200 and stdout_resp.text.strip():
                stdout_data = stdout_resp.json()
                if stdout_data.get("Data"):
                    decoded = base64.b64decode(stdout_data["Data"]).decode("utf-8")
                    yield timestamped_message(f"data: [STDOUT] {decoded}")
                stdout_offset = stdout_data.get("Offset", stdout_offset)

            # Poll stderr
            stderr_resp = requests.get(f"{stderr_url}&offset={stderr_offset}", headers=headers)
            logger.debug(f"polling stderr_url {stderr_url} offset:{stderr_offset}")
            if stderr_resp.status_code == 200 and stderr_resp.text.strip():
                logger.info(stderr_resp.text)
                stderr_data = stderr_resp.json()
                if stderr_data.get("Data"):
                    decoded = base64.b64decode(stderr_data["Data"]).decode("utf-8")
                    yield timestamped_message(f"data: [STDERR] {decoded}")
                stderr_offset = stderr_data.get("Offset", stderr_offset)

            time.sleep(poll_interval)

        yield timestamped_message("data: Timeout reached or job finished")
        cancel_flags.pop(task_id, None)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/<token>/<namespace>/cancel/<job>", methods=["POST"])
def cancel_job_stream(token, namespace, job):
    task_id = f"{token}:{namespace}:{job}"
    if task_id in cancel_flags:
        cancel_flags[task_id] = True
        return jsonify({"status": "cancelled", "task_id": task_id}), 200
    return jsonify({"error": "No active task found"}), 404


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


# Landing page
@app.route("/")
def home():
    return """
        <h1>Welcome to My Flask App</h1>
        <p>This is the landing page.</p>
        <ul>
            <li><a href="/about">About</a></li>
            <li><a href="/routes">Show All Routes</a></li>
        </ul>
    """


# About page
@app.route("/about")
def about():
    return "<h2>About Page</h2><p>This is a sample Flask application.</p>"


# Route to list all available endpoints
@app.route("/routes")
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        methods = ",".join(rule.methods)
        output.append(f"{rule.endpoint}: {rule.rule} [{methods}]")
    return "<br>".join(output)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("NOMAD_PORT_juggler", 5000)))
