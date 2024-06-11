meta:
  id: fdfd_comps
  endian: le
  tags:
    - version: 33
seq:
  - id: header
    type: header
  - id: record_buffer
    size: record_length - 155 - 4
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
        type: unicode_16
        size: 124

  unicode_16:
   seq:
     - id: first
       size: 0
       if: start_ >= 0
     - id: c
       type: u2
       repeat: until
       repeat-until: _ == 0
     - id: last
       size: 0
       if: end_ >= 0
   instances:
     start_:
       value: _io.pos
     end_:
       value: _io.pos
     as_string:
       pos: start_
       type: str
       size: end_ - start_
       encoding: UTF-16
params:
  - id: record_length
    type: u4