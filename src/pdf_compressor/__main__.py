import argparse
import sys
from pathlib import Path
from .config import INPUT_DIR, OUTPUT_DIR
from .compressor import compress_pdf, compress_pdf_batch

def validate_directory(path: Path, create_if_missing: bool = False) -> bool:
    """Validate directory exists or can be created."""
    if path.exists():
        if not path.is_dir():
            print(f"Error: {path} exists but is not a directory")
            return False
        return True
    elif create_if_missing:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {path}: {e}")
            return False
    else:
        print(f"Error: Directory {path} does not exist")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Compressor de PDFs de exames médicos da Fundação Altino Ventura",
        epilog="""
Exemplos de uso:
  %(prog)s                                    # Comprimir todos os PDFs da pasta padrão
  %(prog)s -q screen                         # Compressão máxima (menor qualidade)  
  %(prog)s -i ./meus_pdfs -o ./comprimidos  # Pastas customizadas
  %(prog)s --single arquivo.pdf saida.pdf   # Comprimir arquivo único
  %(prog)s -j 8                             # Usar 8 processadores paralelos
  %(prog)s --no-progress                    # Sem barra de progresso
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Grupos para processamento paralelo de arquivos
    batch_group = parser.add_argument_group('processamento em lote')
    batch_group.add_argument(
        "-i", "--input-dir",
        type=Path, default=INPUT_DIR,
        help=f"pasta dos PDFs originais (padrão: {INPUT_DIR})"
    )
    batch_group.add_argument(
        "-o", "--output-dir",
        type=Path, default=OUTPUT_DIR,
        help=f"pasta de saída para PDFs comprimidos (padrão: {OUTPUT_DIR})"
    )
    
    # Grupo para processamento individual de arquivo
    single_group = parser.add_argument_group('arquivo único')
    single_group.add_argument(
        "--single", nargs=2, metavar=('INPUT', 'OUTPUT'),
        help="comprimir um único arquivo: --single entrada.pdf saida.pdf"
    )
    
    # Opções comuns
    parser.add_argument(
        "-q", "--quality",
        choices=["screen", "ebook", "printer", "prepress", "default"],
        default="prepress",
        help="""nível de compressão:
        screen: máxima compressão, menor qualidade (ideal para visualização)
        ebook: compressão alta, qualidade média (recomendado para arquivos médicos)
        printer: compressão média, qualidade alta
        prepress: compressão baixa, qualidade máxima (padrão)
        default: configuração padrão do Ghostscript"""
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="sobrescrever arquivos de saída existentes"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="modo verboso (mais detalhes nos logs)"
    )
    parser.add_argument(
        "-j", "--jobs", type=int, metavar="N",
        help="número de processadores paralelos (padrão: detecção automática)"
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="desabilitar barra de progresso"
    )
    
    args = parser.parse_args()
    
    # Configura nível de logs
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle single file processing
    if args.single:
        input_file = Path(args.single[0])
        output_file = Path(args.single[1])
        
        print(f"Comprimindo arquivo único: {input_file.name}")
        success, error = compress_pdf(
            input_file, 
            output_file, 
            quality=args.quality,
            overwrite=args.overwrite
        )
        
        if success:
            print("✅ Compressão concluída com sucesso!")
            return 0
        else:
            print(f"❌ Falha na compressão: {error}")
            return 1
    
    # Handle batch processing
    else:
        # Validação do diretório de entrada
        if not validate_directory(args.input_dir, create_if_missing=False):
            return 1
        
        # Valida/Cria diretório de saída
        if not validate_directory(args.output_dir, create_if_missing=True):
            return 1
        
        print(f"📁 Pasta de entrada: {args.input_dir}")
        print(f"📁 Pasta de saída: {args.output_dir}")
        print(f"🎛️  Qualidade: {args.quality}")
        
        # Mostra informações de processamento paralelo
        if args.jobs:
            print(f"⚡ Processadores: {args.jobs}")
        else:
            import os
            cpu_count = os.cpu_count() or 2
            max_workers = min(4, cpu_count)
            print(f"⚡ Processadores: {max_workers} (automático)")
        
        print("-" * 50)
        
        successful, failed = compress_pdf_batch(
            args.input_dir,
            args.output_dir,
            quality=args.quality,
            overwrite=args.overwrite,
            max_workers=args.jobs,
            show_progress=not args.no_progress
        )
        
        print("-" * 50)
        if failed == 0:
            print(f"✅ Todos os {successful} arquivos foram comprimidos com sucesso!")
            return 0
        else:
            print(f"⚠️  {successful} sucessos, {failed} falhas")
            return 1

if __name__ == "__main__":
    sys.exit(main())