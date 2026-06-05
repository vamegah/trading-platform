import redis
from backend.shared.config import settings


class NullRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.channels: dict[str, list[str]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.groups: set[tuple[str, str]] = set()
        self.group_offsets: dict[tuple[str, str], int] = {}
        self._stream_sequence = 0

    def get(self, key: str):
        return self.values.get(key)

    def setex(self, key: str, seconds: int, value: str) -> bool:
        self.values[key] = value
        return True

    def incr(self, key: str) -> int:
        value = int(self.values.get(key, "0")) + 1
        self.values[key] = str(value)
        return value

    def expire(self, key: str, seconds: int) -> bool:
        return key in self.values

    def publish(self, channel: str, message: str) -> int:
        self.channels.setdefault(channel, []).append(message)
        return 1

    def lrange(self, key: str, start: int, end: int):
        values = self.channels.get(key, [])
        return values[start : None if end == -1 else end + 1]

    def rpush(self, key: str, value: str) -> int:
        self.channels.setdefault(key, []).append(value)
        return len(self.channels[key])

    def xadd(self, name: str, fields: dict[str, str], id: str = "*", maxlen: int | None = None, approximate: bool = True):
        self._stream_sequence += 1
        entry_id = f"{int(self._stream_sequence)}-0" if id == "*" else id
        stream = self.streams.setdefault(name, [])
        stream.append((entry_id, fields))
        if maxlen and len(stream) > maxlen:
            self.streams[name] = stream[-maxlen:]
        return entry_id

    def xrange(self, name: str, min: str = "-", max: str = "+", count: int | None = None):
        values = list(self.streams.get(name, []))
        return values[:count] if count else values

    def xrevrange(self, name: str, max: str = "+", min: str = "-", count: int | None = None):
        values = list(reversed(self.streams.get(name, [])))
        return values[:count] if count else values

    def xgroup_create(self, name: str, groupname: str, id: str = "$", mkstream: bool = False):
        if mkstream:
            self.streams.setdefault(name, [])
        key = (name, groupname)
        if key in self.groups:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.groups.add(key)
        self.group_offsets[key] = 0 if id == "0" else len(self.streams.get(name, []))
        return True

    def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 1,
        block: int | None = None,
    ):
        results = []
        for stream_name in streams:
            key = (stream_name, groupname)
            offset = self.group_offsets.get(key, 0)
            entries = self.streams.get(stream_name, [])[offset : offset + count]
            if entries:
                self.group_offsets[key] = offset + len(entries)
                results.append((stream_name, entries))
        return results

    def xack(self, name: str, groupname: str, *ids: str):
        return len(ids)

    def xlen(self, name: str) -> int:
        return len(self.streams.get(name, []))

    def info(self, section: str | None = None) -> dict[str, int | str]:
        return {
            "redis_version": "null-redis",
            "used_memory": sum(len(value) for value in self.values.values()),
            "connected_clients": 1,
        }


try:
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = NullRedis()
