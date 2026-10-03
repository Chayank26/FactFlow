"""Single-process admission for source mutations; no waiting queue."""
import asyncio
from contextlib import contextmanager
from threading import Lock

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool


class MutationGate:
    def __init__(self):
        self._lock = Lock()
        self._workers = set()

    @contextmanager
    def reserve(self):
        if not self._lock.acquire(blocking=False):
            raise HTTPException(
                status_code=503,
                detail='Another document operation is in progress. Please retry when it finishes.',
                headers={'Retry-After': '1'},
            )
        lease = _Lease(self)
        try:
            yield lease
        finally:
            if not lease.deferred:
                self._lock.release()


class _Lease:
    def __init__(self, gate):
        self.gate = gate
        self.deferred = False

    async def run_sync(self, function, *args):
        # A strong task reference and shielding keep ownership with the worker
        # after the requesting task is cancelled. Release only on completion.
        task = asyncio.create_task(run_in_threadpool(function, *args))
        self.gate._workers.add(task)
        self.deferred = True

        def finished(worker):
            self.gate._workers.discard(worker)
            self.gate._lock.release()
            if not worker.cancelled():
                worker.exception()  # Observe failures even if the requester left.

        task.add_done_callback(finished)
        return await asyncio.shield(task)
