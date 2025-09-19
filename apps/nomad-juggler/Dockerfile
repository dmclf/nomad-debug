FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY nomad-juggler.py nomad-juggler.py

CMD ["python", "nomad-juggler.py"]
#CMD ["gunicorn", "--bind", "0.0.0.0:5000", "nomad-juggler:app"]

