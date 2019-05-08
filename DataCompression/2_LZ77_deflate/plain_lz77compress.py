# plain_LZ77Compress.py
# Compresses an input file using the LZ77 algorithm (doesn't actually compress, because no further encoding)

import heapq as hq
import sys
import huff_functions as huff

search_capacity = 255
lookahead_capacity = 255
distance_bits = 8
search_size = 0
lookahead_size = 0

if len(sys.argv) == 3:
    inputname = sys.argv[1]
    outputname = sys.argv[2]
elif len(sys.argv) == 2:
    inputname = sys.argv[1]
    outputname = sys.argv[1] + "_compressed"
else:
    print("Please provide at least one argument")
    sys.exit()

text = open(inputname,"rb")
search = bytearray(search_capacity)
lookahead = bytearray(lookahead_capacity)
output = open(outputname,"wb")

# Fill lookahead buffer with first [lookahead_capacity] chars
next_char = text.read(1)
while (lookahead_size != lookahead_capacity) and next_char:
    lookahead[lookahead_size] = int.from_bytes(next_char, byteorder = "big")
    lookahead_size = lookahead_size + 1
    next_char = text.read(1)

# Main compression algorithm loop
while not lookahead_size <= 0:

    print(search)
    print(lookahead)
    
    to_encode = 0 # TO_ENCODE: first char in lookahead not coded for
    offset = 0
    length = 0
    shift = 0
      
    for i in range(len(search) - search_size, len(search)):
        if search[i] == lookahead[to_encode]:
            offset = len(search) - i
            break

    if not offset == 0:
        length = 1
        to_encode = to_encode + 1
        print("offset: " + str(offset) + "/ ")
        while offset > length and search[len(search) - offset + length] == lookahead[to_encode] and not to_encode == lookahead_size - 1:
            to_encode = to_encode + 1
            length = length + 1
            # When loop terminates, length = offset or search[len(search) - offset + length] is first char that doesn't match
        if length == offset:
            while lookahead[length - offset] == lookahead[to_encode] and not to_encode == lookahead_size - 1:
                length = length + 1
                to_encode = to_encode + 1
            # When loop terminates, length = to_encode = lookahead_size or lookahead[length - offset] is first char to not match

        # Write offset and length in 1 byte each, and next char in one byte NOTE: change this for possible smaller buffer? 
        output.write(offset.to_bytes(1, byteorder = "big"))
        output.write(length.to_bytes(1, byteorder = "big"))
        output.write(lookahead[to_encode].to_bytes(1, byteorder = "big"))
            
        #print(offset, length, lookahead[to_encode])
        shift = length + 1
    else:

        output.write(bytes(1))
        output.write(bytes(1))
        output.write(lookahead[to_encode].to_bytes(1, byteorder = "big"))
        #print(0, 0, lookahead[to_encode])
        shift = 1
      
    # Shift lookahead and search buffers

    # Shift search buffer left by [shift] chars, and fill from lookahead
    for i in range(0, len(search) - shift):
        search[i] = search[i+shift]
    for i in range(0, shift):
        search[len(search) - shift + i] = lookahead[i]
    # Increase size of search buffer if not already full
    search_size = search_size + shift
    if search_size >= search_capacity:
        search_size = search_capacity

    # Shift lookahead buffer left by [shift] chars, and fill from text
    for i in range(0, lookahead_size - shift):
        lookahead[i] = lookahead[i + shift]
    lookahead_size = lookahead_size - shift
    for i in range(0, shift):
        if next_char:
            lookahead[len(lookahead) - shift + i] = int.from_bytes(next_char, byteorder = "big")
            lookahead_size = lookahead_size + 1
            next_char = text.read(1)
        else:
            break
