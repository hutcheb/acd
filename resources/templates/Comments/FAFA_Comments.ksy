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
    size: 0x0A
  - id: body
    size: record_length - 0x0A
    type:
      switch-on: header.record_type
      cases:
        0x01: ascii_record
        0x02: ascii_record
        0x03: utf_16_record(0x0C)
        0x04: utf_16_record(0x0C)
        0x0d: utf_16_record(0x0C)
        0x0e: utf_16_record(0x0C)
        0x17: controller_record
        0x19: controller_record


types:
  header:
     instances:
      seq_number:
        pos: 0x00
        type: u2
      record_type:
        pos: 0x02
        type: u2
      sub_record_length:
        pos: 0x04
        type: u2
      parent:
        pos: 0x06
        type: u4
  ascii_record:
      seq:
        - id: unknown_1
          size: 0x0D
        - id: object_id
          type: u4
        - id: unknown_2
          size: 0x0D
        - id: record_string
          type: strz
          encoding: UTF-8
  ascii_record_4:
    seq:
      - id: unknown_1
        size: 0x08
      - id: object_id
        type: u4
      - id: unknown_2
        size: 0x18
      - id: record_string
        type: strz
        encoding: UTF-8
  utf_16_record:
      params:
      - id: zero_buffer_length
        type: u4
      seq:
        - id: unknown_1
          size: 0x08
        - id: object_id
          type: u4
        - id: unknown_2
          size: 0x04
        - id: len_record
          type: u2
        - id: tag_reference
          type: strz_utf_16
        - id: unknown_3
          size: zero_buffer_length
        - id: record_string
          type: strz
          encoding: UTF-8
  controller_record:
      seq:
        - id: unknown_1
          size: 0x08
        - id: object_id
          type: u4
        - id: unknown_2
          size: 0x04
        - id: tag_reference
          type: strz_utf_16
        - id: unknown_3
          size: 0x0C
        - id: record_string
          type: strz
          encoding: UTF-8

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