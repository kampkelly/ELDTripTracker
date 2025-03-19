from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".ngrok-free.app",  # This allows all ngrok-free.app subdomains
    "peaceful-assuring-pony.ngrok-free.app",
]
