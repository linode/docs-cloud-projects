from flask import Flask
import pika
import threading
import json
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

def rabbitmq_listener():
    """
    Opens listener to the desired RabbitMQ queue and handles incoming messages
    """
    def callback(ch, method, properties, body):
        """
        Callback function to handle incoming messages from RabbitMQ
        """
        app.logger.info(body.decode('utf-8'))
        # Do other processing here as needed on messages

    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host="<RABBITMQ_HOST>",
        port=5672,
        credentials=pika.PlainCredentials("flask_app_user", "<RABBITMQ_PASSWORD>"),
    ))

    channel = connection.channel()
    channel.basic_consume(queue="flask_queue", on_message_callback=callback, auto_ack=True)
    app.logger.info("Started listening to RabbitMQ...")
    channel.start_consuming()

# Start RabbitMQ listener in a separate thread
listener_thread = threading.Thread(target=rabbitmq_listener, daemon=True)
listener_thread.start()

@app.route("/", methods=["GET"])
def default_handler():
    app.logger.info("Request received.")
    return "RabbitMQ Listener Active", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
