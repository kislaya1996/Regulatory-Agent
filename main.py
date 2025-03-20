from parser import Parser

pdf_path = ""
parser = Parser(pdf_path)
elements, text = parser.parse()
print(elements)
print(text)
