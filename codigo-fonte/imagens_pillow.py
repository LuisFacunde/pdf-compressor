import PIL
from PIL import Image

imagem = Image.open('c:/Users/luis.silva/Desktop/compactador-de-imagens/imagens-originais/trabalhador.jpg')

width = imagem.width // 2
height = imagem.height // 2

print("Dimensões originais da imagem:", round(len(imagem.fp.read())/1024,2), "KB")

imagem = imagem.resize((width, height), PIL.Image.NEAREST)
imagem.save('c:/Users/luis.silva/Desktop/compactador-de-imagens/imagens-compactadas/trabalhador_50%.jpg')

imagem_compress = Image.open('c:/Users/luis.silva/Desktop/compactador-de-imagens/imagens-compactadas/trabalhador_50%.jpg')
print("Dimensões da imagem redimensionada:", round(len(imagem_compress.fp.read())/1024,2), "KB")
