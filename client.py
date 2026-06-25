import csv
import os
import socket
import subprocess
import sys
import time
import statistics

# Konfigurasi Jaringan
# Gunakan 127.0.0.1 jika client, proxy, dan webserver dijalankan di laptop yang sama.
# Jika memakai beberapa laptop, ganti IP ini ke IP laptop proxy/server pada jaringan yang sama.
PROXY_IP = '172.20.10.3'
PROXY_PORT = 8085
# PROXY_UDP_PORT = 9090
SERVER_IP = '172.20.10.3'
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

def run_multi_client_mode(num_clients=5):
    """Menjalankan beberapa client TCP secara bersamaan untuk stress testing."""
    print(f"[*] Menjalankan {num_clients} Client TCP secara bersamaan...")
    processes = []
    start_time = time.time()
    client_script = os.path.abspath(__file__)

    for i in range(num_clients):
        print(f" -> Spawn Client-{i+1}")
        p = subprocess.Popen([sys.executable, client_script, "tcp"])
        processes.append(p)

    for p in processes:
        p.wait()

    end_time = time.time()
    print(f"\n[*] Semua {num_clients} client selesai dieksekusi dalam {(end_time - start_time):.2f} detik.")

def show_menu():
    print("=== MENU CLIENT ===")
    print("1. TCP")
    print("2. UDP")
    print("3. Multi Client")
    print("===================")

def run_selected_option(option):
    option = option.strip().lower()

    if option in ("1", "tcp"):
        run_tcp_mode()
    elif option in ("2", "udp"):
        run_udp_mode()
    elif option in ("3", "multi", "multi-client", "multi_client"):
        run_multi_client_mode()
    else:
        print("Error: Opsi tidak dikenali. Pilih 1/TCP, 2/UDP, atau 3/Multi Client.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_selected_option(sys.argv[1])
    else:
        show_menu()
        selected_option = input("Pilih opsi (1/2/3): ")
        run_selected_option(selected_option)
