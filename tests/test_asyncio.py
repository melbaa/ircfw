import logging
import asyncio

import pytest

import ircfw.util

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def test_basic():

    async def hello():
        print('hello')

    async def main(ioloop):
        ioloop.call_later(1, asyncio.create_task, hello())
        await asyncio.sleep(5)

    ioloop = ircfw.util.create_loop()
    ioloop.run_until_complete(main(ioloop))
    # t = ioloop.create_task(main(ioloop))

def test_basic2():

    # TODO how to get the exception from hello(), which is a "background task" started with call_later/create_task ?

    async def hello():
        # print(asyncio.all_tasks(loop=ioloop))
        # print(asyncio.all_tasks())
        print('ooops 1?')
        raise RuntimeError('oops')
        print('ooops 2?')

    def my_create_task():
        print('creating task')
        ircfw.util.create_task(hello(), logger=logger, message='hi')
        print('done creating task')

    class hello2exc(Exception):
        pass

    async def hello2():
        await asyncio.sleep(1)
        raise hello2exc('oops')

    async def main(ioloop):
        # h = ioloop.call_later(1, asyncio.create_task, hello())
        # h = ioloop.call_later(1, my_create_task)

        # res = asyncio.gather( asyncio.sleep(5), hello2() )
        # await res

        hello2_task = ircfw.util.create_task(hello2(), logger=logger, message='hi')
        sleep_task = ircfw.util.create_task(asyncio.sleep(5), logger=logger, message='sleep')
        done, pending = await asyncio.wait([sleep_task, hello2_task], return_when=asyncio.FIRST_COMPLETED)
        assert hello2_task in done
        assert sleep_task in pending
        with pytest.raises(hello2exc):
            hello2_task.result()

        for task in pending:
            task.cancel()

    ioloop = ircfw.util.create_loop()

    res = ioloop.run_until_complete(main(ioloop))
    # ioloop.run_forever()

