meta:
  id: dat
  endian: le
  tags:
    - version: 33
instances:
  
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
  - id: records
    type: records
    size: header.file_length - header.first_record_position + 1
types:
  header:
    seq:
      - id: format_type
        type: u4
      - id: blank_2
        type: u4
      - id: file_length
        type: u4
      - id: first_record_position
        type: u4
      - id: blank_3
        type: u4
      - id: number_records_fafa
        type: u4
      - id: header_buffer
        type: u1
        repeat: expr
        repeat-expr: first_record_position - 24
  records:
    seq:
      - id: record
        type: record
        repeat: eos
  record:
    seq:
      - id: identifier
        type: u2
        valid:
          any-of: [0xFEFE, 0xFDFD, 0xFAFA, 0xFBBF]
      - id: record_length
        type: u4
      - id: record
        size: record_length - 6
        type:
          switch-on: identifier
          cases:
            0xFAFA: fafa_record(record_length - 6)
            0xFDFD: fdfd_record(record_length - 6)
            0xFEFE: fefe_record
            0xFBBF: bffb_record(record_length - 6)

  fafa_record:
    params:
      - id: record_length
        type: u4
    seq:
      - id: record_buffer
        size: record_length
  bffb_record:
    params:
      - id: record_length
        type: u4
    seq:
      - id: record_buffer
        size: record_length
  fdfd_record:
    params:
      - id: record_length
        type: u4
    seq:
      - id: record_buffer
        size-eos: true
  fefe_record:
    seq:
      - id: record_length
        type: u4
      - id: blank_1
        type: u4
      - id: unknown_1
        type: u4
      - id: unknown_2
        type: u4
      - id: record_buffer
        size: record_length
