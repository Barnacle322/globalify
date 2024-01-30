import os

from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(".env")
else:
    raise FileNotFoundError("There's no .env file in the root directory")

os.system("flask run")

