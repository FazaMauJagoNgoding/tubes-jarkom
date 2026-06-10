import socket
import threading
import os
import time
from datetime import datetime

# HOST diatur ke 0.0.0.0 agar bisa menerima request dari IP WiFi teman-teman Anda
HOST = '0.0.0.0' 
TCP_PORT = 8000
UDP_PORT = 9000

# FIREWALL
ALLOWED_PROXY_IP = '10.130.66.43' # IP Proxy yang diizinkan untuk mengakses server TCP


def get_timestamp():
    """Fungsi bantuan untuk mendapatkan waktu saat ini"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def handle_tcp_client(client_socket, client_address):
    """Menangani permintaan HTTP GET berbasis TCP"""
    # Catat waktu mulai saat koneksi mulai diproses
    start_time = time.time()
    
    try:
        request = client_socket.recv(1024).decode('utf-8')
        if not request:
            client_socket.close()
            return

        # Parsing HTTP Request
        headers = request.split('\n')
        if len(headers) > 0 and len(headers[0].split()) > 1:
            filename = headers[0].split()[1]
        else:
            filename = '/'
        
        # Default ke index.html jika meminta root '/'
        if filename == '/':
            filename = '/index.html'
            
        # ==============================================================================
        # [PENANDA ERROR 500]
        # CARA: Tambahkan tanda '#' di awal baris di bawah ini untuk menonaktifkannya.
        # Efek: Program akan kehilangan variabel dan langsung memicu 500 Internal Server Error.
        # ==============================================================================
        filepath = filename.lstrip('/')

        try:
            # --- PENGECEKAN TIPE KONTEN BERDASARKAN EKSTENSI FILE ---
            if filepath.endswith('.css'):
                content_type = 'text/css'
            elif filepath.endswith('.js'):
                content_type = 'application/javascript'
            elif filepath.endswith('.png'):
                content_type = 'image/png'
            elif filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filepath.endswith('.mp4'):
                content_type = 'video/mp4'
            else:
                content_type = 'text/html'
            # --------------------------------------------------------

            # Skenario Berhasil: 200 OK
            with open(filepath, 'rb') as file:
                content = file.read() 
            
            header = 'HTTP/1.1 200 OK\r\n'
            if 'text' in content_type:
                header += f'Content-Type: {content_type}; charset=utf-8\r\n'
            else:
                header += f'Content-Type: {content_type}\r\n'
                
            file_size = len(content) # Dapatkan ukuran file dalam bytes
            header += f'Content-Length: {file_size}\r\n'
            header += '\r\n'
            
            response = header.encode('utf-8') + content
            
            # ==============================================================================
            # [PENANDA ERROR 504]
            # CARA: Hapus tanda '#' pada awal baris 'time.sleep(3)' di bawah ini.
            # Efek: Server akan delay 3 detik, membuat Proxy kehabisan waktu memicu 504 Timeout.
            # ==============================================================================
            #time.sleep(3)
            
            client_socket.sendall(response)
            
            # Hitung total waktu proses dalam milidetik (ms)
            process_time = (time.time() - start_time) * 1000
            
            # Cetak log dengan Ukuran dan Waktu Proses
            print(f"[TCP LOG] {get_timestamp()} | IP: {client_address[0]} | 200 OK | Jalur: {filename} | Ukuran: {file_size} bytes | Waktu: {process_time:.2f} ms")
            
        except FileNotFoundError:
            # Skenario Gagal: 404 Not Found
            error_msg = "<html><body><h1>404 Not Found</h1><p>Berkas tidak ditemukan.</p></body></html>"
            file_size = len(error_msg)
            
            response = 'HTTP/1.1 404 Not Found\r\n'
            response += 'Content-Type: text/html; charset=utf-8\r\n'
            response += f'Content-Length: {file_size}\r\n'
            response += '\r\n'
            response += error_msg
            
            client_socket.sendall(response.encode('utf-8'))
            
            process_time = (time.time() - start_time) * 1000
            print(f"[TCP LOG] {get_timestamp()} | IP: {client_address[0]} | 404 Not Found | Jalur: {filename} | Ukuran: {file_size} bytes | Waktu: {process_time:.2f} ms")

    except Exception as e:
        # Skenario Gagal: 500 Internal Server Error
        error_msg = "<html><body><h1>500 Internal Server Error</h1></body></html>"
        file_size = len(error_msg)
        
        response = 'HTTP/1.1 500 Internal Server Error\r\n'
        response += 'Content-Type: text/html; charset=utf-8\r\n'
        response += f'Content-Length: {file_size}\r\n'
        response += '\r\n'
        response += error_msg
        client_socket.sendall(response.encode('utf-8'))
        
        process_time = (time.time() - start_time) * 1000
        print(f"[TCP ERROR] {get_timestamp()} | IP: {client_address[0]} | 500 Internal Server Error | Detail: {e} | Ukuran: {file_size} bytes | Waktu: {process_time:.2f} ms")
        
    finally:
        client_socket.close()

def start_tcp_server():
    """Menjalankan server TCP (HTTP)"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, TCP_PORT))
    server_socket.listen(5)
    print(f"[*] TCP HTTP Server listening on {HOST}:{TCP_PORT}")
    print(f"[*] Firewall TCP Aktif: Hanya menerima request dari IP Proxy {ALLOWED_PROXY_IP}")

    while True:
        client_socket, client_address = server_socket.accept()
        
        # LOGIKA FIREWALL DITARUH DI SINI (Sebelum masuk ke Thread)
        ip_pengirim = client_address[0]
        
        # Cek apakah IP pengirim bukan IP Proxy dan bukan localhost
        if ip_pengirim != ALLOWED_PROXY_IP and ip_pengirim != '127.0.0.1':
            print(f"[FIREWALL BLOCK] {get_timestamp()} | Akses TCP ditolak dari IP ilegal")
            client_socket.close() # Putus koneksi seketika
            continue # Kembali ke atas (menunggu koneksi lain) tanpa menjalankan thread di bawahnya
        # ============================================================
        
        # Jika lolos firewall, gunakan thread untuk menangani konkurensi HTTP
        client_thread = threading.Thread(target=handle_tcp_client, args=(client_socket, client_address))
        client_thread.start()

def start_udp_server():
    """Menjalankan server UDP (QoS Echo)"""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((HOST, UDP_PORT))
    print(f"[*] UDP Echo Server listening on {HOST}:{UDP_PORT}")

    while True:
        try:
            # 1. Terima paket
            data, client_address = udp_socket.recvfrom(1024)
            start_time = time.time() # Catat waktu saat paket diterima dan siap diproses
            
            # Catatan: UDP tidak dipasangi firewall karena Client memang WAJIB menembak UDP langsung ke server untuk tes QoS.
            
            # 2. Kembalikan paket (Echo)
            udp_socket.sendto(data, client_address)
            
            # 3. Hitung metrik log
            process_time = (time.time() - start_time) * 1000
            data_size = len(data)
            
            # 4. Cetak Log UDP
            print(f"[UDP LOG] {get_timestamp()} | UDP Echo | Ukuran: {data_size} bytes | Waktu Proses: {process_time:.3f} ms")
            
        except Exception as e:
            print(f"[UDP ERROR] {get_timestamp()} | Detail Error: {e}")

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=start_tcp_server)
    udp_thread = threading.Thread(target=start_udp_server)
    
    tcp_thread.start()
    udp_thread.start()