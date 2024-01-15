meta:
  id: sbregion
  title: SBRegion.dat file extracted from an RSLogix 5000 ACD
  file-extension: dat
  license: CC0-1.0
  ks-version: 0.9
  endian: le
  bit-endian: le
doc: |
  Docs for sbregion.dat of ACD File Format
doc-ref:
  - URL Reference?
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
      - id: rec_magic_num
        type: u2
        #contents: [0xfa, 0xfa]
      - id: length
        type: u4
      - id: identifier
        type: u4
      #based on the python code this 6 bytes shouldn't exist...but it looks like it does
        # or I've screwed something else up, because my alignment is off by 6 bytes
      - id: erroneous_6_bytes
        type: u1
        repeat: expr
        repeat-expr: 6
      # Lang Type values I've seen so far while testing (with a single ACD file)
      #    - REGION LE UID
      #        - the text for these come back as gibberish or a foreign language...must be binary not text
      #    - Rung NT
      #        - The text from what I've seen is clearly rung text
      #    - REGION NT
      #       - also looks like Rung text...not sure what the difference is here between this and Rung NT
      #    - REGION_MANGLED_SPECIFIER
      #        - So in the Rung text instead of tags it uses some sort of identifier surrounded by @ symbols
      #        - For example:
      #            - OTL(@d2e1f164@)
      #            - EQU(@361c9540@.@b7ca3c9b@[@475fa515@].@31a4059f@.@9d3d011d@,0)
      #        - In these region mangled specifiers it all just these identifiers
      #        - Such as
      #            - @8d186df7@
      #            - @080668b4@[2]
      #            - @2a060d86@.@f9255b24@
      #        - So I'm getting these are tag references of some sort...but how exactly they refer back to
      #        - a tag is unclear at the moment
      #    - REGION_REF_COUNT
      #        - In every single one of these the text field appeared to be empty (or had unprintable bytes)
      #    - REGION AST
      #        - the text for these come back as gibberish or a foreign language...must be binary not text
      #        - Doing a quick glance...it looks like it could have some UTF-8 in the data
      - id: lang_type
        type: str
        size: 29
        encoding: UTF-8
      - id: rec_unknown_1
        type: u1
        repeat: expr
        repeat-expr: 12
      - id: text_length
        type: u4
      # I'm not seeing any errors in the Katai IDE, but when I did a quick test
      # with the python generated parser, I was getting some errors about some
      # records text not being parsable as UTF-16
      - id: text
        type: str
        size: text_length
        encoding: UTF-16LE
        #encoding: UTF-8
        