from flask import Flask, Response, request, jsonify, send_file
import os
import logging
import urllib.parse
import requests
import time
import base64
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app, group_by="endpoint")
poll_interval = 2

# Suppress Werkzeug request logs
log = logging.getLogger("werkzeug")
log.setLevel(logging.WARN)  # or logging.CRITICAL to suppress even more

# Get a logging instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False


class ColorCodes:
    RESET = "\033[0m"
    DEBUG = "\033[90m"  # Grey
    INFO = "\033[10m"  # Default (no color change)
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"  # Red
    CRITICAL = "\033[31;1m"  # Bold Red


class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: ColorCodes.DEBUG + "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s" + ColorCodes.RESET,
        logging.INFO: ColorCodes.INFO + "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s" + ColorCodes.RESET,
        logging.WARNING: ColorCodes.WARNING
        + "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s"
        + ColorCodes.RESET,
        logging.ERROR: ColorCodes.ERROR + "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s" + ColorCodes.RESET,
        logging.CRITICAL: ColorCodes.CRITICAL
        + "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d: %(message)s"
        + ColorCodes.RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S %z")
        return formatter.format(record)


if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(ColoredFormatter())
    logger.addHandler(ch)

NOMAD_ADDR = os.getenv("NOMAD_ADDR", "http://localhost:4646")
TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "3"))
# yes, remote fetching favicon can be a startup issue.
FAVICON_URL = os.getenv("FAVICON_URL", "https://github.com/hashicorp/nomad/raw/refs/heads/main/ui/public/favicon.ico")
FAVICON_PATH = "cached_favicon.ico"


# Shared cancel signals
cancel_flags = {}


def cache_favicon():
    if not os.path.exists(FAVICON_PATH):
        try:
            response = requests.get(FAVICON_URL)
            response.raise_for_status()
            with open(FAVICON_PATH, "wb") as f:
                f.write(response.content)
            logger.info("Favicon downloaded and cached.")
        except Exception as e:
            logger.error(f"Failed to download favicon ({FAVICON_URL}): {e}")


def timestamped_message(message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    return f"nomad-juggler: {ts} {message}\n"


@app.route("/api/<token>/<namespace>/restart/<job>", methods=["GET"])
def restart_allocations(token, namespace, job):
    try:
        headers = {"X-Nomad-Token": token}
        meta_params = request.args.to_dict()
        timeout = int(meta_params.pop("timeout", 1200))  # default to 1200 seconds
        wait = meta_params.get("wait", "false").lower() == "true"

        # Step 1: Get all allocations for the job
        alloc_url = f"{NOMAD_ADDR}/v1/job/{job}/allocations?namespace={namespace}"
        response = requests.get(alloc_url, headers=headers)
        response.raise_for_status()
        allocations = response.json()

        # Step 2: Filter running allocations
        running_allocs = [alloc for alloc in allocations if alloc.get("ClientStatus") == "running"]
        # logger.error(running_allocs)

        restarted = []
        for alloc in running_allocs:
            alloc_id = alloc["ID"]
            restart_url = f"{NOMAD_ADDR}/v1/client/allocation/{alloc_id}/restart?namespace={namespace}"
            restart_resp = requests.post(restart_url, headers=headers)
            if restart_resp.status_code == 200:
                logger.debug(restart_url)
                restarted.append(alloc_id)
            else:
                logger.error(restart_url)

        # Step 3 (Optional): Wait for allocations to become running again
        if wait:
            start_time = time.time()
            while time.time() - start_time < timeout:
                all_ready = True
                for alloc_id in restarted:
                    status_url = f"{NOMAD_ADDR}/v1/allocation/{alloc_id}?namespace={namespace}"
                    status_resp = requests.get(status_url, headers=headers)
                    if status_resp.status_code != 200 or status_resp.json().get("ClientStatus") != "running":
                        all_ready = False
                        break
                if all_ready:
                    break
                time.sleep(5)

        returnlog = {
            "running_allocs": len(running_allocs),
            "restarted_allocations": restarted,
            "total_restarted": len(restarted),
            "waited": wait,
        }
        logger.info(returnlog)
        return jsonify(returnlog)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/<token>/<namespace>/dispatch/<job>", methods=["GET"])
def dispatch_wait_and_tail(token, namespace, job):
    try:
        headers = {"X-Nomad-Token": token}
        meta_params = request.args.to_dict()
        timeout = int(meta_params.pop("timeout", 1200))  # default to 1200 seconds
        task_id = f"{token}:{namespace}:{job}"
        cancel_flags[task_id] = False

        # exclude 'tail' as special key.
        data = {"meta": {k: str(v) for k, v in meta_params.items() if k != "tail"}}

        dispatch_url = f"{NOMAD_ADDR}/v1/job/{job}/dispatch?namespace={namespace}"
        logger.info(f"starting {dispatch_url} ")
        response = requests.post(dispatch_url, headers=headers, json=data, timeout=TIMEOUT)
        response.raise_for_status()

        if response.status_code != 200:
            return Response(f"Dispatch failed: {response.text}", status=response.status_code)

        if "tail" not in meta_params:
            return jsonify({"status": "dispatched", "url": dispatch_url}), 200

        job_id = urllib.parse.quote(response.json()["DispatchedJobID"], safe="")
        alloc_url = f"{NOMAD_ADDR}/v1/job/{job_id}/allocations?namespace={namespace}"
        nomad_ui_job_url = f"{NOMAD_ADDR}/ui/jobs/{job_id}@{namespace}"

        def generate():
            timestamped_message(f"[JOB_UI] started {nomad_ui_job_url}")
            yield timestamped_message(f"[JOB_UI] started {nomad_ui_job_url}")
            start_time = time.time()
            stdout_offset = 0
            stderr_offset = 0

            # Wait for allocation
            alloc_id = None
            task_name = None
            for _ in range(10):
                alloc_resp = requests.get(alloc_url, headers=headers, timeout=TIMEOUT)
                alloc_resp.raise_for_status()
                if alloc_resp.status_code == 200 and alloc_resp.json():
                    alloc = alloc_resp.json()[0]
                    alloc_id = alloc["ID"]
                    logger.debug(alloc["TaskStates"])
                    if "TaskStates" in alloc and alloc["TaskStates"]:
                        task_name = list(alloc["TaskStates"].keys())[0]
                        break
                    logger.debug(f"task_name: {task_name}")
                time.sleep(poll_interval)

            if not task_name:
                yield timestamped_message("Failed to get allocation")
                return

            stdout_url = f"{NOMAD_ADDR}/v1/client/fs/logs/{alloc_id}?namespace={namespace}&task={task_name}&type=stdout"
            stderr_url = f"{NOMAD_ADDR}/v1/client/fs/logs/{alloc_id}?namespace={namespace}&task={task_name}&type=stderr"
            status_url = f"{NOMAD_ADDR}/v1/job/{job_id}/allocations?namespace={namespace}"
            nomad_ui_alloc_url = f"{NOMAD_ADDR}/ui/allocations/{alloc_id}/{task_name}"

            timestamped_message(f"[ALLOC_UI] started {nomad_ui_alloc_url}")
            yield timestamped_message(f"[ALLOC_UI] started {nomad_ui_alloc_url}")

            while time.time() - start_time < timeout:
                if cancel_flags.get(task_id):
                    logger.warn("Cancelled by user")
                    yield timestamped_message("Cancelled by user")
                    break

                # Check job status
                status_resp = requests.get(status_url, headers=headers, timeout=TIMEOUT)
                status_resp.raise_for_status()
                if status_resp.status_code == 200:
                    logger.debug(f"status_url {status_url} ")
                    status = status_resp.json()[0].get("ClientStatus", "")
                    if "running" not in status:
                        yield timestamped_message(f"[STATUS] {status}")
                    if status.lower() not in ("pending", "running"):
                        logger.debug(f"completed status_url {status_url} ")
                        yield timestamped_message(f"Job completed {status_url}")
                        yield timestamped_message(f"[JOB_UI] {nomad_ui_job_url}")
                        return Response(generate(), mimetype="text/event-stream")
                        break

                # Poll stdout
                stdout_resp = requests.get(f"{stdout_url}&offset={stdout_offset}", headers=headers, timeout=TIMEOUT)
                logger.debug(f"polling stdout_url {stdout_url} offset:{stdout_offset}")
                if stdout_resp.status_code == 200 and stdout_resp.text.strip():
                    stdout_data = stdout_resp.json()
                    if stdout_data.get("Data"):
                        decoded = base64.b64decode(stdout_data["Data"]).decode("utf-8")
                        yield timestamped_message(f"[STDOUT container-logs] {decoded}")
                    stdout_offset = stdout_data.get("Offset", stdout_offset)

                # Poll stderr
                stderr_resp = requests.get(f"{stderr_url}&offset={stderr_offset}", headers=headers, timeout=TIMEOUT)
                logger.debug(f"polling stderr_url {stderr_url} offset:{stderr_offset}")
                if stderr_resp.status_code == 200 and stderr_resp.text.strip():
                    logger.debug(stderr_resp.text)
                    stderr_data = stderr_resp.json()
                    if stderr_data.get("Data"):
                        decoded = base64.b64decode(stderr_data["Data"]).decode("utf-8")
                        yield timestamped_message(f"[STDERR container-logs] {decoded}")
                    stderr_offset = stderr_data.get("Offset", stderr_offset)

                time.sleep(poll_interval)

            yield timestamped_message("Timeout reached or job finished")
            cancel_flags.pop(task_id, None)

        return Response(generate(), mimetype="text/event-stream")
    except requests.exceptions.ConnectionError as e:
        return jsonify({"error": f"Connection error: {e}"}), 503
    except requests.exceptions.Timeout as e:
        return jsonify({"error": f"Timeout error (TIMEOUT:{TIMEOUT}): {e}"}), 504
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"HTTP error: {e}"}), response.status_code
    except requests.exceptions.TooManyRedirects as e:
        return jsonify({"error": f"Too many redirects: {e}"}), 310
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


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


@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="shortcut icon" type="image/x-icon" href="/favicon.ico">
        <title>Nomad Juggling App</title>
        <style>
            body { font-family: sans-serif; background: #f9f9f9; padding: 40px; text-align: center; }
            h1 { color: #333; }
            p { color: #555; max-width: 600px; margin: auto; }
            a { display: inline-block; margin-top: 20px; color: #007BFF; text-decoration: none; }
            footer { margin-top: 40px; font-size: 0.8em; color: #aaa; }
        </style>
    </head>
    <body>
        <h1>🧭 Nomad Juggling App</h1>
        <p>A tiny proxy that juggles with POST and GET to make Nomad behave—and your PowerShell curl scripts breathe easier.</p>
        <a href=/about>Learn more →</a>
        <footer>
            <p>AI – POC - ideation ally</p>
        </footer>
    </body>
    </html>
    """


@app.route("/about")
def about():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="shortcut icon" type="image/x-icon" href="/favicon.ico">
        <title>About - Nomad Juggling App</title>
        <style>
            body { font-family: sans-serif; background: #fff; padding: 40px; max-width: 800px; margin: auto; }
            h1, h2 { color: #333; }
            p { color: #555; line-height: 1.6; }
            ul { color: #444; }
            li { margin-bottom: 10px; }
            footer { margin-top: 40px; font-size: 0.8em; color: #aaa; text-align: center; }
        </style>
    </head>
    <body>
        <h1>About Nomad Juggling App</h1>
        <p>
            The Nomad Juggling App is a lightweight HTTP proxy designed to smooth out the rough edges of working with HashiCorp Nomad,
            especially when dealing with PowerShell's quirky <code>curl</code> behavior and Nomad's sensitivity to HTTP methods.
        </p>
        <p>
            It automatically flips <strong>POST</strong> to <strong>GET</strong> requests to ensure compatibility and reduce friction
            in your automation workflows.
        </p>

        <h2>Why Juggle?</h2>
        <ul>
            <li>🌀 <strong>Workaround Nomad's method-specific bugs</strong> with ease</li>
            <li>🧠 <strong>Simplify PowerShell curl headaches</strong>—especially when <code>Invoke-WebRequest</code> gets picky</li>
            <li>⚡ <strong>Speed up automation</strong> with a drop-in solution that just works</li>
        </ul>

        <p>Built for Nomad users, by Nomad users. Because deployment should be elegant—even when the tools aren’t.</p>

        <footer>
            <p>AI – POC - ideation ally</p>
        </footer>
    </body>
    </html>
    """


@app.route("/favicon.ico")
def serve_favicon():
    cache_favicon()
    if os.path.exists(FAVICON_PATH):
        return send_file(FAVICON_PATH, mimetype="image/vnd.microsoft.icon")
    return "", 404


# Route to list all available endpoints
@app.route("/routes")
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        methods = ",".join(rule.methods)
        output.append(f"{rule.endpoint}: {rule.rule} [{methods}]")
    return "<br>".join(output)


if __name__ == "__main__":
    cache_favicon()
    app.run(host="0.0.0.0", port=int(os.getenv("NOMAD_PORT_juggler", 5000)))
