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
     instances:
      oridinal:
        pos: 0x04
        type: u2
      record_type:
        pos: 0x06
        type: u2
      object_id:
        pos: 0x10
        type: u4
      parent_id:
        pos: 0x14
        type: u4
      record_name:
        pos: 0x18
        type: str
        size: 124
        encoding: UTF-16
