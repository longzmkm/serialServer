import serial
import sys
import pty
import os
import random
import string
import time
import threading
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe

is_rece = True


def async_call(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()

    return wrapper


def generate_number():
    return ''.join(random.sample(string.ascii_letters + string.digits, 16))


def Vpsend(slaveName, master, message):
    try:
        is_rece = False
        os.write(master, bytes(message, 'utf-8'))
        print("send the data:%s" % message)
        time.sleep(1)
        is_rece = True

    except Exception as e:
        print('>>' * 50)
        print(e)
        print('<<' * 50)


# create only one virtual port
def mkpty():
    # make pair of pseudo tty
    master, slave = pty.openpty()
    slaveName = os.ttyname(slave)

    return master, slave


def mqtt_to_serial(client, userdata, message):
    msg = str(message.payload, encoding='utf-8')
    Vpsend(userdata[1], userdata[0], msg)


@async_call
def receive_mqtt(host, user_id, container_id, master, slave):
    print("{user_id}/{container_id}/+/up".format(user_id=user_id, container_id=container_id))
    subscribe.callback(mqtt_to_serial,
                       '2/c556e7e3ccb4/ssssss/up',
                       hostname=host, port=1883,
                       userdata=[master, slave],
                       client_id=generate_number(),
                       keepalive=60)


def get_evn():
    # 获取 环境变量数据
    user_id = '2'
    container_id = 'c556e7e3ccb4'

    return user_id, container_id


@async_call
def read_tty(slave, client, user_id, container_id):
    topic = "{user_id}/{container_id}/aaaaa/down".format(user_id=user_id, container_id=container_id)

    while True:
        if is_rece:
            msg_recv = os.read(slave, 200)
            print('recv the data:%s' % msg_recv)
            client.publish(topic=topic, payload=msg_recv, qos=1)
            print('send data to mqtt topic:%s , payload:%s' % (topic, msg_recv))


if __name__ == '__main__':
    # 获取MQTT 的数据

    host = '52.130.92.191'

    client = mqtt.Client(client_id=generate_number())
    client.connect(host=host, port=1883, keepalive=60)

    # 1. 获取环境变量  组成topic
    print('1.组成topic')
    user_id, container_id = get_evn()

    # 2. 创建串口的 master 和 slave

    print('2.创建串口的 master 和 slave')
    master, slave = mkpty()

    # 3. 订阅数据  通过串口的形式 转发出去
    print('3. 订阅数据  通过串口的形式 转发出去')
    receive_mqtt(host, user_id, container_id, master, slave)

    # 4. 接收串口发送的数据 写入 topic
    read_tty(master, client, user_id, container_id)
