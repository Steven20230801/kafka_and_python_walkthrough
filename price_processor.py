import json
from kafka import KafkaConsumer, KafkaProducer
import redis


def get_subscribers():
    # 从 Redis 获取订阅者列表
    subscribers_json = redis_client.get("subscribers")
    if subscribers_json:
        return json.loads(subscribers_json)
    return []


def save_subscribers(subscribers):
    # 将订阅者列表保存到 Redis
    redis_client.set("subscribers", json.dumps(subscribers))


def get_old_price(symbol):
    price = redis_client.get(f"old_price:{symbol}")
    return float(price) if price else 0.0


def set_old_price(symbol, price):
    redis_client.set(f"old_price:{symbol}", price)


redis_client = redis.Redis(host="localhost", port=6379, db=0)

consumer = KafkaConsumer(
    "stock_prices",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="price_processor_group",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)

producer = KafkaProducer(bootstrap_servers="localhost:9092", value_serializer=lambda v: json.dumps(v).encode("utf-8"))


def should_notify(subscriber, change_percentage):
    direction = subscriber.get("direction", "both")
    threshold = subscriber.get("threshold", 0)
    if direction == "up" and change_percentage >= threshold:
        return True
    elif direction == "down" and change_percentage <= -threshold:
        return True
    elif direction == "both" and abs(change_percentage) >= threshold:
        return True
    return False


def main():
    subscribers = get_subscribers()

    if not subscribers:
        # 如果 Redis 中没有订阅者，初始化订阅者列表
        subscribers = [
            {"user_id": 1, "stock_symbol": "AAPL", "threshold": 2, "priority": 1, "direction": "up"},
            {"user_id": 2, "stock_symbol": "GOOG", "threshold": 3, "priority": 2, "direction": "down"},
            {"user_id": 3, "stock_symbol": "TSLA", "threshold": 5, "priority": 1, "direction": "both"},
        ]
        save_subscribers(subscribers)

    # 构建订阅者映射，按股票分组
    subscription_map = {}
    for sub in subscribers:
        symbol = sub["stock_symbol"]
        if symbol not in subscription_map:
            subscription_map[symbol] = []
        subscription_map[symbol].append(sub)

    for message in consumer:
        data = message.value
        symbol = data["symbol"]
        current_price = data["price"]
        timestamp = data["timestamp"]

        old_price = get_old_price(symbol)
        if old_price == 0:
            old_price = current_price  # 初始化 old_price
        change_percentage = ((current_price - old_price) / old_price) * 100 if old_price != 0 else 0

        print(f"Received: {data}, Change: {change_percentage:.2f}%")

        # 更新 old_price
        set_old_price(symbol, current_price)

        # 检查是否需要通知
        if symbol in subscription_map:
            for subscriber in subscription_map[symbol]:
                if should_notify(subscriber, change_percentage):
                    notification_event = {"user_id": subscriber["user_id"], "symbol": symbol, "change_percentage": change_percentage, "timestamp": timestamp}
                    producer.send("notifications", notification_event)
                    print(f"Notification Event Produced: {notification_event}")

        producer.flush()


if __name__ == "__main__":
    main()
