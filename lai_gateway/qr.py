from __future__ import annotations

from html import escape

from .errors import ConfigError

_VERSION = 4
_SIZE = 17 + 4 * _VERSION
_DATA_CODEWORDS = 80
_ECC_CODEWORDS = 20
_FORMAT_MASK = 0x5412
_FORMAT_POLY = 0x537
_RS_POLY = 0x11D


def qr_svg(text: str, *, scale: int = 6, border: int = 4) -> str:
    """Return a local SVG QR code for short mobile URLs.

    This intentionally supports one narrow case: QR version 4-L byte mode.
    That keeps the gateway dependency-free while covering ordinary local URLs.
    """
    raw = text.encode("utf-8")
    if not raw:
        raise ConfigError("QR payload must not be empty")
    if len(raw) > 78:
        raise ConfigError("QR payload is too long for the built-in mobile QR encoder")
    if scale < 1 or border < 0:
        raise ConfigError("QR scale and border are invalid")
    matrix = _encode_v4_l(raw)
    full = _SIZE + border * 2
    rects: list[str] = []
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                rects.append(f'<rect x="{x + border}" y="{y + border}" width="1" height="1"/>')
    label = escape(text, quote=True)
    body = "".join(rects)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="QR code for {label}" '
        f'viewBox="0 0 {full} {full}" width="{full * scale}" height="{full * scale}">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<g fill="black">{body}</g></svg>'
    )


def _encode_v4_l(raw: bytes) -> list[list[bool]]:
    data = _data_codewords(raw)
    ecc = _rs_remainder(data, _ECC_CODEWORDS)
    bits = _codeword_bits(data + ecc)
    matrix: list[list[bool | None]] = [[None for _ in range(_SIZE)] for _ in range(_SIZE)]
    reserved = [[False for _ in range(_SIZE)] for _ in range(_SIZE)]
    _draw_function_patterns(matrix, reserved)
    _place_data_bits(matrix, reserved, bits)
    _draw_format_bits(matrix, reserved, mask=0)
    return [[bool(cell) for cell in row] for row in matrix]


def _data_codewords(raw: bytes) -> list[int]:
    bits: list[int] = []
    bits.extend(_int_bits(0b0100, 4))
    bits.extend(_int_bits(len(raw), 8))
    for byte in raw:
        bits.extend(_int_bits(byte, 8))
    capacity = _DATA_CODEWORDS * 8
    bits.extend([0] * min(4, capacity - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    pads = [0xEC, 0x11]
    pad_index = 0
    while len(bits) < capacity:
        bits.extend(_int_bits(pads[pad_index % 2], 8))
        pad_index += 1
    return [_bits_to_int(bits[i : i + 8]) for i in range(0, capacity, 8)]


def _draw_function_patterns(matrix: list[list[bool | None]], reserved: list[list[bool]],) -> None:
    _draw_finder(matrix, reserved, 0, 0)
    _draw_finder(matrix, reserved, _SIZE - 7, 0)
    _draw_finder(matrix, reserved, 0, _SIZE - 7)
    for i in range(8, _SIZE - 8):
        _set_function(matrix, reserved, i, 6, i % 2 == 0)
        _set_function(matrix, reserved, 6, i, i % 2 == 0)
    _draw_alignment(matrix, reserved, 26, 26)
    _set_function(matrix, reserved, 8, 4 * _VERSION + 9, True)
    _reserve_format(reserved)


def _draw_finder(matrix: list[list[bool | None]], reserved: list[list[bool]], x: int, y: int) -> None:
    for dy in range(-1, 8):
        for dx in range(-1, 8):
            xx = x + dx
            yy = y + dy
            if 0 <= xx < _SIZE and 0 <= yy < _SIZE:
                dark = 0 <= dx <= 6 and 0 <= dy <= 6 and (
                    dx in {0, 6} or dy in {0, 6} or (2 <= dx <= 4 and 2 <= dy <= 4)
                )
                _set_function(matrix, reserved, xx, yy, dark)


def _draw_alignment(matrix: list[list[bool | None]], reserved: list[list[bool]], cx: int, cy: int) -> None:
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            dark = max(abs(dx), abs(dy)) != 1
            _set_function(matrix, reserved, cx + dx, cy + dy, dark)


def _reserve_format(reserved: list[list[bool]]) -> None:
    positions = []
    for i in range(6):
        positions.append((8, i))
    positions.extend([(8, 7), (8, 8), (7, 8)])
    for i in range(9, 15):
        positions.append((14 - i, 8))
    for i in range(8):
        positions.append((_SIZE - 1 - i, 8))
    for i in range(8, 15):
        positions.append((8, _SIZE - 15 + i))
    for x, y in positions:
        reserved[y][x] = True


def _draw_format_bits(matrix: list[list[bool | None]], reserved: list[list[bool]], *, mask: int) -> None:
    bits = _format_bits(mask)
    for i in range(6):
        _set_function(matrix, reserved, 8, i, ((bits >> i) & 1) != 0)
    _set_function(matrix, reserved, 8, 7, ((bits >> 6) & 1) != 0)
    _set_function(matrix, reserved, 8, 8, ((bits >> 7) & 1) != 0)
    _set_function(matrix, reserved, 7, 8, ((bits >> 8) & 1) != 0)
    for i in range(9, 15):
        _set_function(matrix, reserved, 14 - i, 8, ((bits >> i) & 1) != 0)
    for i in range(8):
        _set_function(matrix, reserved, _SIZE - 1 - i, 8, ((bits >> i) & 1) != 0)
    for i in range(8, 15):
        _set_function(matrix, reserved, 8, _SIZE - 15 + i, ((bits >> i) & 1) != 0)
    _set_function(matrix, reserved, 8, _SIZE - 8, True)


def _format_bits(mask: int) -> int:
    data = (0b01 << 3) | mask
    value = data << 10
    for i in range(14, 9, -1):
        if (value >> i) & 1:
            value ^= _FORMAT_POLY << (i - 10)
    return ((data << 10) | value) ^ _FORMAT_MASK


def _place_data_bits(matrix: list[list[bool | None]], reserved: list[list[bool]], bits: list[int]) -> None:
    bit_index = 0
    upward = True
    x = _SIZE - 1
    while x > 0:
        if x == 6:
            x -= 1
        y_range = range(_SIZE - 1, -1, -1) if upward else range(_SIZE)
        for y in y_range:
            for xx in (x, x - 1):
                if reserved[y][xx]:
                    continue
                bit = bits[bit_index] if bit_index < len(bits) else 0
                bit_index += 1
                if (xx + y) % 2 == 0:
                    bit ^= 1
                matrix[y][xx] = bool(bit)
        upward = not upward
        x -= 2


def _set_function(matrix: list[list[bool | None]], reserved: list[list[bool]], x: int, y: int, dark: bool) -> None:
    matrix[y][x] = dark
    reserved[y][x] = True


def _rs_remainder(data: list[int], degree: int) -> list[int]:
    gen = _rs_generator(degree)
    message = data + [0] * degree
    for i, coef in enumerate(data):
        if coef == 0:
            continue
        for j, factor in enumerate(gen):
            message[i + j] ^= _gf_mul(factor, coef)
    return message[-degree:]


def _rs_generator(degree: int) -> list[int]:
    poly = [1]
    for i in range(degree):
        poly = _poly_mul(poly, [1, _gf_pow(2, i)])
    return poly


def _poly_mul(left: list[int], right: list[int]) -> list[int]:
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] ^= _gf_mul(a, b)
    return out


def _gf_pow(value: int, power: int) -> int:
    out = 1
    for _ in range(power):
        out = _gf_mul(out, value)
    return out


def _gf_mul(a: int, b: int) -> int:
    result = 0
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & 0x100:
            a ^= _RS_POLY
    return result & 0xFF


def _codeword_bits(codewords: list[int]) -> list[int]:
    bits: list[int] = []
    for codeword in codewords:
        bits.extend(_int_bits(codeword, 8))
    return bits


def _int_bits(value: int, width: int) -> list[int]:
    return [(value >> i) & 1 for i in range(width - 1, -1, -1)]


def _bits_to_int(bits: list[int]) -> int:
    out = 0
    for bit in bits:
        out = (out << 1) | bit
    return out
