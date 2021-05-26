import os
import serial
import random
import string
import time
import threading
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import logging
import binascii
from redis import ConnectionPool, Redis

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)

is_rece = True

pool = ConnectionPool(host="serial-redis", port=6379, decode_responses=True)
redis_client = Redis(connection_pool=pool)


def async_call(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()

    return wrapper


def generate_number():
    return ''.join(random.sample(string.ascii_letters + string.digits, 16))


def Vpsend(ser, message):
    global is_rece
    try:
        is_rece = False
        if ser.in_waiting:
            ser.read(ser.in_waiting)
            logger.debug("clean buffer")
        ser.write(bytearray.fromhex(message))
        # logger.debug("send to host:%s" % message)
        time.sleep(0.006)
        is_rece = True

    except Exception as e:
        logger.debug('>>' * 50)
        logger.debug(e)
        logger.debug('<<' * 50)


def mqtt_to_serial(client, userdata, message):
    msg = message.payload.decode('utf8')
    logger.debug("cmd:%s , result:%s" % (message.topic.split('/')[-1], msg))
    redis_client.set(message.topic.split('/')[-1], msg, 6)
    Vpsend(userdata, msg)


@async_call
def receive_mqtt(host, user_id, ser):
    # def receive_mqtt(host, user_id, container_id, ser):
    topic = "{user_id}/modbusRtu/up/#".format(user_id=user_id)
    logger.debug(topic)
    subscribe.callback(mqtt_to_serial,
                       topic,
                       hostname=host, port=1883,
                       userdata=ser,
                       client_id=generate_number(),
                       keepalive=60)


def create_serial_client(device, rate):
    ser = serial.Serial(device, rate)
    return ser


def get_evn():
    # 获取 环境变量数据
    user_id = os.environ.get('userid')
    # container_id = os.environ.get('container')
    # logger.debug('user_id:%s , container_id:%s' % (user_id, container_id))
    logger.debug('user_id:%s' % user_id)

    # return user_id, container_id
    return user_id


def calc_crc(string):
    data = bytearray.fromhex(string)
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for i in range(8):
            if ((crc & 1) != 0):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return hex(((crc & 0xff) << 8) + (crc >> 8))


def get_data(data):
    pos = 4

    while pos <= len(data):
        crc = calc_crc(data[0:pos])

        if crc[2:6] == data[pos:pos + 4]:
            break
        pos += 2
    return data[0:pos + 4]


def read_tty(host, user_id, ser):
    # def read_tty(host, user_id, container_id, ser):
    global is_rece
    topic = '{user_id}/modbusRtu/down'.format(user_id=user_id)
    # topic = '{user_id}/{container_id}/modbusRtu/down'.format(user_id=user_id, container_id=container_id)

    while True:
        time.sleep(0.005)
        if is_rece and ser.in_waiting != 0:
            try:
                recv_data = binascii.hexlify(ser.read(ser.in_waiting)).decode('utf-8')
                msg_recv = get_data(recv_data)
                logger.debug('recv the data:%s' % recv_data)
                client = mqtt.Client(client_id=generate_number())
                client.connect(host=host, port=1883)
                client.publish(topic=topic, payload=msg_recv)
                if len(msg_recv) < len(recv_data):
                    time.sleep(0.01)
                    client.publish(topic=topic, payload=recv_data[len(msg_recv):])
                client.disconnect()
                logger.debug('send data to mqtt topic:%s , payload:%s' % (topic, recv_data))
            except Exception as e:
                logger.debug(e)
                continue


if __name__ == '__main__':
    # 获取MQTT 的数据

    host = 'mq.nlecloud.com'
    device = '/dev/ttyS10'
    rate = 9600

    # 1. 获取环境变量  组成topic
    logger.debug('1.组成topic')
    user_id = get_evn()
    # user_id, container_id = get_evn()
    # logger.debug(u'当前USE_ID:%s, 容器ID:%s' % (user_id, container_id))
    logger.debug(u'当前USE_ID:%s' % user_id)
    # 2. 创建串口的 master 和 slave
    logger.debug('2.创建串口的连接')
    ser = create_serial_client(device, rate)

    # 3. 订阅数据  通过串口的形式 转发出去
    logger.debug('3. 订阅数据  通过串口的形式 转发出去')
    receive_mqtt(host, user_id, ser)
    # receive_mqtt(host, user_id, container_id, ser)

    # 4. 接收串口发送的数据 写入 topic
    read_tty(host, user_id, ser)
    # read_tty(host, user_id, container_id, ser)
