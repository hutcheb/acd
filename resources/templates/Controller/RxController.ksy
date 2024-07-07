meta:
  id: rx_controller
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
        95: v95
        103: v103
        _: v_unknown

types:
  v_unknown:
    instances:
      valid:
        value: false
  v95:
    instances:
      valid:
        value: true
      len_record:
        type: u4
        pos: 0x4A
      record:
        pos: 0x4A
        size: (len_record)
      len_current_active:
        type: u4
        pos: 0x147
      current_acive:
        pos: 0x14B
        type: str
        size: len_current_active
        encoding: utf-16
      len_most_recent:
        type: u4
        pos: 0x16B
      most_recent:
        pos: 0x16F
        type: str
        size: len_most_recent
        encoding: utf-16
      serial_number:
        type: u4
        pos: 0x1CB
  v103:
    instances:
      valid:
        value: true
      len_record:
        type: u4
        pos: 0x4A
      record:
        pos: 0x4A
        size: len_record
      len_sfc_execution_control:
        type: u4
        pos: 0xC4
      sfc_execution_control:
        pos: 0xC8
        type: str
        size: len_current_active
        encoding: utf-16
      len_sfc_restart_position:
        type: u4
        pos: 0xE8
      sfc_restart_position:
        pos: 0xEC
        type: str
        size: len_most_recent
        encoding: utf-16
      serial_number:
        type: u4
        pos: 0x148
      len_path:
        type: u4
        pos: 0x180
      path:
        pos: 0x184
        type: str
        size: len_path
        encoding: utf-16