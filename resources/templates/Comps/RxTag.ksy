meta:
  id: rx_tag
  endian: le

seq:
  - id: parent_id
    type: u4
  - id: unique_tag_identifier
    type: u4
  - id: record_format_version
    type: u2
  - id: comment_id
    type: u4
  - id: body
    type:
      switch-on: record_format_version
      cases:
        60: v60
        63: v63
        _: v_unknown

types:
  v_unknown:
    instances:
      valid:
        value: false
  v60:
    instances:
      valid:
        value: true
      dimension_1:
        pos: 0x1A
        type: u4
      dimension_2:
        pos: 0x1E
        type: u4
      dimension_3:
        pos: 0x22
        type: u4
      data_type:
        pos: 0x2A
        type: u4
      data_table_instance:
        pos: 0x32
        type: u2
      cip_data_type:
        pos: 0x42
        type: u2
      tag_name_length:
        pos: 0x5A
        type: u2
      name:
        pos: 0x5C
        type: str
        size: tag_name_length
        encoding: UTF-8
      logical_path:
        pos: 0x29A
        type: logical_path
  v63:
    instances:
      valid:
        value: true
      dimension_1:
        pos: 0x1A
        type: u4
      dimension_2:
        pos: 0x1E
        type: u4
      dimension_3:
        pos: 0x22
        type: u4
      data_type:
        pos: 0x2A
        type: u4
      data_table_instance:
        pos: 0x32
        type: u2
      cip_data_type:
        pos: 0x42
        type: u2
      number_of_records:
        pos: 0x4E
        type: u4
      tag_name_length:
        pos: 0x4E + (0xC * number_of_records)
        type: u2
      name:
        pos: 0x4E + (0xC * number_of_records) + 2
        type: str
        size: tag_name_length
        encoding: UTF-8
      logical_path:
        pos: 0x29A
        type: logical_path

  logical_path:
    seq:
      - id: position_0
        type: u4
      - id: position_1
        type: u4
      - id: position_2
        type: u4
      - id: position_3
        type: u4
      - id: position_4
        type: u4

