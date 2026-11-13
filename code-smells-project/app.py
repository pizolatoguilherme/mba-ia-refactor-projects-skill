import logging

from src.app import create_app
from src.config.settings import Settings

app = create_app()

if __name__ == "__main__":
    log = logging.getLogger(__name__)
    log.info("Servidor iniciado em http://localhost:%s", Settings.PORT)

    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
