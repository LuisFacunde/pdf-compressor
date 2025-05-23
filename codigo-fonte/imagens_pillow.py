import PIL
from PIL import Image

imagem = Image.open('imagens-originais/pagina_teste2_1.jpg')
tamanho = (imagem.width // 2, imagem.height // 2)

print("Dimensões originais da imagem:", round(len(imagem.fp.read())/1024,2), "KB")

imagem = imagem.resize((tamanho), PIL.Image.NEAREST)
imagem.save('imagens-compactadas/pagina_teste2_1_50%.jpg')

imagem_compress = Image.open('imagens-compactadas/pagina_teste2_1_50%.jpg')
print("Dimensões da imagem redimensionada:", round(len(imagem_compress.fp.read())/1024,2), "KB")

## Parâmetros de compressão:
# NEAREST: menor qualidade, maior compressão
# BOX: qualidade média, compressão média
# BILINEAR: qualidade média, compressão média
# HAMMING: qualidade média, compressão média
# BICUBIC: qualidade alta, compressão baixa
# LANCZOS: qualidade alta, compressão baixa
# Resampling: qualidade alta, compressão baixa