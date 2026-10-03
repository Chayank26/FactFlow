"""Portable source references; no application initialization on import."""
from pathlib import Path


class InvalidSource(ValueError):
    pass


def resolve_source(reference: str, uploads: Path) -> Path:
    if not reference or reference in {'.', '..'} or any(c in reference for c in ('/', '\\', '\0')):
        raise InvalidSource('Invalid source reference')
    root = uploads.resolve()
    path = root / reference
    try:
        if path.is_symlink() or path.resolve().parent != root:
            raise InvalidSource('Invalid source reference')
        if path.exists() and not path.is_file():
            raise InvalidSource('Source is not a regular file')
    except (OSError, RuntimeError) as error:
        raise InvalidSource('Source cannot be resolved') from error
    return path


def migrate_source_references(connection, uploads: Path) -> None:
    replacements = []
    seen = set()
    for identifier, value in connection.execute('SELECT id, stored_path FROM documents'):
        try:
            path = Path(value)
            if not path.is_absolute() or any(part in {'.', '..'} for part in value.split('/')) or path.parent != uploads.resolve():
                raise InvalidSource('Legacy path is outside the original uploads root')
            resolve_source(path.name, uploads)
            if path.name in seen:
                raise InvalidSource('Duplicate source reference')
            seen.add(path.name)
            replacements.append((path.name, identifier))
        except (ValueError, TypeError, OSError) as error:
            raise ValueError(f'Cannot migrate document {identifier}: {error}. Restore the backup at its original data root; no paths were migrated.') from error
    connection.executemany('UPDATE documents SET stored_path = ? WHERE id = ?', replacements)
