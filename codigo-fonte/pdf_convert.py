import subprocess

input_pdf = 'imagens-originais/teste 2.pdf'
output_pdf = 'imagens-originais/teste_4_compactado.pdf'

gs_command = [
    'gswin64c',  # ou 'gswin32c' dependendo do sistema
    '-sDEVICE=pdfwrite',
    '-dCompatibilityLevel=1.4',
    '-dPDFSETTINGS=/screen',  # ou /ebook, /printer, /prepress
    '-dNOPAUSE',
    '-dQUIET',
    '-dBATCH',
    f'-sOutputFile={output_pdf}',
    input_pdf
]

subprocess.run(gs_command)

print("Compactação concluída!")


## Parâmtros adicionais:
# -sDEVICE=pdfwrite → salvar como PDF.
# -dCompatibilityLevel=1.4 → compatível com versões antigas.
# -dPDFSETTINGS=/screen → compactação máxima.
# -sOutputFile="compactado.pdf" → nome do arquivo de saída.
# "original.pdf" → arquivo original.

## Parâmetros de compactação:
# /screen: baixa qualidade, tamanho pequeno 
# /ebook: qualidade média, tamanho médio
# /printer: qualidade alta, tamanho maior
# /prepress: qualidade máxima, tamanho máximo