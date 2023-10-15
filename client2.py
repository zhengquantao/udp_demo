# 客户端

import socket
import struct
import os
import time
import threading


class UDPClient:
    def __init__(self, server_address, filename):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = server_address
        self.filename = filename

    def send_heartbeat(self):
        while True:
            time.sleep(60)  # 每60秒发送一次心跳包
            self.sock.sendto(struct.pack('!H', 3), self.server_address)  # 心跳包类型为3

    def send_file(self):
        # 启动心跳线程
        heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        heartbeat_thread.start()

        # 发送初始化文件信息数据包
        file_size = os.path.getsize(self.filename)
        pkt_count = (file_size + 1023) // 1024
        self.sock.sendto(struct.pack('!H50sQII', 0, self.filename.encode(), file_size, pkt_count, 1024), self.server_address)

        # 等待服务器的响应
        data, _ = self.sock.recvfrom(4096)
        if struct.unpack('!H', data)[0] != 1:
            print("Failed to initialize file transfer.")
            return

        # 发送文件数据包
        with open(self.filename, 'rb') as f:
            for i in range(pkt_count):
                pkt_data = f.read(1024)
                self.sock.sendto(struct.pack('!HHQ1024s', 1, i, pkt_data), self.server_address)

        # 发送结束文件发送数据包
        self.sock.sendto(struct.pack('!H', 2), self.server_address)

        # 等待服务器的响应，如果有丢失的数据包，重新发送
        while True:
            data, _ = self.sock.recvfrom(4096)
            missing_pkts = struct.unpack('!H' + 'I'*((len(data)-2)//4), data)
            if missing_pkts[0] == 0:  # 没有丢失的数据包，结束发送
                break
            else:  # 有丢失的数据包，重新发送
                with open(self.filename, 'rb') as f:
                    for i in missing_pkts[1:]:
                        f.seek(i*1024)
                        pkt_data = f.read(1024)
                        self.sock.sendto(struct.pack('!HHQ1024s', 1, i, pkt_data), self.server_address)


if __name__ == "__main__":
    client = UDPClient(('localhost', 10000), 'test.txt')
    client.send_file()
