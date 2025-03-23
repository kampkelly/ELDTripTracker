import os
from .base import *  # noqa
from dotenv import load_dotenv

load_dotenv()

DEBUG = False
ALLOWED_HOSTS = [".vercel.app"]
