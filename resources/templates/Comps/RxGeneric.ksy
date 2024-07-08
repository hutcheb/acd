meta:
  id: rx_generic
  endian: le

seq:
  - id: parent_id
    type: u4
  - id: unique_tag_identifier
    type: u4
  - id: record_format_version
    type: u2
  - id: cip_type
    type: u2
  - id: comment_id
    type: u2
  - id: main_record
    size: 0x3C
    type:
      switch-on: cip_type
      cases:
        0x6B: rx_tag
        _: unknown
  - id: len_record
    type: u4
  - id: count_record
    type: u4
  - id: extended_records
    type: attribute_record
    repeat: expr
    repeat-expr: count_record - 1
  - id: last_extended_record
    type: last_attribute_record

types:
  attribute_record:
    seq:
      - id: attribute_id
        type: u4
      - id: record_length
        type: u4
      - id: value
        size: record_length
  last_attribute_record:
    seq:
      - id: attribute_id
        type: u4
      - id: record_length
        type: u4
      - id: value
        size: record_length - 4
  rx_tag:
    instances:
      valid:
        value: true
      dimension_1:
        pos: 0x0C
        type: u4
      dimension_2:
        pos: 0x10
        type: u4
      dimension_3:
        pos: 0x14
        type: u4
      data_type:
        pos: 0x1C
        type: u4
      radix:
        pos: 0x20
        type: u2
      external_access:
        pos: 0x22
        type: u2
      data_table_instance:
        pos: 0x24
        type: u4
      cip_data_type:
        pos: 0x34
        type: u2

  unknown:
    seq:
      - id: body
        size: 0x3C

  rx_map_device:
    instances:
      vendor_id:
        pos: 0x02
        type: u2
      product_type:
        pos: 0x04
        type: u2
      product_code:
        pos: 0x06
        type: u2
      parent_module:
        pos: 0x16
        type: u4
      slot_no:
        pos: 0x20
        type: u4
      module_id:
        pos: 0x24
        type: u4
