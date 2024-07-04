meta:
  id: fafa_sbregions
  endian: le
  tags:
    - version: 33
seq:
  - id: record_length
    type: u4
  - id: header
    type: header
  - id: len_record_buffer
    type: u4
  - id: record_buffer
    size: len_record_buffer
types:
  header:
     seq:
      - id: sb_regions
        type: u2
      - id: identifier
        type: u4
      - id: language_type
        type: strz
        size: 41
        encoding: UTF-8
