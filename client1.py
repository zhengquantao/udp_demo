# 客户端

import socket
import struct
import os
import time
import threading

# 创建一个UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 服务器地址和端口
server_address = ('localhost', 10000)

# 要发送的文件名
filename = 'test.txt'

def send_heartbeat():
    while True:
        time.sleep(60)  # 每60秒发送一次心跳包
        sock.sendto(struct.pack('!H', 3), server_address)  # 心跳包类型为3

# 启动心跳线程
heartbeat_thread = threading.Thread(target=send_heartbeat)
heartbeat_thread.start()

# 发送初始化文件信息数据包
file_size = os.path.getsize(filename)
pkt_count = (file_size + 1023) // 1024
sock.sendto(struct.pack('!H50sQII', 0, filename.encode(), file_size, pkt_count, 1024), server_address)

# 等待服务器的响应
data, _ = sock.recvfrom(4096)
if struct.unpack('!H', data)[0] != 1:
    print("Failed to initialize file transfer.")
else:
    # 发送文件数据包
    with open(filename, 'rb') as f:
        for i in range(pkt_count):
            pkt_data = f.read(1024)
            sock.sendto(struct.pack('!HHQ1024s', 1, i, pkt_data), server_address)

    # 发送结束文件发送数据包
    sock.sendto(struct.pack('!H', 2), server_address)

    # 等待服务器的响应，如果有丢失的数据包，重新发送
    while True:
        data, _ = sock.recvfrom(4096)
        missing_pkts = struct.unpack('!H' + 'I'*((len(data)-2)//4), data)
        if missing_pkts[0] == 0:  # 没有丢失的数据包，结束发送
            break
        else:  # 有丢失的数据包，重新发送
            with open(filename, 'rb') as f:
                for i in missing_pkts[1:]:
                    f.seek(i*1024)
                    pkt_data = f.read(1024)
                    sock.sendto(struct.pack('!HHQ1024s', 1, i, pkt_data), server_address)
