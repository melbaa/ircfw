import asyncio
import logging
import functools

def create_loop():
    # zmq uses add_reader and add_writer low level methods, which proactor loop doesn't have
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()  # pylint: disable=no-member
    )

    # loop should throw instead of swallowing exceptions

    def handle_exception(loop, context):
        # context["message"] will always be there; but context["exception"] may not
        msg = context.get("exception", context["message"])
        logging.error(f"Caught exception: {msg}")
        # raise RuntimeError('crash and burn')
    # but asyncio has a global exception handler
    ioloop = asyncio.new_event_loop()
    ioloop.set_exception_handler(handle_exception)

    # also enable debug mode
    ioloop.set_debug(True)
    return ioloop



def create_task(
    coroutine,
    *,
    logger,
    message,
    message_args = (),
    loop = None,
    ):
    '''
    This helper function wraps a ``loop.create_task(coroutine())`` call and ensures there is
    an exception handler added to the resulting task. If the task raises an exception it is logged
    using the provided ``logger``, with additional context provided by ``message`` and optionally
    ``message_args``.
    '''
    if loop is None:
        loop = asyncio.get_running_loop()
    task = loop.create_task(coroutine)
    task.add_done_callback(
        functools.partial(_handle_task_result, logger = logger, message = message, message_args = message_args)
    )
    return task


def _handle_task_result(
    task,
    *,
    logger,
    message,
    message_args = (),
):
    try:
        task.result()
    # except asyncio.CancelledError:
    #    Task cancellation should not be logged as an error.
    #    pass
    except Exception:  # pylint: disable=broad-except
        logger.exception(message, *message_args)
        raise

