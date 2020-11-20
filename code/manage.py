import serial
import random
import string
import time
import threading
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
import logging

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
    try:
        is_rece = False
        ser.write(bytes(message, 'utf-8'))
        logger.debug("send the data:%s" % message)
        time.sleep(1)
        is_rece = True

    except Exception as e:
        logger.debug('>>' * 50)
        logger.debug(e)
        logger.debug('<<' * 50)


def mqtt_to_serial(client, userdata, message):
    msg = str(message.payload, encoding='utf-8')
    Vpsend(userdata, msg)


@async_call
def receive_mqtt(host, user_id, container_id, ser):
    logger.debug("{user_id}/{container_id}/+/up".format(user_id=user_id, container_id=container_id))
    subscribe.callback(mqtt_to_serial,
                       '2/c556e7e3ccb4/ssssss/up',
                       hostname=host, port=1883,
                       userdata=ser,
                       client_id=generate_number(),
                       keepalive=60)


def create_serial_client(device, rate):
    ser = serial.Serial('/dev/ttys003', 9600)
    return ser


def get_evn():
    # 获取 环境变量数据
    user_id = '2'
    container_id = 'c556e7e3ccb4'

    return user_id, container_id


@async_call
def read_tty(ser, client, user_id, container_id):
    topic = "{user_id}/{container_id}/aaaaa/down".format(user_id=user_id, container_id=container_id)

    while True:
        if is_rece and ser.in_waiting != 0:
            msg_recv = ser.read(ser.in_waiting)
            logger.debug('recv the data:%s' % msg_recv)
            client.publish(topic=topic, payload=msg_recv, qos=1)
            logger.debug('send data to mqtt topic:%s , payload:%s' % (topic, msg_recv))


if __name__ == '__main__':
    # 获取MQTT 的数据

    host = '52.130.92.191'
    device = '/dev/ttyS1'
    rate = 9600

    client = mqtt.Client(client_id=generate_number())
    client.connect(host=host, port=1883, keepalive=60)

    # 1. 获取环境变量  组成topic
    logger.debug('1.组成topic')
    user_id, container_id = get_evn()

    # 2. 创建串口的 master 和 slave
    logger.debug('2.创建串口的连接')
    ser = create_serial_client(device, rate)

    # 3. 订阅数据  通过串口的形式 转发出去
    logger.debug('3. 订阅数据  通过串口的形式 转发出去')
    receive_mqtt(host, user_id, container_id, ser)

    # 4. 接收串口发送的数据 写入 topic
    read_tty(ser, client, user_id, container_id)
