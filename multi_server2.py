# 多线程
import socketserver
import struct


class UDPHandler(socketserver.BaseRequestHandler):
    file_info = {}
    data_pkts = {}
    retry_counter = {}

    def handle(self):
        data = self.request[0]
        sock = self.request[1]
        address = self.client_address

        pkt_type = struct.unpack('!H', data[:2])[0]
        if pkt_type == 0:  # 初始化文件信息数据包
            self.handle_init_pkt(data[2:], address, sock)
        elif pkt_type == 1:  # 文件数据包
            self.handle_data_pkt(data[2:], address)
        elif pkt_type == 2:  # 结束文件发送数据包
            self.handle_end_pkt(address, sock)

    def handle_init_pkt(self, data, address, sock):
        filename, file_size, pkt_count, pkt_size = struct.unpack('!50sQII', data)
        filename = filename.strip(b'\x00').decode()
        self.file_info[address] = (filename, file_size, pkt_count, pkt_size)
        self.data_pkts[address] = [b''] * pkt_count
        self.retry_counter[address] = 0
        self.send_response(sock, address)

    def handle_data_pkt(self, data, address):
        pkt_id, pkt_data = struct.unpack('!HQ1024s', data)
        self.data_pkts[address][pkt_id] = pkt_data

    def handle_end_pkt(self, address, sock):
        missing_pkts = [i for i, pkt in enumerate(self.data_pkts[address]) if not pkt]
        if missing_pkts:
            if self.retry_counter[address] < 5:
                self.send_missing_pkts(sock, address, missing_pkts)
                self.retry_counter[address] += 1
            else:
                print(f"Give up receiving file from {address} due to too many lost packets.")
                del self.file_info[address]
                del self.data_pkts[address]
                del self.retry_counter[address]
        else:
            self.save_file(address)

    def send_response(self, sock, address):
        sock.sendto(struct.pack('!H', 1), address)

    def send_missing_pkts(self, sock, address, missing_pkts):
        sock.sendto(struct.pack('!H' + 'I'*len(missing_pkts), *(len(missing_pkts), *missing_pkts)), address)

    def save_file(self, address):
        with open(self.file_info[address][0], 'wb') as f:
            for pkt in self.data_pkts[address]:
                f.write(pkt)
        del self.file_info[address]
        del self.data_pkts[address]
        del self.retry_counter[address]


if __name__ == "__main__":
    server = socketserver.UDPServer(('localhost', 10000), UDPHandler)
    server.serve_forever()
