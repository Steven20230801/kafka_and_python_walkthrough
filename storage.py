import redis
import json

# 连接 Redis
redis_client = redis.Redis(host="localhost", port=6379, db=0)


def get_subscribers():
    subscribers_json = redis_client.get("subscribers")
    if subscribers_json:
        return json.loads(subscribers_json)
    return []


def save_subscribers(subscribers):
    redis_client.set("subscribers", json.dumps(subscribers))


def get_old_price(symbol):
    price = redis_client.get(f"old_price:{symbol}")
    return float(price) if price else 0.0


def set_old_price(symbol, price):
    redis_client.set(f"old_price:{symbol}", price)
