# common_network/file_utils.py

import zlib # cung cấp các thuật toán nén dữ liệu và kiểm tra lỗi, bao gồm CRC32
import os
from typing import Iterator, Tuple

# Tính CRC32 của dữ liệu bytes
def crc32_bytes(data: bytes) -> int:
    return zlib.crc32(data) & 0xffffffff

def stream_file_in_chunks(path: str, chunk_size: int = 32768) -> Iterator[Tuple[int, bytes]]:
    with open(path, "rb") as f:
        offset = 0
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            yield offset, data # offset và chunk dữ liệu
            offset += len(data)

def safe_join(base_dir: str, filename: str) -> str:
    filename = os.path.basename(filename)
    return os.path.join(base_dir, filename)

def safe_write_file(path: str, data_iter, mode="wb"):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        for chunk in data_iter:
            f.write(chunk)
    os.replace(tmp, path)
