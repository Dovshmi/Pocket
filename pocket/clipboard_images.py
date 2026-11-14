"""Windows image clipboard support, deliberately isolated from the UI.

History is memory-only and capped at twenty pictures. Nothing is written to
Pocket's profile, the filesystem, or a network service.
"""
from __future__ import annotations

import ctypes
from datetime import datetime
import hashlib
from io import BytesIO
import sys
import time
import uuid

from PIL import Image, ImageGrab

MAX_IMAGES = 20
MAX_PIXELS = 16_000_000
MAX_PNG_BYTES = 12 * 1024 * 1024


def sequence_number():
    """A cheap change signal; None on non-Windows systems or inaccessible API."""
    if sys.platform != "win32":
        return None
    try:
        fn = ctypes.windll.user32.GetClipboardSequenceNumber
        fn.restype = ctypes.c_uint
        return fn() or None
    except (AttributeError, OSError):
        return None


def image_available():
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        user32.IsClipboardFormatAvailable.argtypes = [ctypes.c_uint]
        user32.IsClipboardFormatAvailable.restype = ctypes.c_int
        user32.RegisterClipboardFormatW.argtypes = [ctypes.c_wchar_p]
        user32.RegisterClipboardFormatW.restype = ctypes.c_uint
        png = user32.RegisterClipboardFormatW("PNG")
        # CF_BITMAP, CF_DIB and CF_DIBV5; "PNG" is used by some browsers/apps.
        return any(user32.IsClipboardFormatAvailable(fmt)
                   for fmt in (2, 8, 17, png) if fmt)
    except (AttributeError, OSError):
        return False


def read_image():
    """Read a real bitmap, not file-drop lists. Captures Snipping Tool and Word."""
    if not image_available():
        return None
    try:
        result = ImageGrab.grabclipboard()
        return result if isinstance(result, Image.Image) else None
    except (OSError, ValueError, TypeError):
        return None


def add_image(items, image, *, maximum=MAX_IMAGES,
              maximum_bytes=MAX_PNG_BYTES, maximum_pixels=MAX_PIXELS):
    """Store PNG bytes in RAM. Newest first; discard oldest at capacity."""
    if not isinstance(image, Image.Image) or maximum < 1:
        return False
    width, height = image.size
    if width < 1 or height < 1 or width * height > maximum_pixels:
        return False
    try:
        # Re-encoding strips metadata and avoids keeping raw RGBA buffers.
        stream = BytesIO()
        image.convert("RGBA" if "A" in image.getbands() else "RGB").save(
            stream, format="PNG", compress_level=3)
        payload = stream.getvalue()
    except (OSError, ValueError, TypeError, MemoryError):
        return False
    if len(payload) > maximum_bytes:
        return False
    digest = hashlib.sha256(payload).hexdigest()
    if items and items[0]["digest"] == digest:
        return False
    items[:] = [item for item in items if item["digest"] != digest]
    items.insert(0, {
        "id": uuid.uuid4().hex, "data": payload, "digest": digest,
        "time": datetime.now().strftime("%H:%M:%S"),
        "width": width, "height": height,
    })
    del items[maximum:]
    return True


def decode_image(payload):
    with Image.open(BytesIO(payload)) as opened:
        return opened.copy()


def copy_image(payload):
    """Put a bitmap back into the real Windows clipboard as CF_DIB."""
    if sys.platform != "win32":
        raise OSError("Image clipboard writing requires Windows")
    image = decode_image(payload).convert("RGB")
    stream = BytesIO()
    image.save(stream, format="BMP")
    dib = stream.getvalue()[14:]  # Strip BMP file header; CF_DIB needs DIB.
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_int
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]

    acquired = False
    for _ in range(5):
        if user32.OpenClipboard(None):
            acquired = True
            break
        time.sleep(0.025)
    if not acquired:
        raise OSError("The Windows clipboard is temporarily busy")
    handle = None
    try:
        handle = kernel32.GlobalAlloc(0x0002, len(dib))  # GMEM_MOVEABLE
        if not handle:
            raise MemoryError("Cannot allocate Windows clipboard memory")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise MemoryError("Cannot access Windows clipboard memory")
        try:
            ctypes.memmove(pointer, dib, len(dib))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.EmptyClipboard():
            raise OSError("Cannot clear Windows clipboard")
        if not user32.SetClipboardData(8, handle):  # CF_DIB
            raise OSError("Cannot set Windows image clipboard data")
        handle = None  # Windows owns the allocation after SetClipboardData.
    finally:
        if handle:
            kernel32.GlobalFree(handle)
        user32.CloseClipboard()
