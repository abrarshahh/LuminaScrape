import subprocess
import time
import os
import psutil
import socket
from core.logger import get_logger

logger = get_logger(__name__)

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
            logger.info(f"Ollama API is already alive on {self.host}:{self.port}")
            return True

        logger.info("Ollama API not responding. Starting Ollama service...")
        try:
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
                    logger.info(f"Ollama service started and responding after {i+1}s.")
                    return True
                logger.debug(f"Waiting for Ollama API... ({i+1}/15)")
            
            logger.error("Ollama service started but API is still not responding after 15s.")
            return False
        except Exception as e:
            logger.error(f"Failed to start Ollama: {e}")
            return False

    def stop(self):
        """Stops the Ollama server if we started it."""
        if self.process:
            logger.info("Shutting down started Ollama service...")
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                logger.info("Ollama service stopped.")
            except Exception as e:
                logger.error(f"Error stopping Ollama service: {e}")
