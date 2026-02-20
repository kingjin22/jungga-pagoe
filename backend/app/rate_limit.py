"""공유 rate limiter — main.py와 routers 양쪽에서 import"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
