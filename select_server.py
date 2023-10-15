# select IO多路复用服务端
import socket
import select
import struct


class UDPServer:
    def __init__(self, address):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(address)
        self.file_info = {}
        self.data_pkts = {}

    def run(self):
        read_list = [self.sock]
        while True:
            readable, _, _ = select.select(read_list, [], [])
            for s in readable:
                if s is self.sock:
                    data, address = self.sock.recvfrom(4096)
                    pkt_type = struct.unpack('!H', data[:2])[0]
                    if pkt_type == 0:  # 初始化文件信息数据包
                        self.handle_init_pkt(data[2:], address)
                    elif pkt_type == 1:  # 文件数据包
                        self.handle_data_pkt(data[2:], address)
                    elif pkt_type == 2:  # 结束文件发送数据包
                        self.handle_end_pkt(address)

    def handle_init_pkt(self, data, address):
        filename, file_size, pkt_count, pkt_size = struct.unpack('!50sQII', data)
        self.file_info[address] = (filename.strip(b'\x00').decode(), file_size, pkt_count, pkt_size)
        self.data_pkts[address] = [b''] * pkt_count
        # 发送响应给客户端
        self.sock.sendto(struct.pack('!H', 1), address)

    def handle_data_pkt(self, data, address):
        pkt_id, pkt_data = struct.unpack('!HQ1024s', data)
        self.data_pkts[address][pkt_id] = pkt_data

    def handle_end_pkt(self, address):
        missing_pkts = [i for i, pkt in enumerate(self.data_pkts[address]) if not pkt]
        if missing_pkts:
            # 发送缺失的数据包编号给客户端
            self.sock.sendto(struct.pack('!H' + 'I'*len(missing_pkts), *(len(missing_pkts), *missing_pkts)), address)
        else:
            # 所有数据包都已接收，保存文件
            with open(self.file_info[address][0], 'wb') as f:
                for pkt in self.data_pkts[address]:
                    f.write(pkt)
            del self.file_info[address]
            del self.data_pkts[address]


if __name__ == "__main__":
    server = UDPServer(('localhost', 10000))
    server.run()
