import sys
import argparse
from pathlib import Path
from src.config import INPUT_DIR, OUTPUT_DIR
from src.compressor import compress_pdf, compress_pdf_batch


def validate_directory(path: Path, create_if_missing: bool = False) -> bool:
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
            %(prog)s                                  # Comprimir todos os PDFs da pasta padrão
            %(prog)s -i ./exames --in-place -q ebook  # Comprimir recursivamente no local
            %(prog)s -q screen                        # Compressão máxima (menor qualidade)  
            %(prog)s -i ./meus_pdfs -o ./comprimidos  # Pastas customizadas
            %(prog)s --single arquivo.pdf saida.pdf   # Comprimir arquivo único
            %(prog)s -j 8                             # Usar 8 processadores paralelos
            %(prog)s --no-progress                    # Sem barra de progresso
                    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    batch_group = parser.add_argument_group("processamento em lote")
    batch_group.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=INPUT_DIR,
        help=f"pasta dos PDFs originais (padrão: {INPUT_DIR})",
    )
    batch_group.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"pasta de saída para PDFs comprimidos (padrão: {OUTPUT_DIR})",
    )
    batch_group.add_argument(
        "--in-place",
        action="store_true",
        help="comprimir arquivos recursivamente no mesmo local, sobrescrevendo os originais. Ignora --output-dir.",
    )

    single_group = parser.add_argument_group("arquivo único")
    single_group.add_argument(
        "--single",
        nargs=2,
        metavar=("INPUT", "OUTPUT"),
        help="comprimir um único arquivo: --single entrada.pdf saida.pdf",
    )

    parser.add_argument(
        "-q",
        "--quality",
        choices=["screen", "ebook", "printer", "prepress", "default"],
        default="prepress",
        help="""
        Nível de compressão:
        screen: máxima compressão, menor qualidade (ideal para visualização)
        ebook: compressão alta, qualidade média (recomendado para arquivos médicos)
        printer: compressão média, qualidade alta
        prepress: compressão baixa, qualidade máxima (padrão)
        default: configuração padrão do Ghostscript
        """,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="sobrescrever arquivos de saída existentes (padrão no modo --in-place)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="modo verboso (mais detalhes nos logs)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        metavar="N",
        help="número de processadores paralelos (padrão: detecção automática)",
    )
    parser.add_argument(
        "--no-progress", action="store_true", help="desabilitar barra de progresso"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="reprocessar arquivos --in-place mesmo que o histórico indique que já foram comprimidos",
    )
    parser.add_argument(
        "--history",
        nargs="?",
        const="",
        metavar="PASTA",
        help="exibir o histórico de compressões (opcionalmente filtrado por pasta) e sair",
    )

    args = parser.parse_args()

    if args.history is not None:
        from src.history import get_history

        rows = get_history(folder=args.history or None)
        if not rows:
            print("Histórico vazio.")
        for r in rows:
            print(
                f"{r['compressed_at']} | {r['status']:<13} | {r['quality']:<8} | "
                f"{r['original_size']} -> {r['compressed_size']} B "
                f"({r['reduction_percent']:.1f}%) | {r['file_path']}"
            )
        return 0

    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    if args.single:
        input_file = Path(args.single[0])
        output_file = Path(args.single[1])

        print(f"Comprimindo arquivo único: {input_file.name}")
        success, error = compress_pdf(
            input_file, output_file, quality=args.quality, overwrite=args.overwrite
        )

        try:
            from src.history import STATUS_COMPRESSED, STATUS_FAILED, record_compression

            record_compression(
                input_file,
                status=STATUS_COMPRESSED if success else STATUS_FAILED,
                mode="single",
                quality=args.quality,
                original_size=input_file.stat().st_size if input_file.exists() else 0,
                compressed_size=output_file.stat().st_size if success else 0,
                output_path=output_file if success else None,
                error=error,
            )
        except Exception as e:
            print(f"Aviso: falha ao gravar histórico: {e}")

        if success:
            print("✅ Compressão concluída com sucesso!")
            return 0
        else:
            print(f"❌ Falha na compressão: {error}")
            return 1

    else:
        if not validate_directory(args.input_dir):
            return 1

        if not args.in_place:
            if not validate_directory(args.output_dir, create_if_missing=True):
                return 1

        if args.in_place:
            print(f"🚀 Modo 'In-Place' ativado.")
            print(f"📁 Pasta raiz para busca: {args.input_dir}")
            args.overwrite = True
        else:
            print(f"📁 Pasta de entrada: {args.input_dir}")
            print(f"📁 Pasta de saída: {args.output_dir}")

        print(f"🎛️  Qualidade: {args.quality}")

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
            show_progress=not args.no_progress,
            in_place=args.in_place,
            force=args.force,
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
