import socket
import threading
import os
import time
from datetime import datetime

# Konfigurasi Jaringan
#PROXY
HOST = '0.0.0.0'  # Proxy akan mendengarkan pada semua interface
PROXY_PORT = 8085      # Port tempat Proxy berjalan

# SERVER
SERVER_IP = '10.130.65.12'  # IP Web Server tujuan
SERVER_PORT = 8000
SERVER_UDP_PORT = 9000       # Port tujuan (Web Server)
CACHE_DIR = 'cache'

# Membuat folder cache jika belum ada
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_timestamp():
    """Fungsi bantuan untuk log waktu respons"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def handle_client(client_socket, client_address):
    """Menangani permintaan dari Client, memproses Cache, dan Forwarding"""
    start_time = time.time()
    try:
        # 1. Menerima request dari Client
        request = client_socket.recv(4096)
        if not request:
            client_socket.close()
            return

        # Parsing URL dari HTTP Request
        request_decoded = request.decode('utf-8', errors='ignore')
        headers = request_decoded.split('\n')
        if len(headers) > 0 and len(headers[0].split()) > 1:
            url = headers[0].split()[1]
        else:
            url = '/'
        
        if url == '/':
            url = '/index.html'

        # Format nama file untuk disimpan di cache (misal: _index.html)
        cache_filename = url.replace('/', '_')
        cache_filepath = os.path.join(CACHE_DIR, cache_filename)

        # 2. LOGIKA CACHING
        if os.path.exists(cache_filepath):
            # --- CACHE HIT ---
            # Mengirim respons langsung dari file cache tanpa menghubungi server
            with open(cache_filepath, 'rb') as f:
                response = f.read()
            client_socket.sendall(response)
            
            response_time = (time.time() - start_time) * 1000
            response_size = len(response) # Menghitung ukuran data
            
            # Menambahkan Ukuran Data ke dalam Log
            print(f"[PROXY LOG] {get_timestamp()} | IP: {client_address[0]} | Ukuran Data: {response_size} bytes | Status: HIT | Waktu: {response_time:.2f}ms")
        else:
            # --- CACHE MISS (FORWARDING) ---
            # Buka koneksi ke Web Server tujuan
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(2.0) # Batas waktu tunggu (Timeout)
            
            try:
                # 1. FASE KONEKSI (Jika gagal/timeout di sini, jadikan 502)
                try:
                    server_socket.connect((SERVER_IP, SERVER_PORT))
                except Exception as e:
                    # Menggagalkan proses secara paksa agar masuk ke blok Exception 502 di bawah
                    raise ConnectionError(f"Gagal koneksi ke server: {e}")

                # 2. FASE REQUEST & RESPONS (Jika timeout di sini, jadikan 504)
                server_socket.sendall(request)
                
                # Menerima respons dari Web Server
                response = b""
                while True:
                    data = server_socket.recv(4096)
                    if len(data) > 0:
                        response += data
                    else:
                        break
                
                # Simpan respons ke folder cache lokal
                if response:
                    with open(cache_filepath, 'wb') as f:
                        f.write(response)
                    
                    # Teruskan kembali ke Client
                    client_socket.sendall(response)
                    
                    response_time = (time.time() - start_time) * 1000
                    response_size = len(response) # Menghitung ukuran data
                    
                    # Menambahkan Ukuran Data ke dalam Log
                    print(f"[PROXY LOG] {get_timestamp()} | IP: {client_address[0]} | Ukuran Data: {response_size} bytes | Status: MISS | Waktu: {response_time:.2f}ms")
            
            except socket.timeout:
                # [KONDISI 504] - Server sudah nyambung, tapi kelamaan merespons data (Timeout)
                error_msg = "HTTP/1.1 504 Gateway Timeout\r\nContent-Type: text/html\r\n\r\n<html><body><h1>504 Gateway Timeout</h1><p>Server tidak merespons dalam batas waktu.</p></body></html>"
                response_bytes = error_msg.encode('utf-8')
                client_socket.sendall(response_bytes)
                
                response_time = (time.time() - start_time) * 1000
                print(f"[PROXY ERROR] {get_timestamp()} | IP: {client_address[0]} | Ukuran Data: {len(response_bytes)} bytes | Status: 504 Timeout | Waktu: {response_time:.2f}ms")
            
            except Exception as e:
                # [KONDISI 502] - Server tujuan mati total, tidak bisa dijangkau, atau menolak koneksi
                error_msg = "HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/html\r\n\r\n<html><body><h1>502 Bad Gateway</h1><p>Server tujuan mati atau menolak koneksi.</p></body></html>"
                response_bytes = error_msg.encode('utf-8')
                client_socket.sendall(response_bytes)
                
                response_time = (time.time() - start_time) * 1000
                print(f"[PROXY ERROR] {get_timestamp()} | IP: {client_address[0]} | Ukuran Data: {len(response_bytes)} bytes | Status: 502 Gateway | Waktu: {response_time:.2f}ms | Detail: {e}")
            
            finally:
                server_socket.close()

    except Exception as e:
        print(f"[PROXY EXCEPTION] {e}")
    finally:
        client_socket.close()

def start_proxy():
    """Menjalankan Proxy Server TCP"""
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind((HOST, PROXY_PORT))
    proxy_socket.listen(10)
    print(f"[*] Proxy Server (TCP) listening on {HOST}:{PROXY_PORT}")

    while True:
        client_socket, client_address = proxy_socket.accept()
        # Menggunakan threading agar bisa menangani banyak client bersamaan
        proxy_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        proxy_thread.start()

if __name__ == '__main__':
    tcp_thread = threading.Thread(target=start_proxy)
    
    tcp_thread.start()