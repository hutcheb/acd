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
  - id: unknown_data_between_header_and_region
    type: u4
    repeat: expr
    repeat-expr: (header.region_pointer_offset / 4) - 7
  - id: region_info
    type: region_info
  - id: unknown_data_between_header_and_rec_info
    type: u1
    repeat: expr
    repeat-expr: region_info.pointer_records_region - header.region_pointer_offset  - 22
  - id: record_info
    type: record_info
  - id: records
    type: record
    repeat: expr
    repeat-expr: header.num_of_records + header.table2_num_of_records
    #repeat-expr: 2
    
    

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
  region_info:
    seq:
      - id: region_magic_number
        contents: [0xfe, 0xfe]
      - id: region_pointer_length
        type: u4
      - id: region_unknown_1
        type: u4
      - id: region_unknown_2
        type: u4
      - id: pointer_metadata_region
        type: u4
      - id: pointer_records_region
        type: u4
  record_info:
    seq:
      - id: rec_magic_number
        contents: [0xfe, 0xfe]
      - id: record_info_length
        type: u4
      - id: record_info_unknown_1
        type: u4
      - id: record_info_unknown_2
        type: u4
      #In the python program there were only 2 known values here
      #132 -> Cross Reference Database if I understand the exception comment correctly
      #512 -> ...?rungs?
      - id: record_format
        type: u4
      - id: record_info_unknown_remaining
        type: u1
        repeat: expr
        repeat-expr: record_info_length - 18 
  record:
    seq:
      - id: identifier
        contents: [0xfa, 0xfa]
      - id: rec_length
        type: u4
      - id: rec_bytes
        type: u1
        repeat: expr
        repeat-expr: rec_length - 6