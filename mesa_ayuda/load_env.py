import os
from dotenv import load_dotenv

def load_env_with_profiles():
    # Carga .env base (si existe)
    load_dotenv(override=False)

    # Perfil activo: home | office
    env = os.environ.get("APP_ENV", "").lower()

    if env in ("home", "office"):
        fname = f".env.{env}"
        if os.path.exists(fname):
            load_dotenv(dotenv_path=fname, override=True)
