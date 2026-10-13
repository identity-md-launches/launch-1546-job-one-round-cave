"""Bounded no-follow workspace I/O; reused from Gathering 18."""
import os
from pathlib import Path
import stat
MAX_BYTES = 99000

def file_parts(raw):
    path = Path(raw)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('relative workspace file without traversal required')
    return path.parts


def parent_descriptor(raw):
    parts = file_parts(raw)
    if not all(hasattr(os, name) for name in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')):
        raise ValueError('POSIX no-follow file support required')
    directory = os.open(Path.cwd(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
    except BaseException:
        os.close(directory)
        raise
    return directory, parts[-1]


def read_workspace(raw):
    directory, name = parent_descriptor(raw)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        with os.fdopen(descriptor, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise ValueError('bounded regular file required')
            data = source.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('file grew past byte limit')
        return data
    finally:
        os.close(directory)


def save_new(raw, data):
    """Create one explicit output through no-follow parents; never overwrite."""
    directory, name = parent_descriptor(raw)
    try:
        descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=directory)
        try:
            with os.fdopen(descriptor, 'wb') as target:
                target.write(data)
        except BaseException:
            os.unlink(name, dir_fd=directory)
            raise
    finally:
        os.close(directory)

