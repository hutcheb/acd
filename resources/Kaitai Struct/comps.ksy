meta:
  id: comps_dat
  title: Comps.dat file extracted from an RSLogix 5000 ACD
  file-extension: dat
  license: CC0-1.0
  ks-version: 0.9
  endian: le
  bit-endian: le
doc: |
  Docs for Comps.dat of ACD File Format
doc-ref:
  - URL Reference?
seq:
  - id: magic_number_maybe
    type: u4
    repeat: expr
    repeat-expr: 2
  - id: header
    type: header
  - id: unknown_data_between_header_and_records
    type: u1
    repeat: expr
    repeat-expr: header.region_pointer_offset - 28
  - id: region_header
    type: region_header
  - id: unknown_betw_reghead_and_region
    type: u1
    repeat: expr
    repeat-expr: region_header.pointer_records_region - header.region_pointer_offset - 22
  - id: record_header
    type: record_header
  - id: unknown_between_head_and_rec
    type: u1
    repeat: expr
    repeat-expr: 36 #self.pointer_records_region + self.record_header_length
  - id: records
    type: record
    repeat: expr
    #repeat-expr: 2 #self.header.no_records + self.header.no_records_table2
    repeat-expr: header.num_records + header.num_records_table2
  
types:
  header:
    seq:
      - id: total_length
        type: u4
      - id: region_pointer_offset
        type: u4
      - id: header_unknown_1
        type: u4
      - id: num_records
        type: u4
      - id: num_records_table2
        type: u4
  region_header:
    seq:
      - id: magic_num
        contents: [0xfe, 0xfe]
      - id: region_pointer_length
        type: u4
      - id: rec_header_unknown_1
        type: u4
      - id: rec_header_unknown_2
        type: u4
      - id: pointer_metadata_region
        type: u4
      - id: pointer_records_region
        type: u4
  record_header:
    seq:
      - id: magic_num
        contents: [0xfe, 0xfe]
      - id: record_header_length
        type: u4
      - id: unknown4
        type: u4
      - id: unknown5
        type: u4
      - id: record_format
        type: u4
        enum: record_format
    enums:
      record_format:
        #there might be other types, but these are the 2 in the python file
        #and I haven't dug too deep yet in my sample files
        132: xfer_db
        512: tag_record_i_presume
  record:
    seq:
      #- id: header
      #  type: record_header
      #- id: unknwon_between_head_and_ident
      #  type: u1
      #  repeat: expr
      #  repeat-expr: 36 #self.pointer_records_region + self.record_header_length
      - id: identifier
        type: u2
      - id: length
        type: u4
      - id: data
        type:
          switch-on: identifier
          cases:
            0xFAFA: dat_record
            0xFDFD: ptr_dat_record
  dat_record:
    seq:
      - id: length
        type: u4
      - id: dat_rec_unknown_1
        type: u4
      - id: sequence_number
        type: u2
      - id: record_type
        type: u2
        #enum: ?
      - id: dat_rec_unknown_2
        type: u4
      - id: obj_id
        type: u4
      - id: parent_id_offset
        type: u4
      - id: rec_text
        type: str
        size: 124
        encoding: UTF-16LE
      - id: unknown_remaining_rec_data
        type: u1
        repeat: expr
        repeat-expr: length - 144
  ptr_dat_record:
    # Not sure what this is specifically, but it appears there aren't any in
    # The sample program I'm testing with currently. Perhaps these are Aliases?
    # I would have to check if this program has any aliases.
    seq:
      - id: ptr_rec_unknown_1
        type: u4
        repeat: expr
        repeat-expr: 2
      - id: sequence_number
        type: u2
     - id: record_type
        type: u2
        #enum: ?
      - id: ptr_dat_rec_unknown_2
        type: u4
      - id: obj_id
        type: u4
      - id: parent_id_offset
        type: u4
      - id: rec_text
        type: str
        size: 124
        encoding: UTF-16LE
      # since I have no examples of this currently, I'm not sure if this is the
      #end of the record or not. The python code stops reading bytes at this point
      #but it also did for the data record and there is no length field in this one
      #or perhaps there is since the python code jups over the first 8 bytes of
      # the ptr record, and the first 4 are the length in the other one...
      # I would need an example to try and test agains though.
      # hell honestly these 2 record types are 99% identical.
      # It's possible these could get merged, but for now I'll leave them seperate