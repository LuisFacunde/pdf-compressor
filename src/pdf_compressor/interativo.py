import sys
import time
import multiprocessing
from pathlib import Path

# Importa as funções do seu projeto existente
from pdf_compressor.compressor import compress_pdf_batch
from pdf_compressor.config import QUALITY_SETTINGS

def pause_exit():
    input("\nPressione Enter para sair...")
    sys.exit()

def main():
    print("="*60)
    print("      COMPRESSOR DE PDFS MÉDICOS - FUNDAÇÃO ALTINO VENTURA")
    print("="*60)
    print("Este programa irá COMPRIMIR e SUBSTITUIR os arquivos originais.")
    print("-" * 60)

    # 1. Pergunta o diretório
    while True:
        target_dir_str = input("\n>> Digite o caminho da pasta com os exames: ").strip()
        # Remove aspas que o Windows costuma adicionar ao copiar como caminho
        target_dir_str = target_dir_str.replace('"', '').replace("'", "")
        
        target_dir = Path(target_dir_str)

        if target_dir.exists() and target_dir.is_dir():
            break
        else:
            print(f"❌ Erro: A pasta '{target_dir_str}' não foi encontrada. Tente novamente.")

    # 2. Confirmação de segurança
    print(f"\n⚠️  ATENÇÃO: Todos os PDFs na pasta (e subpastas):")
    print(f"   📂 {target_dir}")
    print("   Serão comprimidos e SUBSTITUÍDOS pelos novos arquivos.")
    
    confirm = input("\nTem certeza que deseja continuar? (S/N): ").lower()
    if confirm != 's':
        print("Operação cancelada pelo usuário.")
        pause_exit()

    # 3. Execução
    print("\n🚀 Iniciando compressão (Nível: Prepress - Recomendado para exames)...")
    
    # Usa a função compress_pdf_batch original do seu projeto
    # in_place=True garante a substituição dos arquivos originais
    successful, failed = compress_pdf_batch(
        input_dir=target_dir,
        output_dir=None,     # Ignorado no modo in_place
        quality="prepress",  # Qualidade recomendada no seu README
        overwrite=True,
        show_progress=True,
        in_place=True        # Ativa o modo de substituição recursiva
    )

    print("-" * 60)
    if failed == 0 and successful > 0:
        print(f"✅ Sucesso! {successful} arquivos foram otimizados.")
    else:
        print(f"🏁 Finalizado. Sucessos: {successful} | Falhas: {failed}")
        if failed > 0:
            print("Verifique o arquivo de log para detalhes dos erros.")

    pause_exit()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    try:
        main()
    except Exception as e:
        print(f"\n❌ Ocorreu um erro crítico: {e}")
        import traceback
        traceback.print_exc()
        pause_exit()