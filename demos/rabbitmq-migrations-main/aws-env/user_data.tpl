#!/bin/bash
apt update -y
apt install -y python3 python3-pip python3-flask python3-boto3

cat <<EOL > /home/ubuntu/app.py
from flask import Flask, request, jsonify
import json
import boto3
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route("/", methods=["POST"])
def sns_handler():
    app.logger.info("Request received")

    # AWS sends JSON with text/plain mimetype
    try:
        sns_message = json.loads(request.data)
        app.logger.info(str(sns_message))
    except Exception as e:
        app.logger.error(str(e))

    # Validate SNS message type
    message_type = request.headers.get("x-amz-sns-message-type")
    app.logger.info(message_type)
    if message_type == "SubscriptionConfirmation":
        app.logger.info("SubscriptionConfirmation")
        # Handle the Subscription Confirmation
        token = sns_message["Token"]
        topic_arn = sns_message["TopicArn"]
        app.logger.info(f"Topic: {topic_arn}")

        # Confirm the subscription
        client = boto3.client("sns", region_name="${aws_region}")
        app.logger.info("Client ready")
        try:
            response = client.confirm_subscription(
                TopicArn=topic_arn,
                Token=token
            )
            app.logger.info(response)
        except Exception as e:
            app.logger.info(str(e))
        app.logger.info("Subscription confirmed: %s", response)
        return jsonify({"message": "Subscription confirmed"}), 200
    elif message_type == "Notification":
        app.logger.info("Notification")
        # Process SNS Notification
        notification_message = sns_message["Message"]
        app.logger.info("Received SNS message: %s", notification_message)
        return jsonify({"message": "Notification received"}), 200
    else:
        app.logger.warning("Unknown message type: %s", message_type)
        return jsonify({"error": "Unknown message type"}), 400

@app.route("/", methods=["GET"])
def default_handler():
    app.logger.info("Request Received.")
    return "SNS Subscription Active", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
EOL

nohup python3 /home/ubuntu/app.py &
