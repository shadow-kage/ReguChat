import redis
import json


r = redis.Redis(host="localhost", port=6379, db=0)


def get_cache(query):

    data = r.get(query)

    if data:
        return json.loads(data)

    return None


def store_cache(query, answer):

    r.set(query, json.dumps(answer))