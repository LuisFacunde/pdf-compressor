import subprocess

def compress_pdf(input_file, output_file, quality='screen'):
    # Qualidades possíveis: screen, ebook, printer, prepress, default
    try:
        subprocess.run([
            'gswin64c', 
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/' + quality,
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={output_file}',
            input_file
        ], check=True)
        print("PDF comprimido com sucesso!")
    except subprocess.CalledProcessError as e:
        print("Erro na compressão:", e)

compress_pdf('pdfs_originais/Retinografia.pdf', 'pdfs_compactados/Retinografia_default.pdf', quality='default')

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