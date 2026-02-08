# main.py

import socket

from waitress import serve

from src.factory import create_app

# Création explicite de l'app
app, logger, limiter = create_app()

if __name__ == "__main__":
    local_ip = socket.gethostbyname(socket.gethostname())
    logger.info(f"RUNNING | Gateway sur http://{local_ip}:5001")
    serve(app, host="0.0.0.0", port=5001, threads=8)
