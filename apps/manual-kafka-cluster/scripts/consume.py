from confluent_kafka import Consumer, KafkaException, KafkaError
import json

# Kafka SSL configuration
conf = {
    'bootstrap.servers': 'kafka1:9092,kafka2:9092,kafka3:9092',  # Kafka broker
    'group.id': 'python-consumer-group',
    'auto.offset.reset': 'earliest',
    'security.protocol': 'SSL',
    'ssl.ca.location': 'ca-crt',
    'ssl.certificate.location': 'client1.crt',
    'ssl.key.location': 'client1.key',
}

# Create a Consumer instance
consumer = Consumer(conf)

# Our topic
topic = 'test'

# Subscribe to the topic
consumer.subscribe([topic])

# Consume messages
try:
    while True:
        msg = consumer.poll(timeout=1.0)  # Poll for a message
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition event
                print(f"Reached end of partition {msg.partition()} at offset {msg.offset()}")
            elif msg.error():
                raise KafkaException(msg.error())
        else:
            # Successful message consumption
            event = json.loads(msg.value().decode('utf-8'))
            print(f"Received event: {event}")
except KeyboardInterrupt:
    print("Consumer interrupted by user")
finally:
    # Close down consumer cleanly
    consumer.close()