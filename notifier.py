import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    "notifications", bootstrap_servers="localhost:9092", auto_offset_reset="earliest", enable_auto_commit=True, group_id="notifier_group", value_deserializer=lambda m: json.loads(m.decode("utf-8"))
)


def send_notification(notification):
    user_id = notification["user_id"]
    symbol = notification["symbol"]
    change = notification["change_percentage"]
    timestamp = notification["timestamp"]

    change_type = "涨幅" if change >= 0 else "跌幅"
    message = f"用户{user_id}，您好！股票{symbol}的{change_type}已达到" f"{abs(change):.2f}%。"
    # 集成邮件、短信或推送通知服务
    print(f"发送通知: {message}")


def main():
    for message in consumer:
        notification = message.value
        send_notification(notification)


if __name__ == "__main__":
    main()
