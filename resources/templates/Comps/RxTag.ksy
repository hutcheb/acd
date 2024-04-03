meta:
  id: rx_tag
  endian: le
  tags:
    - version: 60
instances:
  first_array_dimension:
    pos: 0xAE
    type: u4
  second_array_dimension:
    pos: 0xB2
    type: u4
  third_array_dimension:
    pos: 0xB6
    type: u4
  data_type_id:
    pos: 0xBE
    type: u4
  tag_name_length:
    pos: 0xEE
    type: u2
  tag_name:
    pos: 0xF0
    type: str
    size: tag_name_length
    encoding: UTF-8

seq:
  - id: header
    type: header
  - id: parent_id
    type: u4
  - id: unique_tag_identifier
    type: u4
types:
  header:
    seq:
      - id: length
        type: u4
      - id: blank_1
        type: u4
      - id: seq_number
        type: u2
      - id: record_type
        type: u2
      - id: blank_2
        type: u4
      - id: object_id
        type: u4
      - id: parent_id
        type: u4
      - id: name
        type: str
        size: 124
        encoding: UTF-16
 