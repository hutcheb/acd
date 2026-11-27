"""Decode a bounded CommPath value without replacing corrupt UTF-16."""


def decode_comm_path(value):
    text = bytes(value).decode('utf-16-le')
    if text.endswith('\0'):
        text = text[:-1]
    if '\0' in text:
        raise ValueError('Embedded terminator in CommPath')
    return text or None
