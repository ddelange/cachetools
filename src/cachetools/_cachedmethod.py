"""Method decorator helpers."""

import weakref


def _cachedmethod_condition_info(*, method, cache, key, lock, condition, info):
    pending = weakref.WeakKeyDictionary()
    hits_misses = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)

        # Get or initialize hits/misses counters for this instance
        if self not in hits_misses:
            hits_misses[self] = [0, 0]  # [hits, misses]

        k = key(self, *args, **kwargs)
        with lock(self):
            p = pending.setdefault(self, set())
            condition(self).wait_for(lambda: k not in p)
            try:
                result = c[k]
                hits_misses[self][0] += 1  # increment hits
                return result
            except KeyError:
                hits_misses[self][1] += 1  # increment misses
                p.add(k)
        try:
            v = method(self, *args, **kwargs)
            with lock(self):
                try:
                    c[k] = v
                except ValueError:
                    pass  # value too large
                return v
        finally:
            with lock(self):
                pending[self].remove(k)
                condition(self).notify_all()

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            with lock(self):
                c.clear()
                if self in hits_misses:
                    hits_misses[self] = [0, 0]  # reset counters

    def cache_info(self):
        if self in hits_misses:
            h, m = hits_misses[self]
            return info(h, m)
        return info(0, 0)  # Default if no hits/misses recorded

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


def _cachedmethod_locked_info(*, method, cache, key, lock, info):
    hits_misses = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)

        # Get or initialize hits/misses counters for this instance
        if self not in hits_misses:
            hits_misses[self] = [0, 0]  # [hits, misses]

        k = key(self, *args, **kwargs)
        with lock(self):
            try:
                result = c[k]
                hits_misses[self][0] += 1  # increment hits
                return result
            except KeyError:
                hits_misses[self][1] += 1  # increment misses
                pass  # key not found
        v = method(self, *args, **kwargs)
        # in case of a race, prefer the item already in the cache
        with lock(self):
            try:
                return c.setdefault(k, v)
            except ValueError:
                return v  # value too large

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            with lock(self):
                c.clear()
                if self in hits_misses:
                    hits_misses[self] = [0, 0]  # reset counters

    def cache_info(self):
        if self in hits_misses:
            h, m = hits_misses[self]
            return info(h, m)
        return info(0, 0)  # Default if no hits/misses recorded

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


def _cachedmethod_unlocked_info(*, method, cache, key, info):
    hits_misses = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)

        # Get or initialize hits/misses counters for this instance
        if self not in hits_misses:
            hits_misses[self] = [0, 0]  # [hits, misses]

        k = key(self, *args, **kwargs)
        try:
            result = c[k]
            hits_misses[self][0] += 1  # increment hits
            return result
        except KeyError:
            hits_misses[self][1] += 1  # increment misses
            pass  # key not found
        v = method(self, *args, **kwargs)
        try:
            c[k] = v
        except ValueError:
            pass  # value too large
        return v

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            c.clear()
            if self in hits_misses:
                hits_misses[self] = [0, 0]  # reset counters

    def cache_info(self):
        if self in hits_misses:
            h, m = hits_misses[self]
            return info(h, m)
        return info(0, 0)  # Default if no hits/misses recorded

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


def _uncachedmethod_info(method, info):
    misses = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        if self not in misses:
            misses[self] = 0
        misses[self] += 1
        return method(self, *args, **kwargs)

    def cache_clear(self):
        if self in misses:
            misses[self] = 0

    def cache_info(self):
        m = misses.get(self, 0)
        return info(0, m)

    wrapper.cache_clear = cache_clear
    wrapper.cache_info = cache_info
    return wrapper


def _cachedmethod_condition(*, method, cache, key, lock, condition):
    pending = weakref.WeakKeyDictionary()

    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)
        k = key(self, *args, **kwargs)
        with lock(self):
            p = pending.setdefault(self, set())
            condition(self).wait_for(lambda: k not in p)
            try:
                return c[k]
            except KeyError:
                p.add(k)
        try:
            v = method(self, *args, **kwargs)
            with lock(self):
                try:
                    c[k] = v
                except ValueError:
                    pass  # value too large
                return v
        finally:
            with lock(self):
                pending[self].remove(k)
                condition(self).notify_all()

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            with lock(self):
                c.clear()

    wrapper.cache_clear = cache_clear
    return wrapper


def _cachedmethod_locked(*, method, cache, key, lock):
    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)
        k = key(self, *args, **kwargs)
        with lock(self):
            try:
                return c[k]
            except KeyError:
                pass  # key not found
        v = method(self, *args, **kwargs)
        # in case of a race, prefer the item already in the cache
        with lock(self):
            try:
                return c.setdefault(k, v)
            except ValueError:
                return v  # value too large

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            with lock(self):
                c.clear()

    wrapper.cache_clear = cache_clear
    return wrapper


def _cachedmethod_unlocked(*, method, cache, key):
    def wrapper(self, *args, **kwargs):
        c = cache(self)
        if c is None:
            return method(self, *args, **kwargs)
        k = key(self, *args, **kwargs)
        try:
            return c[k]
        except KeyError:
            pass  # key not found
        v = method(self, *args, **kwargs)
        try:
            c[k] = v
        except ValueError:
            pass  # value too large
        return v

    def cache_clear(self):
        c = cache(self)
        if c is not None:
            c.clear()

    wrapper.cache_clear = cache_clear
    return wrapper


def _cachedmethod_wrapper(*, method, cache, key, lock=None, condition=None, info=None):
    if info is not None:
        if cache is None:
            wrapper = _uncachedmethod_info(method=method, info=info)
        elif condition is not None and lock is not None:
            wrapper = _cachedmethod_condition_info(
                method=method,
                cache=cache,
                key=key,
                lock=lock,
                condition=condition,
                info=info,
            )
        elif condition is not None:
            # passing lock=condition because _cachedmethod_condition does 'with lock(self)'
            wrapper = _cachedmethod_condition_info(
                method=method,
                cache=cache,
                key=key,
                lock=condition,
                condition=condition,
                info=info,
            )
        elif lock is not None:
            wrapper = _cachedmethod_locked_info(
                method=method, cache=cache, key=key, lock=lock, info=info
            )
        else:
            wrapper = _cachedmethod_unlocked_info(
                method=method, cache=cache, key=key, info=info
            )
    else:
        if cache is None:
            wrapper = method  # No caching at all
        elif condition is not None and lock is not None:
            wrapper = _cachedmethod_condition(
                method=method, cache=cache, key=key, lock=lock, condition=condition
            )
        elif condition is not None:
            # passing lock=condition because _cachedmethod_condition does 'with lock(self)'
            wrapper = _cachedmethod_condition(
                method=method, cache=cache, key=key, lock=condition, condition=condition
            )
        elif lock is not None:
            wrapper = _cachedmethod_locked(
                method=method, cache=cache, key=key, lock=lock
            )
        else:
            wrapper = _cachedmethod_unlocked(method=method, cache=cache, key=key)
        wrapper.cache_info = None
    return wrapper
