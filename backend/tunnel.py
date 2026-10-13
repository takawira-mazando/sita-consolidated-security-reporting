import socket
import threading
import time
import paramiko

REMOTE_HOST = "192.168.101.20"
REMOTE_USER = "uni"
REMOTE_PASS = "H051@pivot"

def pipe(source, dest):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            dest.sendall(data)
    except Exception:
        pass
    finally:
        try: source.close()
        except Exception: pass
        try: dest.close()
        except Exception: pass

def bridge(sock1, sock2):
    t1 = threading.Thread(target=pipe, args=(sock1, sock2), daemon=True)
    t2 = threading.Thread(target=pipe, args=(sock2, sock1), daemon=True)
    t1.start()
    t2.start()

def listen_and_forward(local_port, remote_host, remote_port, transport):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", local_port))
    server.listen(50)
    print(f"[TUNNEL] localhost:{local_port} -> {remote_host}:{remote_port} READY")

    while True:
        client_sock, addr = server.accept()
        try:
            channel = transport.open_channel(
                "direct-tcpip",
                (remote_host, remote_port),
                client_sock.getpeername(),
            )
        except Exception as e:
            print(f"[TUNNEL] Failed to open channel: {e}")
            client_sock.close()
            continue

        if channel is None:
            client_sock.close()
            continue

        bridge(client_sock, channel)

def main():
    print(f"==> Connecting SSH client to {REMOTE_USER}@{REMOTE_HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=15)
    transport = client.get_transport()

    # Port 8801 -> Remote 127.0.0.1:8000 (Backend API, Swagger, Health)
    threading.Thread(
        target=listen_and_forward,
        args=(8801, "127.0.0.1", 8000, transport),
        daemon=True,
    ).start()

    # Port 8802 -> Remote 127.0.0.1:8088 (Frontend Web App via Nginx)
    threading.Thread(
        target=listen_and_forward,
        args=(8802, "127.0.0.1", 8088, transport),
        daemon=True,
    ).start()

    print("[TUNNEL] Tunnels active:")
    print("  http://localhost:8801 -> Backend API / Swagger / Health")
    print("  http://localhost:8802 -> Frontend App")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
