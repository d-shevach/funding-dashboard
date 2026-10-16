"""Daily MySQL dump, compressed and copied to a Google Cloud Storage bucket"""

import gzip
import os
import shutil
import subprocess
import tempfile
from datetime import date
from src.config import Config
from src.logger import get_logger

logger = get_logger("automation.backup")


def backup_database() -> dict:
    if not Config.BACKUP_BUCKET:
        logger.error("Backup não executado: BACKUP_BUCKET não configurado")
        return {"ok": False, "error": "BACKUP_BUCKET não configurado"}

    arquivo = os.path.join(tempfile.gettempdir(), f"caixa_{date.today():%Y%m%d}.sql.gz")
    env = {**os.environ, "MYSQL_PWD": Config.DB_PASSWORD}
    try:
        dump = subprocess.run(
            ["mysqldump", "-h", Config.DB_HOST, "-u", Config.DB_USER,
             "--single-transaction", "--routines", "--triggers", Config.DB_NAME],
            env=env, capture_output=True, check=True,
        )
        with gzip.open(arquivo, "wb") as destino:
            destino.write(dump.stdout)

        subprocess.run(
            ["gcloud", "storage", "cp", arquivo, f"gs://{Config.BACKUP_BUCKET}/"],
            capture_output=True, check=True,
        )
        logger.info(f"Backup enviado: gs://{Config.BACKUP_BUCKET}/{os.path.basename(arquivo)}")
        return {"ok": True, "arquivo": os.path.basename(arquivo)}
    except Exception as e:
        logger.error(f"Backup falhou: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        if os.path.exists(arquivo):
            os.remove(arquivo)
