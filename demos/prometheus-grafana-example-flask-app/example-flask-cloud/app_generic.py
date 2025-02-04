import boto3
import json
import logging
import time

from flask import Flask, request

logging.basicConfig(filename='/var/log/flask-app.log', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def send_latency_metric(response):
    latency = time.time() - request.start_time

    # Send latency metrics to cloud provider.
    # Include request.path, request.method, and latency

    return response

@app.route('/')
def hello_world():
    logger.info("A request was received at the root URL")
    return {'message': 'Hello, World!'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
