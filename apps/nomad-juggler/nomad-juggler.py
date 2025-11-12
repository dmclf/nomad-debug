from flask import Flask, Response, request, jsonify, send_file, url_for
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
POLL_INTERVAL = int(os.getenv("REQUEST_TIMEOUT", "5"))

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
            logger.info(
                f"Favicon downloaded {FAVICON_URL} and cached:{FAVICON_PATH} status_code:{response.status_code} size:{len(response.content)}"
            )
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
        dry_run = meta_params.get("dry_run", "false").lower() == "true"
        verbose = meta_params.get("verbose", "false").lower() == "true"
        task_name = meta_params.get("task_name")  # optional filter

        # Step 1: Get all allocations for the job
        alloc_url = f"{NOMAD_ADDR}/v1/job/{job}/allocations?namespace={namespace}"
        response = requests.get(alloc_url, headers=headers)
        response.raise_for_status()
        allocations = response.json()

        # Step 2: Filter running allocations
        running_allocs = []
        for alloc in allocations:
            if alloc.get("ClientStatus") != "running":
                continue

            task_states = alloc.get("TaskStates", {})
            running_tasks = [task for task, state in task_states.items() if state.get("State") == "running"]

            if running_tasks:
                alloc["RunningTasks"] = running_tasks  # optional: store for verbose output
                running_allocs.append(alloc)

        # Step 2.5: If task_name is provided, filter allocations that include that task
        skipped_allocations = []
        if task_name:
            filtered_allocs = []
            for alloc in running_allocs:
                task_states = alloc.get("TaskStates", {})
                if task_name in task_states:
                    filtered_allocs.append(alloc)
                else:
                    skipped_allocations.append(
                        {
                            # "alloc_id": alloc.get("ID"),
                            # "node_id": alloc.get("NodeID"),
                            "node_name": alloc.get("NodeName"),
                            "task_names": list(task_states.keys()),
                        }
                    )
            running_allocs = filtered_allocs

        restarted = []
        verbose_details = []
        restart_url = None

        for alloc in running_allocs:
            alloc_id = alloc["ID"]
            restart_url = f"{NOMAD_ADDR}/v1/client/allocation/{alloc_id}/restart?namespace={namespace}"

            if dry_run:
                logger.info(f"[DRY RUN] Would restart: {restart_url}")
                restarted.append(alloc_id)
            else:
                restart_resp = requests.post(restart_url, headers=headers)
                if restart_resp.status_code == 200:
                    logger.debug(restart_url)
                    restarted.append(alloc_id)
                else:
                    logger.error(restart_url)

            if verbose:
                verbose_details.append(
                    {
                        "alloc_id": alloc_id,
                        "node_id": alloc.get("NodeID"),
                        "node_name": alloc.get("NodeName"),
                        "task_names": list(alloc.get("TaskStates", {}).keys()),
                        "running_tasks": alloc.get("RunningTasks", []),
                        "restart_url": restart_url,
                        "dry_run": dry_run,
                    }
                )

        # Step 3 (Optional): Wait for allocations to become running again
        if wait and not dry_run:
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
            "filtered_by_task_name": task_name if task_name else "none",
            "dry_run": dry_run,
        }

        if verbose:
            returnlog["details"] = verbose_details
            if task_name:
                returnlog["skipped_due_to_task_name_mismatch"] = skipped_allocations

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
        dry_run = meta_params.get("dry_run", "false").lower() == "true"
        verbose = meta_params.get("verbose", "false").lower() == "true"
        task_id = f"{token}:{namespace}:{job}"
        cancel_flags[task_id] = False

        # Prepare dispatch payload
        data = {"meta": {k: str(v) for k, v in meta_params.items() if k not in ["tail", "dry_run", "verbose"]}}
        dispatch_url = f"{NOMAD_ADDR}/v1/job/{job}/dispatch?namespace={namespace}"

        if dry_run:
            logger.info(f"[DRY RUN] Would dispatch job to: {dispatch_url}")
            return jsonify({"status": "dry_run", "dispatch_url": dispatch_url, "meta": data["meta"]}), 200

        logger.info(f"Dispatching job to: {dispatch_url}")
        response = requests.post(dispatch_url, headers=headers, json=data, timeout=TIMEOUT)
        response.raise_for_status()

        if response.status_code != 200:
            return Response(f"Dispatch failed: {response.text}", status=response.status_code)

        dispatched_job_id = response.json()["DispatchedJobID"]
        job_id = urllib.parse.quote(dispatched_job_id, safe="")
        alloc_url = f"{NOMAD_ADDR}/v1/job/{job_id}/allocations?namespace={namespace}"
        nomad_ui_job_url = f"{NOMAD_ADDR}/ui/jobs/{job_id}@{namespace}"

        if "tail" not in meta_params:
            result = {
                "status": "dispatched",
                "dispatched_job_id": dispatched_job_id,
                "dispatch_url": dispatch_url,
                "nomad_ui_job_url": nomad_ui_job_url,
            }
            if verbose:
                result["meta"] = data["meta"]
            return jsonify(result), 200

        # Blocking tail: wait for allocation + job completion, then return final status.
        # This blocks the request until the job finishes or timeout is reached.
        # Wait for allocation
        alloc_id = None
        task_name = None
        for _ in range(10):
            alloc_resp = requests.get(alloc_url, headers=headers, timeout=TIMEOUT)
            alloc_resp.raise_for_status()
            if alloc_resp.status_code == 200 and alloc_resp.json():
                alloc = alloc_resp.json()[0]
                alloc_id = alloc["ID"]
                if "TaskStates" in alloc and alloc["TaskStates"]:
                    task_name = list(alloc["TaskStates"].keys())[0]
                    break
            time.sleep(POLL_INTERVAL)

        if not task_name:
            return jsonify({"error": "Failed to get allocation"}), 504

        status_url = f"{NOMAD_ADDR}/v1/job/{job_id}/allocations?namespace={namespace}"
        start_time = time.time()
        final_status = None

        while time.time() - start_time < timeout:
            if cancel_flags.get(task_id):
                cancel_flags.pop(task_id, None)
                return jsonify({"status": "cancelled", "task_id": task_id}), 200

            status_resp = requests.get(status_url, headers=headers, timeout=TIMEOUT)
            status_resp.raise_for_status()
            if status_resp.status_code == 200 and status_resp.json():
                final_status = status_resp.json()[0].get("ClientStatus", "")
                if final_status.lower() not in ("pending", "running"):
                    break

            time.sleep(POLL_INTERVAL)

        if not final_status:
            return jsonify({"error": "No status available"}), 504

        if final_status.lower() == "failed":
            # Try to collect last available stdout/stderr from the allocation
            stdout_log = ""
            stderr_log = ""
            try:
                stdout_url = f"{NOMAD_ADDR}/v1/client/fs/logs/{alloc_id}?namespace={namespace}&task={task_name}&type=stdout&offset=0"
                stderr_url = f"{NOMAD_ADDR}/v1/client/fs/logs/{alloc_id}?namespace={namespace}&task={task_name}&type=stderr&offset=0"

                so = requests.get(stdout_url, headers=headers, timeout=TIMEOUT)
                if so.status_code == 200 and so.text.strip():
                    so_j = so.json()
                    if so_j.get("Data"):
                        stdout_log = base64.b64decode(so_j["Data"]).decode("utf-8", errors="replace")

                se = requests.get(stderr_url, headers=headers, timeout=TIMEOUT)
                if se.status_code == 200 and se.text.strip():
                    se_j = se.json()
                    if se_j.get("Data"):
                        stderr_log = base64.b64decode(se_j["Data"]).decode("utf-8", errors="replace")
            except Exception as e:
                logger.debug(f"Failed to fetch logs for failed job: {e}")

            # Truncate logs to a reasonable size
            maxlen = 10000
            if len(stdout_log) > maxlen:
                stdout_log = stdout_log[-maxlen:]
            if len(stderr_log) > maxlen:
                stderr_log = stderr_log[-maxlen:]

            return (
                jsonify(
                    {
                        "error": "Nomad Job Failed",
                        "nomad_ui_job_url": nomad_ui_job_url,
                        "stdout": stdout_log,
                        "stderr": stderr_log,
                    }
                ),
                418,
            )

        result = {
            "status": "completed",
            "client_status": final_status,
            "nomad_ui_job_url": nomad_ui_job_url,
        }
        if verbose:
            result["meta"] = data["meta"]
        return jsonify(result), 200

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
    example_values = {"token": "00000000-2000-0000-0000-000000000000", "namespace": "default", "job": "job42"}

    descriptions = {
        "dispatch_wait_and_tail": "Dispatches a job and waits for its output stream.",
        "cancel_job_stream": "Cancels a running job stream.",
        "restart_allocations": "Restarts allocations for a given token and namespace.",
        "health": "Health check endpoint.",
        "home": "Home page.",
        "about": "About page.",
        "serve_favicon": "Serves the favicon.",
        "list_routes": "Lists all available routes.",
        "prometheus_metrics": "Exposes Prometheus metrics.",
    }

    output = []
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        endpoint = rule.endpoint
        url = rule.rule

        # Check if the route has dynamic arguments
        has_args = bool(rule.arguments)

        # Build example URL accordingly
        try:
            if has_args:
                example_url = url_for(endpoint, **example_values)
            else:
                example_url = url_for(endpoint)
        except Exception:
            example_url = url  # fallback to raw rule

        description = descriptions.get(endpoint, "No description available.")
        output.append(f"<strong>{endpoint}</strong>: {example_url} [{methods}]<br>" f"Description: {description}<br><br>")
    return "<br>".join(output)


if __name__ == "__main__":
    cache_favicon()
    app.run(host="0.0.0.0", port=int(os.getenv("NOMAD_PORT_juggler", 5000)))
