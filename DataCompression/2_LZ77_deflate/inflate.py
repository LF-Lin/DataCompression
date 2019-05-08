# INFLATE.PY
# Decompresses files compressed with deflate_not3
# Theoretically.

import heapq as hq
import sys
import bitstring as bs
import huff_functions as huff
import deflate_fns as defl

# -------------------------------------------------------------
# Function that takes care of buffer for reading individual bits from file
cur_byte = 0
bits_read = 0

# Returns the next n bits as an integer
def readbits(n):
    global cur_byte
    global bits_read
    
    read = 0;
    for i in range(0, n):
        bit_getter = 1 << (7 - bits_read)
        bit = bit_getter & cur_byte
        if bit != 0:
            bit = 1
            
        read = read * 2
        read = read + bit
        bits_read = bits_read + 1

        if bits_read == 8:
            bits_read = 0
            cur_byte = int.from_bytes(text.read(1), byteorder = "big")

    return read

# -----------------------------------------------------------

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
output = open(outputname, "wb")
cur_byte = int.from_bytes(text.read(1), byteorder = "big")
    
# First read in btype (currently we are only sending one block & it is dynamically compressed, so it will always be a 3-bit 6)
btype = readbits(3)
print(btype)

clc_codelengths = {}

# Read in code lengths for clc tree, which are printed in this weird order
for i in [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]:
    clc_codelengths[i] = readbits(3)

clc_codelengths_list = []
for i in range(0, 19):
    clc_codelengths_list.append(clc_codelengths[i])
print(clc_codelengths_list)

# Construct canonical huffman code for code length codes
clc_canonical = huff.makecanonical(range(0, 19), clc_codelengths_list)
print(clc_canonical)
clc_canonical_tree = huff.makecanonicaltree(clc_canonical)
print(clc_canonical_tree)

# Use this code to decode code lengths for length/literal and distance trees
# 286 length/literal code lengths and 30 distance code lengths
# But some codes are followed by extra bits to specify position in a range
ll_codelengths_list = []
prev = -1

while not len(ll_codelengths_list) == 286:

    # Read bits and navigate in decoding tree until we reach a leaf node
    leafreached = False
    currentnode = clc_canonical_tree
    while not leafreached:
        if (not currentnode[1]) and (not currentnode[2]):
            leafreached = True
        else:
            nextbit = bs.BitArray(uint = readbits(1), length = 1)
            if not nextbit[0]:
                currentnode = currentnode[1]
            else:
                currentnode = currentnode[2]

    length_code = currentnode[0]
    print(length_code)
    
    if length_code < 16:
        # Represent literally code lengths of 0-15
        ll_codelengths_list.append(length_code)
        prev = length_code
    elif length_code == 16:
        # 16 followed by 2 extra bits represents prev code repeated 3-6 times
        extrabits = readbits(2)
        numrepeats = 3 + extrabits
        for i in range(0, numrepeats):
            ll_codelengths_list.append(prev)
    elif length_code == 17:
        # 17 followed by 3 extra bits represents 0 repeated 3-10 times
        extrabits = readbits(3)
        numrepeats = 3 + extrabits
        for i in range(0, numrepeats):
            ll_codelengths_list.append(prev)
    elif length_code == 18:
        # 18 followed by 7 extra bits represents 0 repeated 11-138 times
        extrabits = readbits(7)
        numrepeats = 11 + extrabits
        for i in range(0, numrepeats):
            ll_codelengths_list.append(prev)
    else:
        print("error")

print(ll_codelengths_list)

dist_codelengths_list = []
prev = -1

while not len(dist_codelengths_list) == 30:

    # Read bits and navigate in decoding tree until we reach a leaf node
    leafreached = False
    currentnode = clc_canonical_tree
    while not leafreached:
        if (not currentnode[1]) and (not currentnode[2]):
            leafreached = True
        else:
            nextbit = bs.BitArray(uint = readbits(1), length = 1)
            if not nextbit[0]:
                currentnode = currentnode[1]
            else:
                currentnode = currentnode[2]

    length_code = currentnode[0]
    print(length_code)
    
    if length_code < 16:
        # Represent literally code lengths of 0-15
        dist_codelengths_list.append(length_code)
        prev = length_code
    elif length_code == 16:
        # 16 followed by 2 extra bits represents prev code repeated 3-6 times
        extrabits = readbits(2)
        numrepeats = 3 + extrabits
        for i in range(0, numrepeats):
            dist_codelengths_list.append(prev)
    elif length_code == 17:
        # 17 followed by 3 extra bits represents 0 repeated 3-10 times
        extrabits = readbits(3)
        numrepeats = 3 + extrabits
        for i in range(0, numrepeats):
            dist_codelengths_list.append(prev)
    elif length_code == 18:
        # 18 followed by 7 extra bits represents 0 repeated 11-138 times
        extrabits = readbits(7)
        numrepeats = 11 + extrabits
        for i in range(0, numrepeats):
            dist_codelengths_list.append(prev)
    else:
        print("error")

print(dist_codelengths_list)

# Construct canonical huffman code and decoding tree for length/literal codes
ll_canonical = huff.makecanonical(range(0, 286), ll_codelengths_list)
ll_canonical_tree = huff.makecanonicaltree(ll_canonical)

# Construct canonical huffman code and decoding tree for distance codes
dist_canonical = huff.makecanonical(range(0, 30), dist_codelengths_list)
dist_canonical_tree = huff.makecanonicaltree(dist_canonical)

# Finally, DECODE DATA
# NOTE: Adapt this to multi-block structure

lls = []
distances = []
while True:
    
    print(lls)
    print(distances)
    
    # Decode a length/literal value
    leafreached = False
    currentnode = ll_canonical_tree
    while not leafreached:
        if (not currentnode[1]) and (not currentnode[2]):
            leafreached = True
        else:
            nextbit = bs.BitArray(uint = readbits(1), length = 1)
            if not nextbit[0]:
                currentnode = currentnode[1]
            else:
                currentnode = currentnode[2]

    ll = currentnode[0]
    print("Literal/coded length: " + str(ll))
        
    # If value < 256, it's a literal; otherwise length
    if ll < 256:
        lls.append(ll)
    else:
        num_extrabits = defl.length_code_num_extrabits(ll)
        print("Num extra bits for length: " + str(num_extrabits))
        if num_extrabits != 0:
            extrabits = readbits(num_extrabits)
        else:
            extrabits = -1
        length = defl.length_decode(ll, extrabits)
        lls.append(length)
        print("Extra bits: " + str(extrabits))
        print("Decoded length: " + str(length))
        if length == 256:
            break

        # Decode a distance value 
        leafreached = False
        currentnode = dist_canonical_tree
        while not leafreached:
            if (not currentnode[1]) and (not currentnode[2]):
                leafreached = True
            else:
                nextbit = bs.BitArray(uint = readbits(1), length = 1)
                if not nextbit[0]:
                    currentnode = currentnode[1]
                else:
                    currentnode = currentnode[2]

        dist_code = currentnode[0]
        print("Coded distance: " + str(dist_code))
        num_extrabits = defl.dist_code_num_extrabits(dist_code)
        if num_extrabits != 0:
            extrabits = readbits(num_extrabits)
        else:
            extrabits = -1
        print("Distance extra bits: " + str(extrabits))
        dist = defl.dist_decode(dist_code, extrabits)
        print("Decoded distance: " + str(dist))
        distances.append(dist)
        print(extrabits)

print(lls)
print(distances)
        
        
