import logging
import random
import time

from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics

logging.basicConfig(filename="/var/log/flask-app.log", level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
metrics = PrometheusMetrics(app)

metrics.info("FlaskApp", "Application info", version="1.0.0")

@app.route("/")
def hello_world():
    logger.info("A request was received at the root URL")
    return {"message": "Hello, World!"}, 200


@app.route("/long-request")
def long_request():
    n = random.randint(1, 5)
    logger.info(
        f"A request was received at the long-request URL. Slept for {n} seconds"
    )
    time.sleep(n)
    return {"message": f"Long running request with {n=}"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
