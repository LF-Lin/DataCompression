# plain_LZ77Decompress.py
# Decompresses a compressed file written with the LZ77 algorithm, with 3-byte (length, character, distance) triples written in sequence

import heapq as hq
import sys
import huff_functions as huff

search_capacity = 255
distance_bits = 8
search_size = 0

if len(sys.argv) == 3:
    inputname = sys.argv[1]
    outputname = sys.argv[2]
elif len(sys.argv) == 2:
    inputname = sys.argv[1]
    outputname = sys.argv[1] + "_decompressed"
else:
    print("Please provide at least one argument")
    sys.exit()

text = open(inputname,"rb")
search = bytearray(search_capacity)
output = open(outputname,"wb")
to_write = bytearray(8)

# Main decompression loop
cur_byte = text.read(1)
while cur_byte:

    print(search)
    
    # First get an offset, then a length, then a next char
    offset = int.from_bytes(cur_byte, byteorder = "big")
    cur_byte = text.read(1)
    length = int.from_bytes(cur_byte, byteorder = "big")
    cur_byte = text.read(1)
    next_char = cur_byte

    print("Offset: " + str(offset))
    print("Length: " + str(length))
    print("Next char: " + str(next_char))
    
    # If offset = 0, then just append next char & shift search buffer
    if offset == 0:
        print(next_char)
        output.write(next_char)

        # Shift search buffer left one
        for j in range(0, len(search) - 1):
            search[j] = search[j+1]
        search[len(search) - 1] = int.from_bytes(next_char, byteorder = "big")

    else:
        # Otherwise, append the character [offset] chars back & shift buffer,
        # [length] times
        for i in range(0, length):
            char = search[len(search)-offset]
            print(char)
            output.write(char.to_bytes(1, byteorder = "big"))
            
            # Shift search buffer left one
            for j in range(0, len(search) - 1):
                search[j] = search[j+1]
            search[len(search) - 1] = char

        # Then write next_char and shift once more to finish
        print(next_char)
        output.write(next_char)
        # Shift search buffer left one
        for j in range(0, len(search) - 1):
            search[j] = search[j+1]
        search[len(search) - 1] = int.from_bytes(next_char, byteorder = "big")
            
    cur_byte = text.read(1)
    
output.close()
