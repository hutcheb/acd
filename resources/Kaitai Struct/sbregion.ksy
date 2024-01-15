meta:
  id: sbregion
  title: SBRegion.dat file extracted from an RSLogix 5000 ACD
  file-extension: dat
  license: CC0-1.0
  ks-version: 0.9
  endian: le
  bit-endian: le
doc: |
  Docs for ACD File Format
doc-ref:
  - URL Reference?
#unknown pre header info
#maybe magic number?
#and something else?
seq:
  - id: header
    type: header
  - id: unknown_data_between_header_and_records
    type: u4
    repeat: expr
    repeat-expr: (header.region_pointer_offset / 4) - 7
  - id: record_header_info
    type: record_header_info
    #repeat: expr
    #expression should eventually be header.num_of_records + header.table2_num_of_records
    #repeat-expr: 1
  - id: unknown_data_between_recheadinfo_and_records
    type: u4
    repeat: expr
    repeat-expr: (header.region_pointer_offset / 4) - 7
    

types:
  header:
    seq:
      - id: hd_unk_1
        type: u4
      - id: hd_unk_2
        type: u4
      - id: total_length
        doc: Total Length of the file? (records?) in bytes
        type: u4
      - id: region_pointer_offset
        type: u4
      - id: header_unknown_1
        type: u4
      - id: num_of_records
        type: u4
      - id: table2_num_of_records
        type: u4
  record_header_info:
    seq:
      - id: rec_magic_number
        contents: [0xfe, 0xfe]
      - id: record_header_length
        type: u4
      - id: record_unknown_1
        type: u4
      - id: record_unknown_2
        type: u4
      #In the python program there were only 2 known values here
      #132 -> Cross Reference Database if I understand the exception comment correctly
      #512 -> ...?
      - id: record_format
        type: u4
  record:
    seq:
      