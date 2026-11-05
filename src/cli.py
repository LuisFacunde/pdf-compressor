import argparse
import sys
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
from .adapters.ghostscript import GhostscriptEngine
from .adapters.sqlite_history import SqliteHistory
from .logging_setup import setup_logging
from .models import Mode, Quality
from .ports import CompressionEngine
from .services import BatchCompressor, FileCompressor, default_workers
from .settings import Settings, get_settings


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


def build_parser(settings: Settings) -> argparse.ArgumentParser:
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
            %(prog)s --history                        # Exibir histórico de compressões
                    """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    batch_group = parser.add_argument_group("processamento em lote")
    batch_group.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        default=settings.input_dir,
        help=f"pasta dos PDFs originais (padrão: {settings.input_dir})",
    )
    batch_group.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=settings.output_dir,
        help=f"pasta de saída para PDFs comprimidos (padrão: {settings.output_dir})",
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
        choices=[q.value for q in Quality],
        default=Quality.PREPRESS.value,
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
    return parser


def _print_history(history: SqliteHistory, folder: Optional[str]) -> int:
    rows = history.query(folder=folder or None)
    if not rows:
        print("Histórico vazio.")
    for r in rows:
        print(
            f"{r['compressed_at']} | {r['status']:<13} | {r['quality']:<8} | "
            f"{r['original_size']} -> {r['compressed_size']} B "
            f"({r['reduction_percent']:.1f}%) | {r['file_path']}"
        )
    return 0


def main(
    argv: Optional[List[str]] = None,
    settings: Optional[Settings] = None,
    engine: Optional[CompressionEngine] = None,
    configure_logging: bool = True,
) -> int:
    settings = settings or get_settings()
    args = build_parser(settings).parse_args(argv)

    history = SqliteHistory(settings.history_db)

    if args.history is not None:
        return _print_history(history, args.history)

    if configure_logging:
        setup_logging(verbose=args.verbose, log_file=settings.log_file)

    if args.jobs is not None and args.jobs < 1:
        print("Error: --jobs deve ser maior que zero")
        return 1

    if engine is None:
        gs = GhostscriptEngine(settings.ghostscript_cmd, settings.timeout)
        if not gs.is_available():
            print(
                "❌ Ghostscript não encontrado. Instale o Ghostscript e garanta que "
                f"'{gs.command}' esteja no PATH."
            )
            return 1
        engine = gs

    file_compressor = FileCompressor(engine, settings.min_output_size)

    if args.single:
        input_file = Path(args.single[0])
        output_file = Path(args.single[1])

        print(f"Comprimindo arquivo único: {input_file.name}")
        result = file_compressor.compress_to(
            input_file,
            output_file,
            args.quality,
            overwrite=args.overwrite,
            mode=Mode.SINGLE,
        )

        try:
            history.record(result, args.quality)
        except Exception as e:
            print(f"Aviso: falha ao gravar histórico: {e}")

        if result.success:
            print("✅ Compressão concluída com sucesso!")
            return 0
        print(f"❌ Falha na compressão: {result.error}")
        return 1

    if not validate_directory(args.input_dir):
        return 1

    if not args.in_place:
        if not validate_directory(args.output_dir, create_if_missing=True):
            return 1

    if args.in_place:
        print("🚀 Modo 'In-Place' ativado.")
        print(f"📁 Pasta raiz para busca: {args.input_dir}")
        args.overwrite = True
    else:
        print(f"📁 Pasta de entrada: {args.input_dir}")
        print(f"📁 Pasta de saída: {args.output_dir}")

    print(f"🎛️  Qualidade: {args.quality}")
    if args.jobs:
        print(f"⚡ Processadores: {args.jobs}")
    else:
        print(f"⚡ Processadores: {default_workers()} (automático)")
    print("-" * 50)

    progress = (
        None if args.no_progress else tqdm(desc="Comprimindo PDFs", unit="arquivo")
    )
    try:
        summary = BatchCompressor(file_compressor, history).run(
            args.input_dir,
            args.output_dir,
            args.quality,
            overwrite=args.overwrite,
            in_place=args.in_place,
            force=args.force,
            max_workers=args.jobs,
            on_result=(lambda _result: progress.update(1)) if progress else None,
        )
    finally:
        if progress is not None:
            progress.close()

    print("-" * 50)
    if summary.failed == 0:
        print(
            f"✅ Todos os {summary.successful} arquivos foram comprimidos com sucesso!"
        )
        return 0
    print(f"⚠️  {summary.successful} sucessos, {summary.failed} falhas")
    return 1


if __name__ == "__main__":
    sys.exit(main())
