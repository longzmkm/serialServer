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

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)

is_rece = True


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
        ser.write(bytearray.fromhex(message))
        logger.debug("send the data:%s" % message)
        time.sleep(1)
        is_rece = True

    except Exception as e:
        logger.debug('>>' * 50)
        logger.debug(e)
        logger.debug('<<' * 50)


def mqtt_to_serial(client, userdata, message):
    msg = message.payload.decode('utf8')
    Vpsend(userdata, msg)


@async_call
def receive_mqtt(host, user_id, container_id, ser):
    topic = "{user_id}/{container_id}/+/up".format(user_id=user_id, container_id=container_id)
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
    container_id = os.environ.get('container')
    logger.debug('user_id:%s , container_id:%s' % (user_id, container_id))

    return user_id, container_id


def read_tty(host, user_id, container_id, ser):
    global is_rece
    topic = '{user_id}/{container_id}/serial/down'.format(user_id=user_id, container_id=container_id)

    while True:
        if is_rece and ser.in_waiting != 0:
            msg_recv = binascii.hexlify(ser.read(ser.in_waiting)).decode('utf-8')
            logger.debug('recv the data:%s' % msg_recv)
            client = mqtt.Client(client_id=generate_number())
            client.connect(host=host, port=1883)
            client.publish(topic=topic, payload=msg_recv)
            client.disconnect()
            logger.debug('send data to mqtt topic:%s , payload:%s' % (topic, msg_recv))


if __name__ == '__main__':
    # 获取MQTT 的数据

    host = '52.130.92.191'
    device = '/dev/ttyS10'
    rate = 9600

    # 1. 获取环境变量  组成topic
    logger.debug('1.组成topic')
    user_id, container_id = get_evn()
    logger.debug(u'当前USE_ID:%s, 容器ID:%s' % (user_id, container_id))
    # 2. 创建串口的 master 和 slave
    logger.debug('2.创建串口的连接')
    ser = create_serial_client(device, rate)

    # 3. 订阅数据  通过串口的形式 转发出去
    logger.debug('3. 订阅数据  通过串口的形式 转发出去')
    receive_mqtt(host, user_id, container_id, ser)

    # 4. 接收串口发送的数据 写入 topic
    read_tty(host, user_id, container_id, ser)
