meta:
  id: rx_tag
  endian: le
  tags:
    - version: 60
instances:
  first_array_dimension:
    pos: 0x1A
    type: u4
  second_array_dimension:
    pos: 0x1E
    type: u4
  third_array_dimension:
    pos: 0x22
    type: u4
  data_type_id:
    pos: 0x2A
    type: u4
  hidden:
    pos: 0x32
    type: u2
  tag_name_length:
    pos: 0x5A
    type: u2
  cip_data_type:
    pos: 0x42
    type: u2
  tag_name:
    pos: 0x5C
    type: str
    size: tag_name_length
    encoding: UTF-8

seq:
  - id: parent_id
    type: u4
  - id: unique_tag_identifier
    type: u4
  - id: record_format_version
    type: u2
 