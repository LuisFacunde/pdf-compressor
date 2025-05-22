import PIL
from PIL import Image

imagem = Image.open('imagens-originais/trabalhador.jpg')
tamanho = (imagem.width // 2, imagem.height // 2)

print("Dimensões originais da imagem:", round(len(imagem.fp.read())/1024,2), "KB")

imagem = imagem.resize((tamanho), PIL.Image.NEAREST)
imagem.save('imagens-compactadas/trabalhador_50%.jpg')

imagem_compress = Image.open('imagens-compactadas/trabalhador_50%.jpg')
print("Dimensões da imagem redimensionada:", round(len(imagem_compress.fp.read())/1024,2), "KB")
