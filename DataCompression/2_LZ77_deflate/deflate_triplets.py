# DEFLATE.py
# Compresses files with a DEFLATE-ish algorithm. (Working towards compliance.)
# NOTE: output NUMBER of length/literal/etc values before outputting huffman trees
# NOTE: rework length/distance -> code to utilize the pattern ?
# NOTE: change algorithm to only use next_char for non-repeated letters and dist/length for repeats, instead of triples

import heapq as hq
import sys
import huff_functions as huff
import deflate_fns as defl

# -------------------------------------------------------   
# Function that takes care of buffer for writing individual bits to file.
# NOTE: remember to flush buffer before closing
to_write = 0
bits_written = 0

def writebits(n):
    print(n)
    global to_write
    global bits_written
    if n == 0:
        bits_written = bits_written + 1
    else:

        power = 1
        while power * 2 <= n:
            power = power * 2
        
        while power >= 1:
            if n - power >= 0:
                bit = 1
                n = n - power
            else:
                bit = 0
                
            power = power / 2

            bit_flicker = bit << (7-bits_written)
            to_write = to_write | bit_flicker
            bits_written = bits_written + 1

            if bits_written == 8:
                output.write(to_write.to_bytes(1, byteorder = "big"))
                towrite = 0
                bits_written = 0
            
    if bits_written == 8:
        output.write(to_write.to_bytes(1, byteorder = "big"))
        towrite = 0
        bits_written = 0 
            
# -------------------------------------------------------
search_capacity = 32000
search_size = 0

lookahead_capacity = 258
lookahead_size = 0

chars_sent = 0 # Position of next character to send, relative to the start of the file. (Gives a consistent frame of reference for offsets.)

# Read arguments from command line to determine which file to decompress and where to 
if len(sys.argv) == 3:
    inputname = sys.argv[1]
    outputname = sys.argv[2]
elif len(sys.argv) == 2:
    inputname = sys.argv[1]
    outputname = sys.argv[1] + "_deflated"
else:
    print("Please provide at least one argument")
    sys.exit()

# Setup for lookahead and search buffers, and the dictionary "search" (which contains the locations of all the three-length strings encountered)
text = open(inputname, "rb")
search_buffer = bytearray(search_capacity)
lookahead = bytearray(lookahead_capacity)
search = {}

# We use LZ77 algorithm to compute three lists: offsets, lengths and next_chars; will be compressed and sent in triples
offsets = []
lengths = []
next_chars = []

# Fill lookahead buffer with first [lookahead_capacity] chars
next_char = text.read(1)
while (lookahead_size != lookahead_capacity) and next_char:
    lookahead[lookahead_size] = int.from_bytes(next_char, byteorder = "big")
    lookahead_size = lookahead_size + 1
    next_char = text.read(1)

print(lookahead)

# Main LZ77 loop
while not lookahead_size <= 0:

    print("search: " + str(search))
    
    offset = 0
    length = 0
    shift = 0

    # If there are at least three bytes left, search for a match
    if not lookahead_size <= 2:

        # Get first three bytes as string for hashing
        next_three = chr(lookahead[0]) + chr(lookahead[1]) + chr(lookahead[2])

        if not next_three in search:

            print("Sending as literal")
            
            # Send next char as literal
            offsets.append(0)
            lengths.append(0)
            next_chars.append(lookahead[0])
            shift = 1
            
            # String has not been encountered previously, so construct an entry in search with the index of this match
            print("Adding " + next_three + " at index " + str(chars_sent))
            search[next_three] = [chars_sent]

        else:

            print("Attempting to send " + next_three + " as match")
            # print(str(search_buffer))
            print(str(lookahead))

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
                        
            offsets.append(offset)
            lengths.append(length)
            next_chars.append(lookahead[length])
            shift = length + 1

            # Add this index to the entry for next_string
            # (At the beginning, so search will prioritize more recent matches)
            print("Adding " + next_three + " to search at index " + str(chars_sent))
            search[next_three].insert(0, chars_sent)     

    else:
        # Less than three bytes left, so send as literal
        offsets.append(0)
        lengths.append(0)
        next_chars.append(lookahead[0])
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
offsets.append(0)
lengths.append(0)
next_chars.append(256)

print(str(offsets))
print(str(lengths))
print(str(next_chars))

# Constructing huffman tree for lengths and literals
# First count frequencies of codes: 0-255 are literals, 256 is end of block, 257-285 represent lengths (some are ranges of lengths, with extra bits to be placed after symbol)
# Simultaneously, build list of length codes & list of extra bits to append after codes representing ranges of lengths
ll_frequencies = {}
length_codes = []
length_extrabits = []

for nc in next_chars:
    if nc in ll_frequencies:
        ll_frequencies[nc] = ll_frequencies[nc] + 1
    else:
        ll_frequencies[nc] = 1

for l in lengths:
    code = -1
    extrabits = -1
    if l <= 10:
        code = 254 + l
    elif l == 11 or l == 12:
        code = 265
        extrabits = l - 11
    elif l == 13 or l == 14:
        code = 266
        extrabits = l - 13
    elif l == 15 or l == 16:
        code = 267
        extrabits = l - 15
    elif l == 17 or l == 18:
        code = 268
        extrabits = l - 17
    elif l >= 19 and l <= 22:
        code = 269
        extrabits = l - 19
    elif l >= 23 and l <= 26:
        code = 270
        extrabits = l - 23
    elif l >= 27 and l <= 30:
        code = 271
        extrabits = l - 27
    elif l >= 31 and l <= 34:
        code = 272
        extrabits = l - 31
    elif l >= 35 and l <= 42:
        code = 273
        extrabits = l - 35
    elif l >= 43 and l <= 50:
        code = 274
        extrabits = l - 43
    elif l >= 51 and l <= 58:
        code = 275
        extrabits = l - 51
    elif l >= 59 and l <= 66:
        code = 276
        extrabits = l - 59
    elif l >= 67 and l <= 82:
        code = 277
        extrabits = l - 67
    elif l >= 83 and l <= 98:
        code = 278
        extrabits = l - 83
    elif l >= 99 and l <= 114:
        code = 279
        extrabits = l - 99
    elif l >= 115 and l <= 130:
        code = 280
        extrabits = l - 115
    elif l >= 131 and l <= 162:
        code = 281
        extrabits = l - 131
    elif l >= 163 and l <= 194:
        code = 282
        extrabits = l - 163
    elif l >= 195 and l <= 226:
        code = 283
        extrabits = l - 195
    elif l >= 227 and l <= 257:
        code = 284
        extrabits = l - 227
    elif l == 258:
        code = 285

    length_codes.append(code)
    length_extrabits.append(extrabits)
        
    if code in ll_frequencies:
        ll_frequencies[code] = ll_frequencies[code] + 1
    else:
        ll_frequencies[code] = 1

# Build generic huffman tree from frequencies
ll_tree = huff.buildhufftree_full(ll_frequencies)

# Get ordered list of code lengths to create canonical huffman code 
ll_codelengths = huff.getcodelengths(ll_tree)
ll_codelengths_list = huff.lengthslist(range(0, 286), ll_codelengths)
ll_canonical = huff.makecanonical(range(0, 286), ll_codelengths_list)
print(ll_codelengths_list)

# Construct list of code length codes for canonical huffman tree for lengths/literals
ll_codes_plus_extrabits = defl.getcodelengthcodes(ll_codelengths_list)
ll_codelengthcodes = ll_codes_plus_extrabits[0]
ll_repeat_extrabits = ll_codes_plus_extrabits[1]

# Now repeat for distance alphabet
# First, collect distance codes, extra bits, and code frequencies.
dist_frequencies = {}
dist_codes = []
dist_extrabits = []
for dist in offsets:
    code = -1
    extrabits = -1

    if dist == 1:
        code = 0
    elif dist == 2:
        code = 1
    elif dist == 3:
        code = 2
    elif dist == 4:
        code = 3
    elif dist == 5 or dist == 6:
        code = 4
        extrabits = dist - 5
    elif dist == 7 or dist == 8:
        code = 5
        extrabits = dist - 7
    elif dist >= 9 and dist <= 12:
        code = 6
        extrabits = dist - 9
    elif dist >= 13 and dist <= 16:
        code = 7
        extrabits = dist - 13
    elif dist >= 17 and dist <= 24:
        code = 8
        extrabits = dist - 17
    elif dist >= 25 and dist <= 32:
        code = 9
        extrabits = dist - 25
    elif dist >= 33 and dist <= 48:
        code = 10
        extrabits = dist - 33
    elif dist >= 49 and dist <= 64:
        code = 11
        extrabits = dist - 49
    elif dist >= 65 and dist <= 96:
        code = 12
        extrabits = dist - 65
    elif dist >= 97 and dist <= 128:
        code = 13
        extrabits = dist - 97
    elif dist >= 129 and dist <= 192:
        code = 14
        extrabits = dist - 129
    elif dist >= 193 and dist <= 256:
        code = 15
        extrabits = dist - 193
    elif dist >= 257 and dist <= 384:
        code = 16
        extrabits = dist - 257
    elif dist >= 385 and dist <= 512:
        code = 17
        extrabits = dist - 385
    elif dist >= 513 and dist <= 768:
        code = 18
        extrabits = dist - 513
    elif dist >= 769 and dist <= 1024:
        code = 19
        extrabits = dist - 769
    elif dist >= 1025 and dist <= 1536:
        code = 20
        extrabits = dist - 1025
    elif dist >= 1537 and dist <= 2048:
        code = 21
        extrabits = dist - 1537
    elif dist >= 2049 and dist <= 3072:
        code = 22
        extrabits = dist - 2049
    elif dist >= 3073 and dist <= 4096:
        code = 23
        extrabits = dist - 3073
    elif dist >= 4097 and dist <= 6144:
        code = 24
        extrabits = dist - 4097
    elif dist >= 6145 and dist <= 8192:
        code = 25
        extrabits = dist - 6145
    elif dist >= 8193 and dist <= 12288:
        code = 26
        extrabits = dist - 8193
    elif dist >= 12289 and dist <= 16384:
        code = 27
        extrabits = dist - 12289
    elif dist >= 16385 and dist <= 24576:
        code = 28
        extrabits = dist - 16385
    elif dist >= 24577 and dist <= 32768:
        code = 29
        extrabits = dist - 24577
    
    dist_codes.append(code)
    dist_extrabits.append(extrabits)
        
    if code in dist_frequencies:
        dist_frequencies[code] = dist_frequencies[code] + 1
    else:
        dist_frequencies[code] = 1

# Build generic huffman tree from frequencies
dist_tree = huff.buildhufftree_full(dist_frequencies)

# Get ordered list of code lengths to create canonical huffman code 
dist_codelengths = huff.getcodelengths(dist_tree)
dist_codelengths_list = huff.lengthslist(range(0, 30), dist_codelengths)
dist_canonical = huff.makecanonical(range(0, 30), dist_codelengths_list)
print(dist_codelengths_list)

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
clc_canonical = huff.makecanonical(range(0, 19), clc_codelengths_list)
print(clc_canonical)

# Open output stream; towrite is a one-byte buffer, bits_written keeps track of how much of it is full
output = open(outputname, "wb")

# Currently we are putting all data in one dynamically compressed block
# So write BFINAL = 1 and BTYPE = 0b10 to the buffer, to signify that it is final and dynamically compressed
writebits(6)

# Output code lengths for clc tree in this weird order
for i in [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]:
    writebits(clc_codelengths_list[i])


# Create list of all clcs, ll and dist together
codelengthcodes = ll_codelengthcodes + dist_codelengthcodes
all_extrabits = ll_repeat_extrabits + dist_repeat_extrabits
print(codelengthcodes)
print(all_extrabits)

# Then output clcs using canonical huffman code
extrabits_index = 0
for code in codelengthcodes:
    writebits(clc_canonical[code])
    if code >= 16:
        writebits(all_extrabits[extrabits_index])
        extrabits_index = extrabits_index + 1

# The decompressor can now construct the canonical huffman codes for code length codes, then use that to construct the canonical huffman codes for lengths/literals and distances. So data can actually be output now, taken from lists offsets, lengths, and next_chars and then encoded with the appropriate huffman code (extra bits added if necessary)
