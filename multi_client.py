import subprocess
import time

def run_concurrent_clients(num_clients):
    print(f"[*] Menjalankan {num_clients} Client TCP secara bersamaan...")
    processes = []
    
    start_time = time.time()
    
    for i in range(num_clients):
        # Membuka proses baru untuk setiap client
        print(f" -> Spawn Client-{i+1}")
        p = subprocess.Popen(["python", "client.py", "-mode", "tcp"])
        processes.append(p)
        
    # Menunggu semua proses selesai
    for p in processes:
        p.wait()
        
    end_time = time.time()
    print(f"\n[*] Semua {num_clients} client selesai dieksekusi dalam {(end_time - start_time):.2f} detik.")

if __name__ == '__main__':
    # Eksekusi minimal 5 client sesuai ketentuan dokumen
    run_concurrent_clients(5)