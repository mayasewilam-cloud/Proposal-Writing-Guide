import copy
import re

path = 'upload/core/reference_service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import copy
if 'import copy' not in content:
    content = content.replace('import time\n', 'import time\nimport copy\n')

# Update val_copy = dict(value) -> val_copy = copy.deepcopy(value)
old_set_part = "        now = timestamp if timestamp is not None else time.time()\n        val_copy = dict(value)"
new_set_part = "        now = timestamp if timestamp is not None else time.time()\n        val_copy = copy.deepcopy(value)"
assert old_set_part in content, "old_set_part not found"
content = content.replace(old_set_part, new_set_part)

# Update get()
old_get = """    def get(self, key: str, default=None, max_age: Optional[float] = None):
        norm_key = self._normalize(key)
        if super().__contains__(norm_key):
            if self.is_expired(norm_key, custom_ttl=max_age):
                self.pop(norm_key, None)
                self._timestamps.pop(norm_key, None)
                return default
            return super().get(norm_key)
        return default"""

new_get = """    def get(self, key: str, default=None, max_age: Optional[float] = None):
        norm_key = self._normalize(key)
        if super().__contains__(norm_key):
            if self.is_expired(norm_key, custom_ttl=max_age):
                self.pop(norm_key, None)
                self._timestamps.pop(norm_key, None)
                return default
            res = super().get(norm_key)
            return copy.deepcopy(res) if res is not None else default
        return default"""
assert old_get in content, "old_get not found"
content = content.replace(old_get, new_get)

# Update __getitem__
old_getitem = """    def __getitem__(self, key: str):
        norm_key = self._normalize(key)
        if not super().__contains__(norm_key):
            raise KeyError(key)
        if self.is_expired(norm_key):
            self.pop(norm_key, None)
            self._timestamps.pop(norm_key, None)
            raise KeyError(f\"{key} (expired)\")
        return super().__getitem__(norm_key)"""

new_getitem = """    def __getitem__(self, key: str):
        norm_key = self._normalize(key)
        if not super().__contains__(norm_key):
            raise KeyError(key)
        if self.is_expired(norm_key):
            self.pop(norm_key, None)
            self._timestamps.pop(norm_key, None)
            raise KeyError(f\"{key} (expired)\")
        return copy.deepcopy(super().__getitem__(norm_key))"""
assert old_getitem in content, "old_getitem not found"
content = content.replace(old_getitem, new_getitem)

# Add values and items defensive copying
old_clear = """    def clear(self) -> None:
        self._timestamps.clear()
        super().clear()"""

new_clear = """    def values(self):
        expired = [k for k in list(self.keys()) if self.is_expired(k)]
        for k in expired:
            self.pop(k, None)
        return [copy.deepcopy(v) for v in super().values()]

    def items(self):
        expired = [k for k in list(self.keys()) if self.is_expired(k)]
        for k in expired:
            self.pop(k, None)
        return [(k, copy.deepcopy(v)) for k, v in super().items()]

    def clear(self) -> None:
        self._timestamps.clear()
        super().clear()"""
assert old_clear in content, "old_clear not found"
content = content.replace(old_clear, new_clear)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Successfully applied defensive copying to CitationStatusCache in reference_service.py")
