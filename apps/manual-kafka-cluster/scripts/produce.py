# python producer script for Kafka

from confluent_kafka import Producer
import time
import json

# Kafka SSL configuration
conf = {
    'bootstrap.servers': 'kafka1:9092,kafka2:9092,kafka3:9092',  # Kafka broker
    'client.id': 'python-producer',
    'security.protocol': 'SSL',
    'ssl.ca.location': 'ca-crt',
    'ssl.certificate.location': 'client1.crt',
    'ssl.key.location': 'client1.key',
}

# Create a Producer instance
producer = Producer(conf)

# Our topic
topic = 'test'

# Handle delivery reports
def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

# Produce messages
try:
    for i in range(3):
        # sample event
        event = {
            'event_id': i,
            'timestamp': int(time.time()),
            'message': f"Event number {i}"
        }
        event_json = json.dumps(event)

        # send message to Kafka
        producer.produce(topic, value=event_json, callback=delivery_report)

        # poll to trigger delivery reports
        producer.poll(0)
    producer.flush()
except Exception as e:
    print(f"An error occurred: {e}")