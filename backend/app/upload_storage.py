"""Copy a parsed upload in bounded chunks before publishing its source file."""
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

CHUNK_BYTES = 64 * 1024


class UploadTooLarge(ValueError):
    pass


async def store_upload(upload, destination: Path, limit: int) -> int:
    """Return byte count; never publish an oversized or incomplete copy.

    The HTTP multipart parser has already received/spooled the request. This
    bounds this application's copy, not network or multipart-parser resources.
    """
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, prefix='.upload-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            total = 0
            while True:
                chunk = await upload.read(min(CHUNK_BYTES, limit - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise UploadTooLarge('The PDF exceeds the 10 MB upload limit')
                output.write(chunk)
        os.replace(temporary, destination)
        return total
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
