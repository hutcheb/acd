meta:
  id: fafa_comps
  endian: le
  tags:
    - version: 33
seq:
  - id: record_length
    type: u4
  - id: header
    type: header
  - id: record_buffer
    size: record_length - 144 - 4
types:
  header:
    seq:
      - id: unknown_1
        type: u4
      - id: seq_number
        type: u2
      - id: record_type
        type: u2
      - id: unknown_4
        type: u2
      - id: unknown_5
        type: u2
      - id: object_id
        type: u4
      - id: parent_id
        type: u4
      - id: record_name
        type: str
        size: 124
        encoding: UTF-16