meta:
  id: fdfd_comps
  endian: le
  tags:
    - version: 33
seq:
  - id: header
    type: header
    size: 155
  - id: record_buffer
    size: record_length - 155 - 8
types:
  header:
    instances:
      seq_number:
        pos: 0x04
        type: u2
      record_type:
        pos: 0x0A
        type: u2
      object_id:
        pos: 0x10
        type: u4
      parent_id:
        pos: 0x14
        type: u4
      record_name:
        pos: 0x18
        type: strz_utf_16
        size: 124

  strz_utf_16:
    seq:
      - id: value
        size: 2 * (code_units.size - 1)
        type: str
        encoding: utf-16le
      - id: term
        type: u2
        valid: 0
    instances:
      code_units:
        pos: _io.pos
        type: u2
        repeat: until
        repeat-until: _ == 0
params:
  - id: record_length
    type: u4