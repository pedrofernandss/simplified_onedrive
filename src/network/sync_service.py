import os
import json
import struct
import socket
import hashlib
import threading


class SyncService:
    """Serviço de sincronização de arquivos via TCP.

    - Servidor TCP (porta 8888): responde pedidos LIST e GET de outros nós.
    - Cliente TCP: conecta em peers para listar e baixar arquivos ausentes.
    """

    def __init__(self, sync_dir: str, node_id: str):
        self.sync_dir = sync_dir
        self.node_id = node_id
        self.tcp_port = 8888
        self.running = True

    def _recv_exactly(self, sock: socket.socket, n: int) -> bytes | None:
        """Recebe exatamente `n` bytes do socket."""
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _send_message(self, sock: socket.socket, header: dict, payload: bytes = b"") -> None:
        """Envia header JSON com prefixo de tamanho (4 bytes big-endian) + payload opcional."""
        header_bytes = json.dumps(header).encode("utf-8")
        sock.sendall(struct.pack("!I", len(header_bytes)))
        sock.sendall(header_bytes)
        if payload:
            sock.sendall(payload)

    def _recv_message(self, sock: socket.socket) -> dict | None:
        """Recebe header JSON com prefixo de tamanho. Retorna o dict parseado."""
        raw_len = self._recv_exactly(sock, 4)
        if not raw_len:
            return None
        header_len = struct.unpack("!I", raw_len)[0]
        header_bytes = self._recv_exactly(sock, header_len)
        if not header_bytes:
            return None
        return json.loads(header_bytes.decode("utf-8"))


    def _get_file_hash(self, filepath: str) -> str | None:
        """Calcula SHA-256 do arquivo em blocos de 64 KB."""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for block in iter(lambda: f.read(65536), b""):
                    sha256.update(block)
            return sha256.hexdigest()
        except FileNotFoundError:
            return None

    def _get_local_files(self) -> dict:
        """Retorna dicionário {caminho_relativo: {"hash": ..., "size": ...}} dos arquivos locais."""
        files = {}
        for root, _, filenames in os.walk(self.sync_dir):
            for fname in filenames:
                filepath = os.path.join(root, fname)
                rel_path = os.path.relpath(filepath, self.sync_dir)
                file_hash = self._get_file_hash(filepath)
                if file_hash:
                    files[rel_path] = {
                        "hash": file_hash,
                        "size": os.path.getsize(filepath)
                    }
        return files

    #  SERVIDOR TCP

    def _handle_client(self, conn: socket.socket, addr: tuple) -> None:
        """Trata uma conexão TCP recebida. Suporta ações LIST e GET."""
        try:
            header = self._recv_message(conn)
            if not header:
                return

            action = header.get("action")

            if action == "list":
                files = self._get_local_files()
                self._send_message(conn, {
                    "action": "list_response",
                    "files": files
                })

            elif action == "get":
                filename = header.get("filename")
                filepath = os.path.join(self.sync_dir, filename)

                if os.path.exists(filepath):
                    file_hash = self._get_file_hash(filepath)
                    file_size = os.path.getsize(filepath)

                    with open(filepath, "rb") as f:
                        content = f.read()

                    self._send_message(conn, {
                        "action": "get_response",
                        "filename": filename,
                        "hash": file_hash,
                        "size": file_size
                    }, content)
                else:
                    self._send_message(conn, {
                        "action": "error",
                        "message": f"Arquivo não encontrado: {filename}"
                    })

        except Exception as e:
            print(f"[{self.node_id}] Erro ao atender conexão de {addr}: {e}")
        finally:
            conn.close()

    def _tcp_server(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(1.0)
        server.bind(("", self.tcp_port))
        server.listen(5)

        print(f"[{self.node_id}] Servidor TCP ouvindo na porta {self.tcp_port}")

        while self.running:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue

        server.close()

    #  CLIENTE TCP — Sincronização inicial

    def sync_with_peer(self, peer_id: str, peer_ip: str) -> None:
        """Conecta no peer, compara catálogos e baixa arquivos ausentes."""
        try:
            print(f"\n[{self.node_id}] Iniciando sincronização com {peer_id} ({peer_ip})...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((peer_ip, self.tcp_port))

            self._send_message(sock, {"action": "list", "node_id": self.node_id})
            response = self._recv_message(sock)
            sock.close()

            if not response or response.get("action") != "list_response":
                print(f"[{self.node_id}] Resposta inválida de {peer_id}")
                return

            remote_files = response.get("files", {})
            local_files = self._get_local_files()

            files_to_download = []
            for filename, info in remote_files.items():
                if filename not in local_files or local_files[filename]["hash"] != info["hash"]:
                    files_to_download.append(filename)

            if not files_to_download:
                print(f"[{self.node_id}] Já está sincronizado com {peer_id}")
                return

            print(f"[{self.node_id}] {len(files_to_download)} arquivo(s) para baixar de {peer_id}")

            for filename in files_to_download:
                self._download_file(peer_id, peer_ip, filename)

            print(f"[{self.node_id}] Sincronização com {peer_id} concluída!\n")

        except Exception as e:
            print(f"[{self.node_id}] Erro na sincronização com {peer_id}: {e}")

    def _download_file(self, peer_id: str, peer_ip: str, filename: str) -> None:
        """Baixa um único arquivo de um peer via TCP."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((peer_ip, self.tcp_port))

            self._send_message(sock, {"action": "get", "filename": filename})
            response = self._recv_message(sock)

            if not response or response.get("action") != "get_response":
                print(f"[{self.node_id}] Falha ao baixar {filename} de {peer_id}")
                sock.close()
                return

            file_size = response.get("size", 0)
            expected_hash = response.get("hash")

            content = self._recv_exactly(sock, file_size)
            sock.close()

            if not content:
                print(f"[{self.node_id}] Conteúdo vazio para {filename}")
                return

            received_hash = hashlib.sha256(content).hexdigest()
            if received_hash != expected_hash:
                print(f"[{self.node_id}] ⚠️  Hash incorreto para {filename}! Descartando.")
                return

            filepath = os.path.join(self.sync_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, "wb") as f:
                f.write(content)

            print(f"[{self.node_id}] ✅ Arquivo recebido: {filename} ({file_size} bytes)")

        except Exception as e:
            print(f"[{self.node_id}] Erro ao baixar {filename}: {e}")

    def start(self) -> None:
        threading.Thread(target=self._tcp_server, daemon=True).start()
