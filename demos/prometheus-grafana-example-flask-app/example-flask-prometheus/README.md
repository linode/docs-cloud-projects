# Example Flask -> Prometheus

How to export logs and metrics to Prometheus for the same app.

Copy this `app.py` in place of the deployed version on the EC2 instance and
restart the `flask-app` service via: `sudo systemctl restart flask-app`.

Then hit `http://<IP-of-instance>/metrics` to see the scrape payload.
