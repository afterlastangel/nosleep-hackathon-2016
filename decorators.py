from functools import wraps

from google.appengine.ext import deferred
from google.appengine.api import taskqueue


def execute(f, *args, **kwargs):  # pragma: no cover
    try:
        f(*args, **kwargs)
    except deferred.SingularTaskFailure:
        raise deferred.SingularTaskFailure


def task(f):
    @wraps(f)
    def delay(*args, **kwargs):  # pragma: no cover
        return deferred.defer(
            execute, f, *args, **kwargs)
    f.delay = delay
    return f
