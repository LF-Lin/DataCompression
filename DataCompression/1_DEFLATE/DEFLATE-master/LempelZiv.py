def prep_text(filename):
	text = open(filename, 'rU')
	text_raw = text.readlines()
	chars = []
	for line in text_raw:
		chars.extend(line)

	return chars

def encode(chars, windowlen):
	l = ['%']*windowlen
	chars = l + chars
	coded = ''

	window = l #reversal better reflects that we're reading back into encoded characters

	i = windowlen
	while i <len(chars):
		window = list(reversed(chars[i - windowlen:i]))
		n = 1

		if chars[i] in window:
			reverse = window.index(chars[i]) + 1#how far to go back from i
			i = i+1
			while i< len(chars) and chars[i] == chars[(i-reverse)]:
				n = n+1
				i = i+1

			coded = coded + str(('1'+'$'+str(reverse)+'$'+str(n)))+'='

		else:
			coded = coded + str(('0'+'$'+chars[i]))+'='
			i = i+1

	coded = coded[0:len(coded)-1]

	return coded

def decode(message):

	message = message.split('=')
	plaintext = []

	for element in message:
		element = tuple(element.split('$'))
		if len(element)>1:
			if element[0] == '0':
				plaintext.append(element[1])
			else:
				for i in range(0,int(element[2])):
					plaintext.append(plaintext[len(plaintext)-int(element[1])])
	plaintext = ''.join(plaintext)

	return plaintext



if __name__ == '__main__':
	m = encode((prep_text('test_text.txt')),110)
	print(decode(m))




