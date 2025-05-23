import PIL
from PIL import Image

imagem = Image.open('imagens-originais/trabalhador.jpg')
tamanho = (imagem.width // 2, imagem.height // 2)

print("Dimensões originais da imagem:", round(len(imagem.fp.read())/1024,2), "KB")

imagem = imagem.resize((tamanho), PIL.Image.LANCZOS)
imagem.save('imagens-compactadas/trabalhador_compress.jpg')

imagem_compress = Image.open('imagens-compactadas/trabalhador_compress.jpg')
print("Dimensões da imagem redimensionada:", round(len(imagem_compress.fp.read())/1024,2), "KB")

## Parâmetros de compressão:
# NEAREST: menor qualidade, maior compressão
# BOX: qualidade média, compressão média
# BILINEAR: qualidade média, compressão média
# HAMMING: qualidade média, compressão média
# BICUBIC: qualidade alta, compressão baixa
# LANCZOS: qualidade alta, compressão baixa
# Resampling: qualidade alta, compressão baixa

## Qualide/Desempenho dos métodos de redimensionamento:
# Image.NEAREST | Redução da qualidade: nenhuma | Qualidade de upscaling: nenhuma | Desempenho: excelente (★★★★★).
# Image.BOX | Redução da qualidade: baixa (★) | Qualidade de upscaling: nenhuma | Desempenho: muito bom (★★★★☆).
# Image.BILINEAR | Redução da qualidade: baixa (★) | Qualidade de upscaling: baixa (★) | Desempenho: muito bom (★★★★☆).
# Image.HAMMING | Redução da qualidade: moderada (★★) | Qualidade de upscaling: nenhuma | Desempenho: muito bom (★★★★☆).
# Image.BICUBIC | Redução da qualidade: boa (★★★) | Qualidade de upscaling: boa (★★★) | Desempenho: razoável (★★★☆).
# Image.LANCZOS | Redução da qualidade: excelente (★★★★) | Qualidade de upscaling: excelente (★★★★★) | Desempenho: baixo (★☆).