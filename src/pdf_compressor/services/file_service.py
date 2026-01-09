"""Serviço para processamento de arquivos via API"""
import uuid
from pathlib import Path
from typing import List, Dict, Any
from fastapi import UploadFile

from ..repositories.file_repository import FileRepository
from ..services.compression_service import CompressionService
from ..core.config import MIN_OUTPUT_FILE_SIZE
from ..core.logging_config import get_logger
from ..utils.file_utils import get_file_size, format_file_size, calculate_compression_ratio
from ..utils.validators import validate_pdf_file, validate_file_size

logger = get_logger(__name__)


class FileService:
    """Serviço para processamento de arquivos via API"""
    
    def __init__(self, file_repository: FileRepository, compression_service: CompressionService):
        """Inicializa o serviço de arquivos"""
        self.file_repository = file_repository
        self.compression_service = compression_service
    
    async def compress_single_file(
        self,
        file: UploadFile,
        quality: str,
    ) -> Dict[str, Any]:
        """
        Comprime um único arquivo PDF
        
        Args:
            file: Arquivo PDF a ser comprimido
            quality: Nível de qualidade
        
        Returns:
            Dicionário com informações da compressão
        """
        file_id = self.file_repository.generate_file_id()
        input_path = self.file_repository.get_input_path(file_id)
        output_path = self.file_repository.get_output_path(file_id)
        
        try:
            # Ler e validar arquivo
            content = await file.read()
            validate_file_size(len(content))
            
            # Salvar arquivo temporário
            self.file_repository.save_file(file_id, content)
            original_size = len(content)
            
            # Comprimir
            logger.info(f"Comprimindo arquivo {file.filename} (ID: {file_id}) com qualidade '{quality}'")
            success, error = self.compression_service.compress_pdf(
                input_path,
                output_path,
                quality=quality,
                overwrite=True
            )
            
            if not success:
                self.file_repository.delete_all_files(file_id)
                return {
                    "success": False,
                    "error": error or "Falha na compressão",
                    "file_id": None,
                }
            
            # Verificar se o arquivo comprimido é válido
            compressed_size = get_file_size(output_path)
            if compressed_size < MIN_OUTPUT_FILE_SIZE:
                self.file_repository.delete_all_files(file_id)
                return {
                    "success": False,
                    "error": "Arquivo comprimido inválido ou muito pequeno",
                    "file_id": None,
                }
            
            compression_ratio = calculate_compression_ratio(original_size, compressed_size)
            
            logger.info(
                f"Compressão bem-sucedida: {file.filename} "
                f"({format_file_size(original_size)} → {format_file_size(compressed_size)}, "
                f"{compression_ratio:.1f}% redução)"
            )
            
            return {
                "success": True,
                "message": "Compressão concluída com sucesso",
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "original_size_formatted": format_file_size(original_size),
                "compressed_size_formatted": format_file_size(compressed_size),
                "file_id": file_id,
            }
        
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {file.filename}: {str(e)}")
            self.file_repository.delete_all_files(file_id)
            raise
    
    async def compress_batch_files(
        self,
        files: List[UploadFile],
        quality: str,
    ) -> Dict[str, Any]:
        """
        Comprime múltiplos arquivos PDF em lote
        
        Args:
            files: Lista de arquivos PDF a serem comprimidos
            quality: Nível de qualidade
        
        Returns:
            Dicionário com resultados do processamento em lote
        """
        results = []
        total_original_size = 0
        total_compressed_size = 0
        successful = 0
        failed = 0
        
        for file in files:
            file_id = self.file_repository.generate_file_id()
            input_path = self.file_repository.get_input_path(file_id)
            output_path = self.file_repository.get_output_path(file_id)
            
            try:
                # Validar tipo de arquivo
                if not file.filename:
                    results.append({
                        "file_name": "unknown",
                        "success": False,
                        "error": "Nome de arquivo não fornecido",
                        "file_id": None,
                    })
                    failed += 1
                    continue
                
                validate_pdf_file(file.filename)
                
                # Ler e validar tamanho
                content = await file.read()
                validate_file_size(len(content))
                
                # Salvar arquivo
                self.file_repository.save_file(file_id, content)
                original_size = len(content)
                total_original_size += original_size
                
                # Comprimir
                success, error = self.compression_service.compress_pdf(
                    input_path,
                    output_path,
                    quality=quality,
                    overwrite=True
                )
                
                if success:
                    compressed_size = get_file_size(output_path)
                    if compressed_size >= MIN_OUTPUT_FILE_SIZE:
                        compression_ratio = calculate_compression_ratio(original_size, compressed_size)
                        total_compressed_size += compressed_size
                        successful += 1
                        results.append({
                            "file_name": file.filename,
                            "success": True,
                            "error": None,
                            "file_id": file_id,
                            "original_size": original_size,
                            "compressed_size": compressed_size,
                            "compression_ratio": compression_ratio,
                            "original_size_formatted": format_file_size(original_size),
                            "compressed_size_formatted": format_file_size(compressed_size),
                        })
                    else:
                        failed += 1
                        results.append({
                            "file_name": file.filename,
                            "success": False,
                            "error": "Arquivo comprimido inválido",
                            "file_id": None,
                        })
                        self.file_repository.delete_file(file_id, is_output=True)
                else:
                    failed += 1
                    results.append({
                        "file_name": file.filename,
                        "success": False,
                        "error": error or "Falha na compressão",
                        "file_id": None,
                    })
                    self.file_repository.delete_file(file_id, is_output=True)
                
                # Limpar arquivo de entrada após processamento
                self.file_repository.delete_file(file_id, is_output=False)
                
            except Exception as e:
                logger.error(f"Erro ao processar arquivo {file.filename or 'unknown'}: {str(e)}")
                failed += 1
                results.append({
                    "file_name": file.filename or "unknown",
                    "success": False,
                    "error": f"Erro interno: {str(e)}",
                    "file_id": None,
                })
                self.file_repository.delete_all_files(file_id)
        
        overall_compression_ratio = (
            calculate_compression_ratio(total_original_size, total_compressed_size)
            if total_compressed_size > 0
            else 0.0
        )
        
        return {
            "success": successful > 0,
            "message": f"Processados {len(files)} arquivos: {successful} sucessos, {failed} falhas",
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "total_original_size": total_original_size,
            "total_compressed_size": total_compressed_size,
            "overall_compression_ratio": overall_compression_ratio,
            "files": results,
        }

