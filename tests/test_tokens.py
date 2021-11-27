import functools
import token_bucket

def test_tokens():
    storage = token_bucket.MemoryStorage()
    limiter = token_bucket.Limiter(rate=3, capacity=5, storage=storage)
    consume = functools.partial(limiter.consume, key=b'X')
    consume()
    consume()
    consume()
    consume()
    consume()
    assert not consume()
