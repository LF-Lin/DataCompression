# DEFLATE.py
# Compresses files with a DEFLATE-ish algorithm. (Working towards compliance.)
# Working to send data as length/offset pairs and literals, instead of offset/length/nextchar triples
# NOTE: output NUMBER of length/literal/etc values before outputting huffman trees
# NOTE: rework length/distance -> code to utilize the pattern ?

import heapq as hq
import bitstring as bs
import sys
import huff_functions as huff
import deflate_fns as defl

# -------------------------------------------------------   
# Function that takes care of buffer for writing individual bits to file.
# NOTE: remember to flush buffer before closing
to_write = 0
bits_written = 0

# Writes the number "data" as an n-bit binary integer
def writebits(data, n):
    
    global to_write
    global bits_written

    data_bits = bs.Bits(uint=data, length=n)

    for i in range(0, n):
        if(data_bits[i]):
            bit = 1
        else:
            bit = 0
            
        bit_flicker = bit << (7-bits_written)
        to_write = to_write | bit_flicker
        bits_written = bits_written + 1

        if bits_written == 8:
            output.write(to_write.to_bytes(1, byteorder = "big"))
            to_write = 0
            bits_written = 0

def writebitstring(data):
    global to_write
    global bits_written

    for i in range(0, len(data)):
        if(data[i]):
            bit = 1
        else:
            bit = 0
            
        bit_flicker = bit << (7-bits_written)
        to_write = to_write | bit_flicker
        bits_written = bits_written + 1

        if bits_written == 8:
            output.write(to_write.to_bytes(1, byteorder = "big"))
            to_write = 0
            bits_written = 0
    
# ------------------------------------------------------
search_capacity = 32000
search_size = 0

lookahead_capacity = 258
lookahead_size = 0

chars_sent = 0 # Position of next character to send, relative to the start of the file. (Gives a consistent frame of reference for offsets.)

# Read arguments from command line to determine which file to decompress and where to 
inputname = "examples/test2.bmp"
outputname = "examples/test2_compressed.txt"

#elif len(sys.argv) == 2:
#    inputname = sys.argv[1]
#    outputname = sys.argv[1] + "_compressed"
#else:
#    print("Please provide at least one argument")
#    sys.exit()

# Setup for lookahead and search buffers, and the dictionary "search" (which contains the locations of all the three-length strings encountered)
text = open(inputname, "rb")
search_buffer = bytearray(search_capacity)
lookahead = bytearray(lookahead_capacity)
search = {}

# We use the LZ77 algorithm to compute some lists:
# Coded lengths and literals
# Extra bits for length codes that specify a range of lengths
# Distance offset codes for each length
# Extra bits for distance codes that specify a range of distances
lens_lits = []
len_extrabits = []
distances = []
dist_extrabits = []

# Fill lookahead buffer with first [lookahead_capacity] chars
next_char = text.read(1)
while (lookahead_size != lookahead_capacity) and next_char:
    lookahead[lookahead_size] = int.from_bytes(next_char, byteorder = "big")
    lookahead_size = lookahead_size + 1
    next_char = text.read(1)

# Main LZ77 loop
while not lookahead_size <= 0:

    print(lookahead)
    print("search: " + str(search))
    
    offset = 0
    length = 0
    shift = 0

    # If there are at least three bytes left, search for a match
    if not lookahead_size <= 2:

        # Get first three bytes as string for hashing
        next_three = chr(lookahead[0]) + chr(lookahead[1]) + chr(lookahead[2])

        if not next_three in search:

            print("Sending" + str(lookahead[0]) + "as literal")
            
            # Send next char as literal
            lens_lits.append(lookahead[0])
            shift = 1
            
            # String has not been encountered previously, so construct an entry in search with the index of this match
            print("Adding " + next_three + " at index " + str(chars_sent))
            search[next_three] = [chars_sent]

        else:

            print("Attempting to send " + next_three + " as match")

            # Look through all matches for the longest recent one
            # NOTE: Take care of case where only matches are >32000 back
            length = 3
            matches = search[next_three]
            offset = chars_sent - matches[0]
            for match in matches:

                print("Examining match at " + str(match))
                
                cur_length = 3
                cur_offset = chars_sent - match

                if not cur_offset >= 32000: 
                
                    # Compare characters [cur_length] into lookahead and [cur_length]
                    # until 1) they don't match 2) we spill out of search buffer
                    # 3) we're matching entire lookahead buffer
                    while cur_offset > cur_length and search_buffer[len(search_buffer) - cur_offset + cur_length] == lookahead[cur_length] and not cur_length == lookahead_size - 1:
                        cur_length = cur_length + 1

                    # Then if 2) happened, compare with beginning of lookahead
                    if cur_offset <= cur_length:

                        print("Spilling over into lookahead buffer...")
                        
                        while lookahead[cur_length - cur_offset] == lookahead[cur_length] and not cur_length == lookahead_size - 1:
                            cur_length = cur_length + 1

                    # If this is new longest match, store it in length/offset
                    if cur_length > length:
                        length = cur_length
                        offset = cur_offset

                print("... which has offset " + str(cur_offset) + " and length " + str(cur_length))

            dist_code = defl.dist_code(offset)
            distances.append(dist_code[0])
            dist_extrabits.append(dist_code[1])
            length_code = defl.length_code(length)
            lens_lits.append(length_code[0])
            len_extrabits.append(length_code[1])
            shift = length

            # Add this index to the entry for next_string
            # (At the beginning, so search will prioritize more recent matches)
            print("Adding " + next_three + " to search at index " + str(chars_sent))
            search[next_three].insert(0, chars_sent)

    else:
        # Less than three bytes left, so send as literal
        lens_lits.append(lookahead[0])
        shift = 1
            
    # Shift lookahead and search buffers, and add three-strings to search as we
    # watch them go by

    # Shift search buffer left by [shift] chars, and fill from lookahead
    for i in range(0, len(search_buffer) - shift):
        search_buffer[i] = search_buffer[i+shift]
    for i in range(0, shift):
        search_buffer[len(search_buffer) - shift + i] = lookahead[i]
    # Increase size of search buffer if not already full
    search_size = search_size + shift
    if search_size >= search_capacity:
        search_size = search_capacity

    # Get and save three-strings up to the one that will be examined in next loop
    for i in range(1, shift):
        if i <= lookahead_size - 3:
            next_three = chr(lookahead[i]) + chr(lookahead[i+1]) + chr(lookahead[i+2]);
            print("Examining string " + next_three + " at index " + str(i))

            if next_three in search:
                search[next_three].insert(0, chars_sent + i)
            else:
                search[next_three] = [chars_sent + i]
        else:
            break

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

    chars_sent = chars_sent + shift

# Write an end-of-block character (there will only be one of these right now since it's all in one block)
length_code = defl.length_code(256)
lens_lits.append(length_code[0])
len_extrabits.append(length_code[1])

print(str(lens_lits))
print(str(len_extrabits))
print(str(distances))
print(str(dist_extrabits))

# Constructing huffman tree for lengths and literals
# First count frequencies of codes: 0-255 are literals, 256 is end of block, 257-285 represent lengths (some represent a range of lengths)
ll_frequencies = {}

for ll in lens_lits:
    if ll in ll_frequencies:
        ll_frequencies[ll] = ll_frequencies[ll] + 1
    else:
        ll_frequencies[ll] = 1

# Build generic huffman tree from frequencies
ll_tree = huff.buildhufftree_full(ll_frequencies)

# Get ordered list of code lengths to create canonical huffman code 
ll_codelengths = huff.getcodelengths(ll_tree)
ll_codelengths_list = huff.lengthslist(range(0, 286), ll_codelengths)
ll_canonical = huff.makecanonical(range(0, 286), ll_codelengths_list)
#print(ll_codelengths_list)
#print("LL_CANONICAL: " + str(ll_canonical))

# Construct list of code length codes for canonical huffman tree for lengths/literals
ll_codes_plus_extrabits = defl.getcodelengthcodes(ll_codelengths_list)
ll_codelengthcodes = ll_codes_plus_extrabits[0]
ll_repeat_extrabits = ll_codes_plus_extrabits[1]

# Now repeat for distance alphabet
# First, collect distance codes, extra bits, and code frequencies.
dist_frequencies = {}

for dist in distances:
    if dist in dist_frequencies:
        dist_frequencies[dist] = dist_frequencies[dist] + 1
    else:
        dist_frequencies[dist] = 1

# Build generic huffman tree from frequencies
dist_tree = huff.buildhufftree_full(dist_frequencies)

# Get ordered list of code lengths to create canonical huffman code 
dist_codelengths = huff.getcodelengths(dist_tree)
dist_codelengths_list = huff.lengthslist(range(0, 30), dist_codelengths)
dist_canonical = huff.makecanonical(range(0, 30), dist_codelengths_list)
#print(dist_codelengths_list)

# Construct list of code length codes for canonical huffman tree for distances
dist_codes_plus_extrabits = defl.getcodelengthcodes(dist_codelengths_list)
dist_codelengthcodes = dist_codes_plus_extrabits[0]
dist_repeat_extrabits = dist_codes_plus_extrabits[1]

# Compress ALL code length codes with ANOTHER canonical huffman code
# First collect frequencies from both ll and dist code length code lists
clc_frequencies = {}
for code in ll_codelengthcodes:
    if code in clc_frequencies:
        clc_frequencies[code] = clc_frequencies[code] + 1
    else:
        clc_frequencies[code] = 1

for code in dist_codelengthcodes:
    if code in clc_frequencies:
        clc_frequencies[code] = clc_frequencies[code] + 1
    else:
        clc_frequencies[code] = 1

clc_tree = huff.buildhufftree_full(clc_frequencies)

# Get ordered list of code lengths to create canonical huffman code 
clc_codelengths = huff.getcodelengths(clc_tree)
clc_codelengths_list = huff.lengthslist(range(0, 19), clc_codelengths)
#print("clc_codelengths_list: " + str(clc_codelengths_list))
clc_canonical = huff.makecanonical(range(0, 19), clc_codelengths_list)
#print(clc_canonical)

# Open output stream; towrite is a one-byte buffer, bits_written keeps track of how much of it is full
output = open(outputname, "wb")

# Currently we are putting all data in one dynamically compressed block
# So write BFINAL = 1 and BTYPE = 0b10 to the buffer, to signify that it is final and dynamically compressed
writebits(6, 3)

# Output code lengths for clc tree in this weird order
for i in [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]:
    writebits(clc_codelengths_list[i], 3)

# Create list of all clcs, ll and dist together
codelengthcodes = ll_codelengthcodes + dist_codelengthcodes
all_extrabits = ll_repeat_extrabits + dist_repeat_extrabits
#print(codelengthcodes)
#print(all_extrabits)

# Then output clcs using canonical huffman code
extrabits_index = 0
for code in codelengthcodes:
    writebitstring(clc_canonical[code])
    if code == 16:
        writebits(all_extrabits[extrabits_index], 2)
        extrabits_index = extrabits_index + 1
    if code == 17:
        writebits(all_extrabits[extrabits_index], 3)
        extrabits_index = extrabits_index + 1
    if code == 18:
        writebits(all_extrabits[extrabits_index], 7)
        extrabits_index = extrabits_index + 1
        
# The decompressor can now construct the canonical huffman codes for code length codes, then use that to construct the canonical huffman codes for lengths/literals and distances. So data can actually be output now, taken from lists lens_lits and distances and then encoded with the appropriate huffman code (extra bits added if necessary)
num_tuples = 0 # Number of length/distance pairs sent
for ll in lens_lits:
    writebitstring(ll_canonical[ll])
    if ll > 256:
        if len_extrabits[num_tuples] != -1:
            print(len_extrabits[num_tuples])
            writebits(len_extrabits[num_tuples], defl.length_code_num_extrabits(ll))
        # If this is not the last length (the EOB code) then also print distance
        if not num_tuples == len(distances):
            writebitstring(dist_canonical[distances[num_tuples]])
            if dist_extrabits[num_tuples] != -1:
                cur_dist_code = distances[num_tuples]
                writebits(dist_extrabits[num_tuples], defl.dist_code_num_extrabits(cur_dist_code))
        num_tuples = num_tuples + 1


output.write(to_write.to_bytes(1, byteorder = "big"))
output.close()
