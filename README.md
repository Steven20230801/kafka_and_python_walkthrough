# kafka_and_python_walkthrough
https://youtu.be/D2NYvGlbK0M



wget https://downloads.apache.org/kafka/3.8.1/kafka_2.13-3.8.1.tgz
tar -xzf kafka_2.13-3.8.1.tgz
# rename  kafka_2.13-3.8.1 dir  to kafka
mv kafka_2.13-3.8.1 kafka
cd kafka
bin/zookeeper-server-start.sh config/zookeeper.properties

# 確認ZooKeeper 是否正常運行
bin/zookeeper-shell.sh localhost:2181 ls /brokers/ids

```bash
回傳
Connecting to localhost:2181

WATCHER::

WatchedEvent state:SyncConnected type:None path:null
[]
```

# 以后台方式启动 ZooKeeper
bin/zookeeper-server-start.sh config/zookeeper.properties &


# 2.4 启动 Kafka Broker

bin/kafka-server-start.sh config/server.properties

2.5 创建 Kafka 主题（可选）

# 创建 stock_prices 主题
bin/kafka-topics.sh --create --topic stock_prices --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

# 创建 notifications 主题
bin/kafka-topics.sh --create --topic notifications --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

您可以列出现有的 Kafka 主题以确认 Kafka 是否正在运行：

bash
複製程式碼

bin/kafka-topics.sh --list --bootstrap-server localhost:9092




是的，您可以使用 **Apache Kafka** 来构建和扩展您的股价涨跌幅通知系统。Kafka 是一个分布式流处理平台，非常适合处理实时数据流、高吞吐量和高可靠性的应用场景。通过将 Kafka 集成到您的系统中，您可以提高系统的可扩展性、可靠性和性能。

下面将详细介绍如何在您的股价涨跌幅通知系统中使用 Kafka，包括架构设计、组件说明以及示例代码。

## **1. Kafka 概述**

### **1.1 什么是 Kafka？**

Apache Kafka 是一个分布式的流处理平台，主要用于构建实时数据管道和流应用。它具有以下核心组件：

- **Producer**：负责向 Kafka 主题（Topic）发布消息的客户端。
- **Consumer**：从 Kafka 主题中订阅和消费消息的客户端。
- **Broker**：Kafka 服务器，负责存储消息和管理消费者。
- **Topic**：消息的分类或频道，Producer 将消息发布到特定的 Topic，Consumer 订阅相应的 Topic。
- **Partition**：每个 Topic 分为多个分区，用于提高并行处理能力和容错性。
- **Consumer Group**：多个消费者组成的组，共同消费一个 Topic 的消息，实现负载均衡和高可用性。

### **1.2 为什么选择 Kafka？**

- **高吞吐量**：Kafka 能处理大量实时数据流，适用于高频率的股价更新。
- **可扩展性**：支持水平扩展，可以根据需求增加 Broker、Partition 等。
- **持久性和容错性**：消息持久化存储，支持多副本，提高数据可靠性。
- **实时处理**：低延迟的数据传输和处理，适合实时通知系统。

## **2. 系统架构设计**

将 Kafka 集成到您的股价涨跌幅通知系统，可以按照以下架构设计：

### **2.1 架构组件**

1. **股票价格数据源（Data Source）**：
   - 通过 API（如 Yahoo Finance、Alpha Vantage）或交易所数据获取实时股价。
   - 作为 Kafka Producer，将股价更新发布到 Kafka 主题。

2. **Kafka 集群**：
   - 存储和传输股价更新消息。
   - 配置适当的 Topic 和 Partition，以满足吞吐量和并行处理需求。

3. **价格处理服务（Price Processing Service）**：
   - 作为 Kafka Consumer，订阅股价更新主题。
   - 维护 `old_price`，计算涨跌幅。
   - 根据涨跌幅条件，生成通知事件并发布到另一个 Kafka 主题（如 Notification Topic）。

4. **通知服务（Notification Service）**：
   - 作为 Kafka Consumer，订阅通知主题。
   - 根据通知事件，向相应的订阅者发送通知（如邮件、短信、推送通知）。

5. **订阅管理和存储（Subscription Management & Storage）**：
   - 使用数据库（如 PostgreSQL、Redis）存储订阅者信息、`old_price` 等。
   - 确保数据的一致性和持久性。

### **2.2 架构图示**

```
+-------------------+        +-------------+        +-------------------+
| 股票价格数据源    | -----> | Kafka Topic | -----> | Price Processing  |
| (Producer)        |        | (Stock Prices) |     | Service (Consumer)|
+-------------------+        +-------------+        +-------------------+
                                                         |
                                                         v
                                                +-------------------+
                                                | Kafka Topic       |
                                                | (Notifications)   |
                                                +-------------------+
                                                         |
                                                         v
                                                +-------------------+
                                                | Notification      |
                                                | Service (Consumer)|
                                                +-------------------+
```

## **3. Kafka 集成详细实现**

### **3.1 安装和配置 Kafka**

首先，确保您已经安装并配置好了 Kafka 集群。如果尚未安装，可以参考以下步骤：

1. **下载 Kafka**：
   - 从 [Apache Kafka 官网](https://kafka.apache.org/downloads) 下载最新版本。

2. **启动 ZooKeeper**：
   ```bash
   bin/zookeeper-server-start.sh config/zookeeper.properties
   ```

3. **启动 Kafka Broker**：
   ```bash
   bin/kafka-server-start.sh config/server.properties
   ```

4. **创建必要的 Kafka 主题**：
   ```bash
   bin/kafka-topics.sh --create --topic stock_prices --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
   bin/kafka-topics.sh --create --topic notifications --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
   ```

### **3.2 实现 Kafka Producer（股票价格数据发布）**

这个组件负责从数据源获取实时股价，并将更新发布到 Kafka 的 `stock_prices` 主题。

```python
# producer.py
import json
import time
import random
from kafka import KafkaProducer

# 定义股票列表
STOCK_SYMBOLS = ["AAPL", "GOOG", "TSLA"]

def get_stock_price(symbol):
    # 模拟获取股票价格，实际应调用真实API
    return round(random.uniform(100, 200), 2)

def main():
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    while True:
        for symbol in STOCK_SYMBOLS:
            price = get_stock_price(symbol)
            message = {
                'symbol': symbol,
                'price': price,
                'timestamp': time.time()
            }
            producer.send('stock_prices', message)
            print(f"Produced: {message}")
        producer.flush()
        time.sleep(5)  # 每5秒发布一次更新

if __name__ == "__main__":
    main()
```

### **3.3 实现价格处理服务（Kafka Consumer）**

该服务订阅 `stock_prices` 主题，维护 `old_price`，计算涨跌幅，并根据条件生成通知事件发布到 `notifications` 主题。

```python
# price_processor.py
import json
import heapq
from kafka import KafkaConsumer, KafkaProducer

# 存储每个股票的上一周期价格
stock_prices = {}

# 配置 Kafka Producer 和 Consumer
consumer = KafkaConsumer(
    'stock_prices',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='price_processor_group',
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def should_notify(subscriber, change_percentage):
    direction = subscriber.get('direction', 'both')
    threshold = subscriber.get('threshold', 0)
    if direction == 'up' and change_percentage >= threshold:
        return True
    elif direction == 'down' and change_percentage <= -threshold:
        return True
    elif direction == 'both' and abs(change_percentage) >= threshold:
        return True
    return False

def main():
    # 假设从数据库加载订阅者信息
    subscribers = [
        {'user_id': 1, 'stock_symbol': 'AAPL', 'threshold': 2, 'priority': 1, 'direction': 'up'},
        {'user_id': 2, 'stock_symbol': 'GOOG', 'threshold': 3, 'priority': 2, 'direction': 'down'},
        {'user_id': 3, 'stock_symbol': 'TSLA', 'threshold': 5, 'priority': 1, 'direction': 'both'},
    ]
    
    # 构建订阅者映射，按股票分组
    subscription_map = {}
    for sub in subscribers:
        symbol = sub['stock_symbol']
        if symbol not in subscription_map:
            subscription_map[symbol] = []
        subscription_map[symbol].append(sub)
    
    for message in consumer:
        data = message.value
        symbol = data['symbol']
        current_price = data['price']
        timestamp = data['timestamp']
        
        old_price = stock_prices.get(symbol, current_price)
        change_percentage = ((current_price - old_price) / old_price) * 100 if old_price != 0 else 0
        
        print(f"Received: {data}, Change: {change_percentage:.2f}%")
        
        # 更新 old_price
        stock_prices[symbol] = current_price
        
        # 检查是否需要通知
        if symbol in subscription_map:
            for subscriber in subscription_map[symbol]:
                if should_notify(subscriber, change_percentage):
                    notification_event = {
                        'user_id': subscriber['user_id'],
                        'symbol': symbol,
                        'change_percentage': change_percentage,
                        'timestamp': timestamp
                    }
                    producer.send('notifications', notification_event)
                    print(f"Notification Event Produced: {notification_event}")

        producer.flush()

if __name__ == "__main__":
    main()
```

### **3.4 实现通知服务（Kafka Consumer）**

该服务订阅 `notifications` 主题，消费通知事件并向相应的订阅者发送通知。

```python
# notifier.py
import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'notifications',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='notifier_group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

def send_notification(notification):
    user_id = notification['user_id']
    symbol = notification['symbol']
    change = notification['change_percentage']
    timestamp = notification['timestamp']
    
    change_type = '涨幅' if change >= 0 else '跌幅'
    message = (f"用户{user_id}，您好！股票{symbol}的{change_type}已达到"
               f"{abs(change):.2f}%。")
    # 这里可以集成邮件、短信或推送通知服务
    print(f"发送通知: {message}")

def main():
    for message in consumer:
        notification = message.value
        send_notification(notification)

if __name__ == "__main__":
    main()
```

### **3.5 订阅者管理和 `old_price` 存储**

为了实现更复杂的订阅管理和 `old_price` 的持久化，建议使用数据库来存储订阅者信息和股票价格。以下是一个使用 Redis 作为存储的示例：

```python
# storage.py
import redis
import json

# 连接 Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_subscribers():
    # 从 Redis 获取订阅者列表
    # 假设订阅者存储在键 'subscribers' 下，以 JSON 格式存储
    subscribers_json = redis_client.get('subscribers')
    if subscribers_json:
        return json.loads(subscribers_json)
    return []

def save_subscribers(subscribers):
    # 将订阅者列表保存到 Redis
    redis_client.set('subscribers', json.dumps(subscribers))

def get_old_price(symbol):
    price = redis_client.get(f'old_price:{symbol}')
    return float(price) if price else 0.0

def set_old_price(symbol, price):
    redis_client.set(f'old_price:{symbol}', price)
```

然后在 `price_processor.py` 中集成 Redis 存储：

```python
# price_processor.py
import json
from kafka import KafkaConsumer, KafkaProducer
import redis
from storage import get_subscribers, get_old_price, set_old_price

# 存储每个股票的上一周期价格
# 使用 Redis 替代本地字典
# 初始化 Redis 客户端
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

consumer = KafkaConsumer(
    'stock_prices',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='price_processor_group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def should_notify(subscriber, change_percentage):
    direction = subscriber.get('direction', 'both')
    threshold = subscriber.get('threshold', 0)
    if direction == 'up' and change_percentage >= threshold:
        return True
    elif direction == 'down' and change_percentage <= -threshold:
        return True
    elif direction == 'both' and abs(change_percentage) >= threshold:
        return True
    return False

def main():
    subscribers = get_subscribers()
    
    # 构建订阅者映射，按股票分组
    subscription_map = {}
    for sub in subscribers:
        symbol = sub['stock_symbol']
        if symbol not in subscription_map:
            subscription_map[symbol] = []
        subscription_map[symbol].append(sub)
    
    for message in consumer:
        data = message.value
        symbol = data['symbol']
        current_price = data['price']
        timestamp = data['timestamp']
        
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
                    notification_event = {
                        'user_id': subscriber['user_id'],
                        'symbol': symbol,
                        'change_percentage': change_percentage,
                        'timestamp': timestamp
                    }
                    producer.send('notifications', notification_event)
                    print(f"Notification Event Produced: {notification_event}")

        producer.flush()

if __name__ == "__main__":
    main()
```

### **3.6 使用 Kafka Streams（高级选项）**

如果需要更复杂的流处理逻辑，可以考虑使用 **Kafka Streams** 或 **ksqlDB**。这些工具提供了更高级的流处理能力，如状态管理、窗口计算等。

不过，对于大多数通知系统，简单的 Kafka Producer 和 Consumer 已经足够。

## **4. 示例运行步骤**

1. **启动 Kafka 和 ZooKeeper**：
   ```bash
   bin/zookeeper-server-start.sh config/zookeeper.properties
   bin/kafka-server-start.sh config/server.properties
   ```

2. **创建 Kafka 主题**：
   ```bash
   bin/kafka-topics.sh --create --topic stock_prices --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
   bin/kafka-topics.sh --create --topic notifications --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
   ```

3. **启动 Producer（发布股价更新）**：
   ```bash
   python producer.py
   ```

4. **启动 Price Processor（处理股价变动并生成通知事件）**：
   ```bash
   python price_processor.py
   ```

5. **启动 Notifier（消费通知事件并发送通知）**：
   ```bash
   python notifier.py
   ```

6. **监控系统**：
   - 您可以在控制台中观察到 Producer 发布的股价更新，Price Processor 处理后的通知事件，以及 Notifier 发送的通知消息。

## **5. 进一步优化与扩展**

### **5.1 使用数据库存储订阅者信息**

在生产环境中，订阅者信息应存储在持久化数据库中（如 PostgreSQL、MongoDB）。可以构建一个 API 服务，管理订阅者的 CRUD 操作，并在 Price Processor 中动态获取订阅者信息。

### **5.2 高可用性和扩展性**

- **增加 Kafka Broker**：提高系统的吞吐量和容错性。
- **增加 Consumer 实例**：通过增加 Consumer 实例到同一个 Consumer Group，实现水平扩展。
- **使用负载均衡**：在通知服务中使用负载均衡器，分发通知请求。

### **5.3 集成监控和日志**

- **监控工具**：使用 Prometheus 和 Grafana 监控 Kafka 集群和应用程序的性能。
- **日志管理**：集成 ELK（Elasticsearch、Logstash、Kibana）堆栈，集中管理和分析日志。

### **5.4 安全性**

- **认证与授权**：配置 Kafka 的 SASL/SSL，确保消息传输的安全性。
- **数据加密**：加密敏感数据，保护用户隐私。
- **访问控制**：限制不同服务和用户对 Kafka 主题的访问权限。

### **5.5 错误处理和重试机制**

- **错误处理**：在 Producer 和 Consumer 中实现错误处理逻辑，如重试机制、死信队列（Dead Letter Queue）。
- **消息幂等性**：确保消息处理的幂等性，避免重复通知。

### **5.6 使用 Schema Registry**

为了确保消息格式的一致性和向后兼容性，可以使用 **Confluent Schema Registry**，通过 Avro、Protobuf 等序列化格式管理消息模式。

## **6. 完整示例代码汇总**

以下是整合了 Kafka 和 Redis 存储的完整示例代码片段：

### **6.1 Producer（producer.py）**

```python
import json
import time
import random
from kafka import KafkaProducer

STOCK_SYMBOLS = ["AAPL", "GOOG", "TSLA"]

def get_stock_price(symbol):
    return round(random.uniform(100, 200), 2)

def main():
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    while True:
        for symbol in STOCK_SYMBOLS:
            price = get_stock_price(symbol)
            message = {
                'symbol': symbol,
                'price': price,
                'timestamp': time.time()
            }
            producer.send('stock_prices', message)
            print(f"Produced: {message}")
        producer.flush()
        time.sleep(5)

if __name__ == "__main__":
    main()
```

### **6.2 Price Processor（price_processor.py）**

```python
import json
from kafka import KafkaConsumer, KafkaProducer
import redis

def get_subscribers():
    # 从 Redis 获取订阅者列表
    subscribers_json = redis_client.get('subscribers')
    if subscribers_json:
        return json.loads(subscribers_json)
    return []

def save_subscribers(subscribers):
    # 将订阅者列表保存到 Redis
    redis_client.set('subscribers', json.dumps(subscribers))

def get_old_price(symbol):
    price = redis_client.get(f'old_price:{symbol}')
    return float(price) if price else 0.0

def set_old_price(symbol, price):
    redis_client.set(f'old_price:{symbol}', price)

redis_client = redis.Redis(host='localhost', port=6379, db=0)

consumer = KafkaConsumer(
    'stock_prices',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='price_processor_group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def should_notify(subscriber, change_percentage):
    direction = subscriber.get('direction', 'both')
    threshold = subscriber.get('threshold', 0)
    if direction == 'up' and change_percentage >= threshold:
        return True
    elif direction == 'down' and change_percentage <= -threshold:
        return True
    elif direction == 'both' and abs(change_percentage) >= threshold:
        return True
    return False

def main():
    subscribers = get_subscribers()
    
    if not subscribers:
        # 如果 Redis 中没有订阅者，初始化订阅者列表
        subscribers = [
            {'user_id': 1, 'stock_symbol': 'AAPL', 'threshold': 2, 'priority': 1, 'direction': 'up'},
            {'user_id': 2, 'stock_symbol': 'GOOG', 'threshold': 3, 'priority': 2, 'direction': 'down'},
            {'user_id': 3, 'stock_symbol': 'TSLA', 'threshold': 5, 'priority': 1, 'direction': 'both'},
        ]
        save_subscribers(subscribers)
    
    # 构建订阅者映射，按股票分组
    subscription_map = {}
    for sub in subscribers:
        symbol = sub['stock_symbol']
        if symbol not in subscription_map:
            subscription_map[symbol] = []
        subscription_map[symbol].append(sub)
    
    for message in consumer:
        data = message.value
        symbol = data['symbol']
        current_price = data['price']
        timestamp = data['timestamp']
        
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
                    notification_event = {
                        'user_id': subscriber['user_id'],
                        'symbol': symbol,
                        'change_percentage': change_percentage,
                        'timestamp': timestamp
                    }
                    producer.send('notifications', notification_event)
                    print(f"Notification Event Produced: {notification_event}")

        producer.flush()

if __name__ == "__main__":
    main()
```

### **6.3 Notifier（notifier.py）**

```python
import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'notifications',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='notifier_group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

def send_notification(notification):
    user_id = notification['user_id']
    symbol = notification['symbol']
    change = notification['change_percentage']
    timestamp = notification['timestamp']
    
    change_type = '涨幅' if change >= 0 else '跌幅'
    message = (f"用户{user_id}，您好！股票{symbol}的{change_type}已达到"
               f"{abs(change):.2f}%。")
    # 集成邮件、短信或推送通知服务
    print(f"发送通知: {message}")

def main():
    for message in consumer:
        notification = message.value
        send_notification(notification)

if __name__ == "__main__":
    main()
```

### **6.4 Storage 管理（storage.py）**

```python
import redis
import json

# 连接 Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_subscribers():
    subscribers_json = redis_client.get('subscribers')
    if subscribers_json:
        return json.loads(subscribers_json)
    return []

def save_subscribers(subscribers):
    redis_client.set('subscribers', json.dumps(subscribers))

def get_old_price(symbol):
    price = redis_client.get(f'old_price:{symbol}')
    return float(price) if price else 0.0

def set_old_price(symbol, price):
    redis_client.set(f'old_price:{symbol}', price)
```

## **7. 部署与运行**

1. **确保 Kafka 和 Redis 正在运行**：
   - Kafka Broker 和 ZooKeeper 已启动。
   - Redis 服务已启动。

2. **启动 Producer**：
   ```bash
   python producer.py
   ```

3. **启动 Price Processor**：
   ```bash
   python price_processor.py
   ```

4. **启动 Notifier**：
   ```bash
   python notifier.py
   ```

您应该会在控制台看到如下输出：

- **Producer**：发布的股价更新消息。
- **Price Processor**：接收到的股价变动和生成的通知事件。
- **Notifier**：发送给用户的通知消息。

## **8. 高级功能与优化**

### **8.1 动态订阅管理**

- **API 服务**：构建一个 RESTful API 服务，允许用户动态添加、更新和删除订阅。
- **实时更新**：Price Processor 可以实时从数据库或 Redis 中获取最新的订阅者信息，支持动态调整。

### **8.2 使用 Kafka Streams**

对于更复杂的流处理需求，可以使用 **Kafka Streams** 或 **ksqlDB**，实现更高级的逻辑，如聚合、窗口计算等。

### **8.3 消息序列化**

使用高效的序列化格式（如 Avro、Protobuf）与 **Schema Registry** 结合，提高消息传输效率和模式管理。

### **8.4 弹性伸缩**

- **容器化**：将各个组件容器化（如使用 Docker），方便部署和弹性伸缩。
- **编排工具**：使用 Kubernetes 等编排工具，管理服务的自动伸缩、故障恢复等。

### **8.5 性能监控与调优**

- **监控指标**：监控 Kafka 的延迟、吞吐量、消费者的消费速率等关键指标。
- **调优参数**：根据监控数据，调整 Kafka 的配置参数（如 Partition 数量、Consumer 数量）以优化性能。

## **9. 总结**

通过将 Apache Kafka 集成到您的股价涨跌幅通知系统中，您可以实现高效、可扩展和可靠的实时数据处理。Kafka 的分布式架构和强大的流处理能力，使其成为构建复杂实时应用的理想选择。结合 Redis 等存储解决方案，您可以进一步提升系统的性能和灵活性。

以下是本回答的关键要点：

- **Kafka Producer**：发布实时股价更新。
- **Kafka Consumer（Price Processor）**：处理股价变动，计算涨跌幅，生成通知事件。
- **Kafka Consumer（Notifier）**：消费通知事件，向用户发送通知。
- **Redis 存储**：管理订阅者信息和 `old_price`，确保数据持久化和快速访问。
- **系统扩展**：通过增加 Broker、Consumer 实例，实现系统的水平扩展和高可用性。
- **高级功能**：动态订阅管理、使用 Kafka Streams、消息序列化等，进一步优化和增强系统功能。

通过以上设计和实现，您可以构建一个强大且高效的股价涨跌幅通知系统，满足多客户、高并发和实时性的需求。







sudo apt install redis-server -y

sudo systemctl start redis

sudo systemctl status redis
