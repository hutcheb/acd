meta:
  id: rx_map_device
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
        0: v0
        162: v162
        173: v173
        _: v_unknown

types:
  v_unknown:
    instances:
      valid:
        value: false
  v0:
    instances:
      valid:
        value: false
  v162:
    instances:
      valid:
        value: true
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
  v173:
    instances:
      valid:
        value: true
      record_length:
        pos: 0x4A
        type: u4
      record_count:
        pos: 0x4E
        type: u2
      records:
        pos: 0x50
        size: 0x0C
        repeat: expr
        repeat-expr: record_count
      vendor_id:
        pos: (0x50 + (record_count*0x0C))
        type: u2
      product_type:
        pos: (0x50 + 0x02 + (record_count*0x0C))
        type: u2
      product_code:
        pos: (0x50 + 0x04 + (record_count*0x0C))
        type: u2
      parent_module:
        pos: ((0x50 + (record_count*0x0C)) + 0x14)
        type: u4
      slot_no:
        pos: ((0x50 + 0x04 + (record_count*0x0C)) + 0x16)
        type: u4
      module_id:
        pos: ((0x50 + 0x04 + (record_count*0x0C)) + 0x26)
        type: u4