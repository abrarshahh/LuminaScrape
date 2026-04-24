import subprocess
import time
import os
import psutil
import socket

class OllamaManager:
    def __init__(self, host="127.0.0.1", port=11434):
        self.host = host
        self.port = port
        self.process = None

    def is_api_alive(self):
        """Check if the Ollama API is actually listening on the port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            try:
                s.connect((self.host, self.port))
                return True
            except (ConnectionRefusedError, socket.timeout):
                return False

    def is_process_running(self):
        """Check if any ollama process exists."""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def start(self):
        """Starts the Ollama server if it's not actually responding."""
        if self.is_api_alive():
            print(f"[Ollama] API is already alive on {self.host}:{self.port}")
            return True

        print("[Ollama] API not responding. Starting Ollama service...")
        try:
            # We use 'ollama serve' to ensure the API starts
            self.process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # Poll until alive (max 15 seconds)
            for i in range(15):
                time.sleep(1)
                if self.is_api_alive():
                    print(f"[Ollama] Service started and responding after {i+1}s.")
                    return True
                print(f"[Ollama] Waiting for API... ({i+1}/15)")
            
            print("[Ollama] Warning: Service started but API is still not responding.")
            return False
        except Exception as e:
            print(f"[Ollama] Failed to start: {e}")
            return False

    def stop(self):
        """Stops the Ollama server if we started it."""
        if self.process:
            print("[Ollama] Shutting down started Ollama service...")
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                print("[Ollama] Service stopped.")
            except Exception as e:
                print(f"[Ollama] Error stopping service: {e}")
