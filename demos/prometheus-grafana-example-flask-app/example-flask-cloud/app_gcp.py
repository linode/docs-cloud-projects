import json
import logging
import time

from flask import Flask, request
from google.cloud import monitoring_v3 # Note: pip install google-cloud-monitoring

logging.basicConfig(filename='/var/log/flask-app.log', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Google Cloud Monitoring setup
metric_client = monitoring_v3.MetricServiceClient()
project_id = 'YOUR_PROJECT_ID'  # replace with your project ID
project_name = f"projects/{project_id}"

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def send_latency_metric(response):
    latency = time.time() - request.start_time

    # Send latency metric to Google Cloud Monitoring
    series = monitoring_v3.TimeSeries()
    series.metric.type = 'custom.googleapis.com/EndpointLatency'
    series.resource.type = 'global'
    series.metric.labels['endpoint'] = request.path
    series.metric.labels['method'] = request.method

    point = monitoring_v3.Point()
    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10**9)
    point.interval.end_time.seconds = seconds
    point.interval.end_time.nanos = nanos
    point.value.double_value = latency

    series.points.append(point)
    metric_client.create_time_series(name=project_name, time_series=[series])

    return response

@app.route('/')
def hello_world():
    logger.info("A request was received at the root URL")
    return {'message': 'Hello, World!'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
