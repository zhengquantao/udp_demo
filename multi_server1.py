# 多线程服务端

import socket
import struct
import threading

# 创建一个UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 绑定到一个地址和端口
server_address = ('localhost', 10000)
sock.bind(server_address)

# 存储文件信息和数据包
file_info = {}
data_pkts = {}


def handle_client(address):
    while True:
        data, addr = sock.recvfrom(4096)
        if addr == address:
            # 解析数据包类型
            pkt_type = struct.unpack('!H', data[:2])[0]

            if pkt_type == 0:  # 初始化文件信息数据包
                filename, file_size, pkt_count, pkt_size = struct.unpack('!50sQII', data[2:])
                file_info[address] = (filename.strip(b'\x00').decode(), file_size, pkt_count, pkt_size)
                data_pkts[address] = [b''] * pkt_count
                # 发送响应给客户端
                sock.sendto(struct.pack('!H', 1), address)
            elif pkt_type == 1:  # 文件数据包
                pkt_id, pkt_data = struct.unpack('!HQ1024s', data[2:])
                data_pkts[address][pkt_id] = pkt_data
            elif pkt_type == 2:  # 结束文件发送数据包
                missing_pkts = [i for i, pkt in enumerate(data_pkts[address]) if not pkt]
                if missing_pkts:
                    # 发送缺失的数据包编号给客户端
                    sock.sendto(struct.pack('!H' + 'I' * len(missing_pkts), *(len(missing_pkts), *missing_pkts)),
                                address)
                else:
                    # 所有数据包都已接收，保存文件
                    with open(file_info[address][0], 'wb') as f:
                        for pkt in data_pkts[address]:
                            f.write(pkt)
                    del file_info[address]
                    del data_pkts[address]
                    break


while True:
    data, address = sock.recvfrom(4096)
    threading.Thread(target=handle_client, args=(address,)).start()
