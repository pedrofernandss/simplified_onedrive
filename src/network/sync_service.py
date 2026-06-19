import os
import json
import struct
import socket
import hashlib
import threading
from typing import cast

from utils.merge import create_merge_conflits_marks, has_merge_conflict_marks

class SyncService:
    def __init__(self, sync_dir: str, node_id: str, monitor):
        self.sync_dir = sync_dir
        self.node_id = node_id
        self.tcp_port = 8888
        self.running = True
        self.monitor = monitor

    def _recv_exactly(self, sock: socket.socket, n: int) -> bytes | None:
        """Recebe exatamente `n` bytes do socket."""
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def _send_message(self, sock: socket.socket, header: dict[str, object], payload: bytes = b"") -> None:
        """Envia header JSON com prefixo de tamanho (4 bytes big-endian) + payload opcional."""
        header_bytes = json.dumps(header).encode("utf-8")
        sock.sendall(struct.pack("!I", len(header_bytes)))
        sock.sendall(header_bytes)
        if payload:
            sock.sendall(payload)

    def _recv_message(self, sock: socket.socket) -> dict[str, object] | None:
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

    def _normalize_remote_files(self, value: object) -> dict[str, dict[str, object]] | None:
        if not isinstance(value, dict):
            return None

        return cast(dict[str, dict[str, object]], value)

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
                if "filename" not in header or not isinstance(header["filename"], str):
                    self._send_message(conn, {
                        "action": "error",
                        "message": "Nome de arquivo inválido"
                    })
                    return

                filename = cast(str, header["filename"])

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

            elif action == "push":
                if "filename" not in header or "size" not in header:
                    self._send_message(conn, {
                        "status": "error",
                        "message": "Cabeçalho de push inválido"
                    })
                    return

                filename_raw = header["filename"]
                file_size_raw = header["size"]
                expected_hash_raw = header.get("hash")
                force_raw = header.get("force", False)

                if not isinstance(filename_raw, str) or not isinstance(file_size_raw, int):
                    self._send_message(conn, {
                        "status": "error",
                        "message": "Cabeçalho de push inválido"
                    })
                    return

                if expected_hash_raw is not None and not isinstance(expected_hash_raw, str):
                    self._send_message(conn, {
                        "status": "error",
                        "message": "Hash inválido no push"
                    })
                    return

                if not isinstance(force_raw, bool):
                    self._send_message(conn, {
                        "status": "error",
                        "message": "Flag de sobrescrita inválida"
                    })
                    return

                filename = cast(str, filename_raw)
                file_size = cast(int, file_size_raw)
                expected_hash = cast(str | None, expected_hash_raw)
                force = cast(bool, force_raw)

                content = self._recv_exactly(conn, file_size)

                if content is not None:
                    filepath = os.path.join(self.sync_dir, filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    remote_content = content.decode('utf-8', errors='ignore')

                    if os.path.exists(filepath):
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            local_content = f.read()

                        local_hash = hashlib.sha256(local_content.encode('utf-8')).hexdigest()

                        if force:
                            self.monitor.ignore_next_scan.add(filename)

                            with open(filepath, "wb") as f:
                                f.write(content)

                            ans = {"status": "success"}
                            ans_json = json.dumps(ans).encode('utf-8')
                            conn.sendall(len(ans_json).to_bytes(4, byteorder='big') + ans_json)

                            print(f"[{self.node_id}] Arquivo {filename} sobrescrito com sucesso.")
                            return

                        if local_hash != expected_hash:
                            merged_text = create_merge_conflits_marks(local_content, remote_content)
                            merged_bytes = merged_text.encode('utf-8')

                            if has_merge_conflict_marks(merged_text):
                                print(f"[{self.node_id}] Conflito detectado em '{filename}'.")

                                ans = {
                                    "status": "conflict",
                                    "filename": filename,
                                    "size": len(merged_bytes)
                                }
                                ans_json = json.dumps(ans).encode('utf-8')

                                conn.sendall(len(ans_json).to_bytes(4, byteorder='big') + ans_json)
                                conn.sendall(merged_bytes)
                                return

                            self.monitor.ignore_next_scan.add(filename)

                            with open(filepath, "wb") as f:
                                f.write(merged_bytes)

                            if merged_text == remote_content:
                                ans = {"status": "success"}
                                ans_json = json.dumps(ans).encode('utf-8')
                                conn.sendall(len(ans_json).to_bytes(4, byteorder='big') + ans_json)
                                print(f"[{self.node_id}] Merge automático aplicado em '{filename}'.")
                                return

                            ans = {
                                "status": "merged",
                                "filename": filename,
                                "size": len(merged_bytes)
                            }
                            ans_json = json.dumps(ans).encode('utf-8')

                            conn.sendall(len(ans_json).to_bytes(4, byteorder='big') + ans_json)
                            conn.sendall(merged_bytes)
                            print(f"[{self.node_id}] Merge automático aplicado em '{filename}'.")
                            return

                    self.monitor.ignore_next_scan.add(filename)

                    with open(filepath, "wb") as f:
                        f.write(content)

                    ans = {"status": "success"}
                    ans_json = json.dumps(ans).encode('utf-8')
                    conn.sendall(len(ans_json).to_bytes(4, byteorder='big') + ans_json)

                    print(f"[{self.node_id}] Arquivo {filename} atualizado com sucesso.")

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
                print(f"[{self.node_id}] ans inválida de {peer_id}")
                return

            remote_files_raw = response.get("files", {})
            remote_files = self._normalize_remote_files(remote_files_raw)
            if remote_files is None:
                print(f"[{self.node_id}] Catálogo remoto inválido vindo de {peer_id}")
                return
            local_files = self._get_local_files()

            files_to_download = []
            for filename in remote_files:
                info = remote_files[filename]
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

            if not response or "action" not in response or response["action"] != "get_response":
                print(f"[{self.node_id}] Falha ao baixar {filename} de {peer_id}")
                sock.close()
                return

            if "size" not in response or "hash" not in response:
                print(f"[{self.node_id}] Resposta inválida para {filename} de {peer_id}")
                return

            file_size_raw = response["size"]
            expected_hash_raw = response["hash"]

            if not isinstance(file_size_raw, int) or file_size_raw < 0:
                print(f"[{self.node_id}] Resposta inválida para {filename} de {peer_id}")
                return

            if not isinstance(expected_hash_raw, str):
                print(f"[{self.node_id}] Hash inválido recebido para {filename} de {peer_id}")
                return

            file_size = cast(int, file_size_raw)
            expected_hash = cast(str, expected_hash_raw)

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

    def spread_modifications(self, peer_ip: str, filename: str, force: bool = False) -> None:
        try:
            filepath = os.path.join(self.sync_dir, filename)

            with open(filepath, "rb") as f:
                content = f.read()

            file_hash = self._get_file_hash(filepath)
            if not isinstance(file_hash, str):
                raise ValueError(f"Não foi possível calcular o hash de '{filename}'")
            file_size = len(content)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_ip, self.tcp_port))

            header = {
                "action": "push",
                "filename": filename,
                "hash": file_hash,
                "size": file_size,
                "node_id": self.node_id,
                "force": force
            }

            self._send_message(sock, header, content)

            resp_size_bytes = self._recv_exactly(sock, 4)
            if resp_size_bytes:
                resp_size = int.from_bytes(resp_size_bytes, byteorder='big')
                resp_json_bytes = self._recv_exactly(sock, resp_size)

                if resp_json_bytes is None:
                    sock.close()
                    return

                ans = json.loads(resp_json_bytes.decode('utf-8'))
                status = ans.get("status")

                if status == "conflict":
                    print(f"[{self.node_id}] Alterações rejeitados pelo peer {peer_ip}!")

                    conflict_size = ans.get("size")
                    if not isinstance(conflict_size, int):
                        sock.close()
                        return

                    conflict_content = self._recv_exactly(sock, conflict_size)

                    if conflict_content is None:
                        sock.close()
                        return

                    with open(filepath, "wb") as f:
                        f.write(conflict_content)

                    self.monitor.mark_force_overwrite_after_resolution(filename)

                    print(f"[{self.node_id}] Conflito detectado no arquivo '{filename}'. Realize as correções de conflito e tente novamente.")

                elif status == "merged":
                    merged_size = ans.get("size")
                    if not isinstance(merged_size, int):
                        sock.close()
                        return

                    merged_content = self._recv_exactly(sock, merged_size)

                    if merged_content is None:
                        sock.close()
                        return

                    self.monitor.ignore_next_scan.add(filename)

                    with open(filepath, "wb") as f:
                        f.write(merged_content)

                    print(f"[{self.node_id}] Merge automático aplicado ao arquivo '{filename}'.")

                elif status == "success":
                    if force:
                        print(f"[{self.node_id}] - Arquivo '{filename}' sobrescrito com sucesso em peer {peer_ip}")
                    else:
                        print(f"[{self.node_id}] - Arquivo '{filename}' compartilhado com sucesso com peer {peer_ip}")
            sock.close()

        except Exception as e:
            print(f"[{self.node_id}] Falha ao enviar '{filename}' para {peer_ip}: {e}")

    def start(self) -> None:
        threading.Thread(target=self._tcp_server, daemon=True).start()
