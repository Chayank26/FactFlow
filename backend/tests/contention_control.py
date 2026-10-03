"""Deterministic contention controls installed only by the test server launcher."""
from threading import Event


def install(main):
    armed, entered, release = Event(), Event(), Event()
    original = main.process_document

    def controlled(*args):
        if armed.is_set():
            armed.clear()
            entered.set()
            try:
                if not release.wait(30):
                    raise RuntimeError('Test did not release the held operation')
            finally:
                entered.clear()
        return original(*args)

    main.process_document = controlled

    @main.app.post('/__test__/contention')
    async def arm():
        release.clear()
        entered.clear()
        armed.set()
        return {'armed': True}

    @main.app.get('/__test__/contention')
    async def status():
        return {'entered': entered.is_set()}

    @main.app.delete('/__test__/contention')
    async def resume():
        armed.clear()
        release.set()
        return {'released': True}
