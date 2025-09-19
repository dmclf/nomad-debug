# NomadJuggler

NomadJuggler is a lightweight Python Flask service that acts as a smart proxy for dispatching Nomad jobs. 
It accepts simple GET requests and converts them into properly formatted POST requests to the Nomad API.

[saw the light due to](https://github.com/hashicorp/nomad/issues/26693)

## 🚀 Overview
NomadJuggler simplifies job dispatching by allowing clients to use GET requests with query parameters, which are internally translated into Nomad-compatible POST requests.

there might be some possible concerns with putting the token in GET requests, in this app they would not be logged, but if you feel its an issue, obviously feel free to not use this.

*(born as a middleware for rundeck with powershell curl and simplistic one-liners)*

## ✨ Features
- Accepts GET requests with token, namespace, job, and meta parameters
- Converts GET into POST requests to Nomad API
- Adds required headers and JSON payload
- Logs dispatch activity
- Includes health endpoints

## 🧪 Usage
```bash
# Run the Flask app
python app.py

# Or use Gunicorn for production
gunicorn --bind 0.0.0.0:5000 app:app

# Or run the docker
docker run -it --rm -p 5050:5050 -e NOMAD_PORT_juggler=5050 -e NOMAD_ADDR=https://nomad-endpoint.com dmclf/nomad-juggler:0.1a
```


## 📡 API Reference
### GET /api/{token}/{namespace}/{job}?meta1=value1&meta2=value2
Dispatches a Nomad job using the provided parameters.
```bash
example:
http://localhost:5050/api/00000000-2000-0000-0000-000000000000/default/dispatch/parameterized-job?SCRIPT=runthis.sh&DAY=1970-01-01
```
optionally:
`http://localhost:5050/api/00000000-2000-0000-0000-000000000000/default/dispatch/parameterized-job?SCRIPT=runthis.sh&DAY=1970-01-01&tail=true`
to keep the session open and return logs

and this will
- invoke a POST to https://nomad-endpoint.com/v1/jobs/parameterized-job?namespace=default
 - with meta SCRIPT=runthis.sh and DAY=1970-01-01
- whilst providing a header X-Nomad-Token: 00000000-2000-0000-0000-000000000000

### GET /health
Returns a simple health check response.

## 📄 License
MIT License
