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
  - id: record_buffer
    size: record_length - 144 - 4
types:
  header:
     seq:
      - id: sb_regions
        type: u2

