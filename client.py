import csv
import socket
import sys
import time
import statistics

# Konfigurasi Jaringan
PROXY_IP = '10.130.66.43'  # Masukin IP Kamu Disi yang Sebagai Proxy Lewat Ipconfig
PROXY_PORT = 8085
# PROXY_UDP_PORT = 9090
SERVER_IP = '10.130.65.12'  # IP Web Server 
SERVER_UDP_PORT = 9000

def run_tcp_mode():
    """Mengirim permintaan HTTP GET ke Proxy Server"""
    print(f"[*] Menjalankan Client dalam Mode TCP (HTTP)...")
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Client tidak boleh terhubung langsung ke Server 8000, wajib ke Proxy 8080
        tcp_socket.connect((PROXY_IP, PROXY_PORT))
        
        # Format request HTTP standar
        request = "GET /index.html HTTP/1.1\r\n"
        request += f"Host: {PROXY_IP}\r\n"
        request += "Connection: close\r\n\r\n"
        
        tcp_socket.sendall(request.encode('utf-8'))
        
        # Menerima respons secara utuh
        response = b""
        while True:
            data = tcp_socket.recv(4096)
            if not data:
                break
            response += data
            
        print("\n--- RESPONSE DARI PROXY ---")
        print(response.decode('utf-8', errors='ignore'))
        print("---------------------------\n")
        
    except Exception as e:
        print(f"[TCP CLIENT ERROR] Gagal terhubung ke Proxy: {e}")
    finally:
        tcp_socket.close()

def run_udp_mode():
    """Mengirim paket Ping UDP dan menghitung metrik QoS"""
    print(f"[*] Menjalankan Client dalam Mode UDP (QoS Ping)...")
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Aturan Wajib: Timeout per paket maksimal 1 detik
    udp_socket.settimeout(1.0) 
    
    num_pings = 10
    rtt_list = []
    lost_packets = 0
    total_payload_bytes = 0
    
    start_test_time = time.time()
    
    for i in range(1, num_pings + 1):
        send_time = time.time()
        # Format payload wajib: "Ping <seq> <timestamp>"
        payload = f"Ping {i} {send_time}" 
        
        try:
            udp_socket.sendto(payload.encode('utf-8'), (SERVER_IP, SERVER_UDP_PORT))
            data, server = udp_socket.recvfrom(1024)
            recv_time = time.time()
            
            rtt = (recv_time - send_time) * 1000 # Konversi ke ms
            rtt_list.append(rtt)
            total_payload_bytes += len(data)
            
            print(f"Reply dari {server[0]}: seq={i} time={rtt:.2f} ms")
            
        except socket.timeout:
            lost_packets += 1
            print(f"Request timed out (seq={i})")
            
    end_test_time = time.time()
    udp_socket.close()
    
    # --- PERHITUNGAN STATISTIK QoS ---
    print("\n--- STATISTIK PENGUJIAN QoS ---")
    if len(rtt_list) > 0:
        min_rtt = min(rtt_list)
        max_rtt = max(rtt_list)
        avg_rtt = sum(rtt_list) / len(rtt_list)
        print(f"Latency (RTT) : Min = {min_rtt:.2f} ms | Avg = {avg_rtt:.2f} ms | Max = {max_rtt:.2f} ms")
    else:
        print("Latency (RTT) : Pengukuran gagal (semua paket loss)")

    # Menghitung Packet Loss (%)
    loss_percent = (lost_packets / num_pings) * 100
    print(f"Packet Loss   : {loss_percent:.2f}% ({lost_packets}/{num_pings} paket hilang)")

    # Menghitung Jitter menggunakan standar deviasi selisih RTT berturut-turut
    jitter = 0.0
    if len(rtt_list) > 1:
        rtt_diffs = [abs(rtt_list[i] - rtt_list[i-1]) for i in range(1, len(rtt_list))]
        if len(rtt_diffs) > 1:
            jitter = statistics.stdev(rtt_diffs)
        else:
            jitter = rtt_diffs[0]
    print(f"Jitter        : {jitter:.2f} ms")

    # Menghitung Throughput (kbps) = (Total Payload dalam bit) / (Durasi Pengujian) / 1000
    test_duration = end_test_time - start_test_time
    throughput_kbps = ((total_payload_bytes * 8) / test_duration) / 1000
    print(f"Throughput    : {throughput_kbps:.2f} kbps")
    print("-------------------------------\n")

    
    csv_filename = "qos_result.csv"
    try:
        with open(csv_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Menulis Header
            writer.writerow(["Metrik QoS", "Nilai", "Satuan"])
            # Menulis Data
            if len(rtt_list) > 0:
                writer.writerow(["Min RTT", f"{min_rtt:.2f}", "ms"])
                writer.writerow(["Avg RTT", f"{avg_rtt:.2f}", "ms"])
                writer.writerow(["Max RTT", f"{max_rtt:.2f}", "ms"])
            else:
                writer.writerow(["Min/Avg/Max RTT", "Pengukuran Gagal", "-"])
                
            writer.writerow(["Packet Loss", f"{loss_percent:.2f}", "%"])
            writer.writerow(["Jitter", f"{jitter:.2f}", "ms"])
            writer.writerow(["Throughput", f"{throughput_kbps:.2f}", "kbps"])
            
        print(f"[*] BERHASIL: Statistik QoS telah disimpan ke dalam file '{csv_filename}'")
    except Exception as e:
        print(f"[!] GAGAL: Tidak dapat menyimpan file CSV. Error: {e}")

if __name__ == '__main__':
    # Memilih mode berdasarkan argumen command line
    if len(sys.argv) < 3 or sys.argv[1] != '-mode':
        print("Penggunaan: python client.py -mode tcp ATAU python client.py -mode udp")
        sys.exit(1)

    mode = sys.argv[2].lower()
    if mode == 'tcp':
        run_tcp_mode()
    elif mode == 'udp':
        run_udp_mode()
    else:
        print("Error: Mode tidak dikenali. Gunakan 'tcp' atau 'udp'.")