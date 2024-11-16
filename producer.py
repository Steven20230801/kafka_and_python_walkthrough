import json
import time
import random
from kafka import KafkaProducer

STOCK_SYMBOLS = ["AAPL", "GOOG", "TSLA"]


def get_stock_price(symbol):
    return round(random.uniform(100, 200), 2)


def main():
    producer = KafkaProducer(bootstrap_servers="localhost:9092", value_serializer=lambda v: json.dumps(v).encode("utf-8"))

    while True:
        for symbol in STOCK_SYMBOLS:
            price = get_stock_price(symbol)
            message = {"symbol": symbol, "price": price, "timestamp": time.time()}
            producer.send("stock_prices", message)
            print(f"Produced: {message}")
        producer.flush()
        time.sleep(5)


if __name__ == "__main__":
    main()
