meta:
  id: fafa_coments
  endian: le
  tags:
    - version: 33
instances:
  lookup_id:
    pos: 0x1B
    type: u2
  sub_record_type:
    pos: 0x29
    type: u2

seq:
  - id: record_length
    type: u4
  - id: header
    type: header
    size: 12
  - id: body
    type: body(header.string_start_position, lookup_id)

types:
  header:
     instances:
      seq_number:
        pos: 0x00
        type: u2
      string_length:
        pos: 0x02
        type: u2
      string_start_position:
        pos: 0x04
        type: u2
      record_type:
        pos: 0x06
        type: u2
  body:
      params:
        - id: string_start_position
          type: u2
        - id: sub_record_type
          type: u2
      instances:
        record_string_utf8:
          pos: 0x2B
          type: strz
          encoding: UTF-8
          if:  sub_record_type == 0
        record_string_utf16:
          pos: 0x2E
          type: strz_utf_16
          if:  sub_record_type == 1

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