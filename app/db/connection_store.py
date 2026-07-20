import contextvars

# Request/thread-scoped context variable to store user connection details
active_connection_ctx = contextvars.ContextVar("active_connection_ctx", default=None)

# Global connection dictionary for script-level / fallback usage
_global_active_connection = {
    "db_type": None,
    "host": None,
    "port": None,
    "database": None,
    "username": None,
    "password": None,
}

class ConnectionStoreProxy(dict):
    """
    A dictionary proxy class that intercepts dictionary operations and forwards
    them to the thread/request-scoped ContextVar if populated. Otherwise,
    falls back to the global connection dictionary.
    
    This ensures thread-safety, multi-user isolation, and process safety in FastAPI,
    while maintaining 100% backward compatibility with existing code.
    """
    def _get_current(self):
        ctx = active_connection_ctx.get()
        if ctx is not None:
            return ctx
        return _global_active_connection

    def __getitem__(self, key):
        return self._get_current()[key]

    def __setitem__(self, key, value):
        self._get_current()[key] = value

    def __delitem__(self, key):
        if key in self._get_current():
            del self._get_current()[key]

    def __contains__(self, key):
        return key in self._get_current()

    def get(self, key, default=None):
        return self._get_current().get(key, default)

    def setdefault(self, key, default=None):
        return self._get_current().setdefault(key, default)

    def update(self, *args, **kwargs):
        self._get_current().update(*args, **kwargs)

    def pop(self, *args):
        return self._get_current().pop(*args)

    def clear(self):
        self._get_current().clear()

    def keys(self):
        return self._get_current().keys()

    def values(self):
        return self._get_current().values()

    def items(self):
        return self._get_current().items()

    def __len__(self):
        return len(self._get_current())

    def __iter__(self):
        return iter(self._get_current())

    def __str__(self):
        return str(self._get_current())

    def __repr__(self):
        return repr(self._get_current())

# Singleton proxy instance imported throughout the application
active_connection = ConnectionStoreProxy()