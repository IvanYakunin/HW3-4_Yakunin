import redis
import os

def get_redis_client():
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", 6379))
    return redis.StrictRedis(host=host, port=port, db=0, decode_responses=True)