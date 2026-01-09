"""Repositório para gerenciamento de arquivos temporários"""
import tempfile
import uuid
from pathlib import Path
from typing import Optional


class FileRepository:
    """Gerencia arquivos temporários para processamento"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Inicializa o repositório de arquivos"""
        if base_dir is None:
            base_dir = Path(tempfile.gettempdir()) / "pdf_compressor"
        
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_file_id(self) -> str:
        """Gera um ID único para um arquivo"""
        return str(uuid.uuid4())
    
    def get_input_path(self, file_id: str) -> Path:
        """Retorna o caminho do arquivo de entrada"""
        return self.base_dir / f"{file_id}_input.pdf"
    
    def get_output_path(self, file_id: str) -> Path:
        """Retorna o caminho do arquivo de saída"""
        return self.base_dir / f"{file_id}_compressed.pdf"
    
    def save_file(self, file_id: str, content: bytes) -> Path:
        """Salva um arquivo temporário"""
        input_path = self.get_input_path(file_id)
        input_path.write_bytes(content)
        return input_path
    
    def file_exists(self, file_id: str, is_output: bool = False) -> bool:
        """Verifica se um arquivo existe"""
        path = self.get_output_path(file_id) if is_output else self.get_input_path(file_id)
        return path.exists()
    
    def delete_file(self, file_id: str, is_output: bool = False) -> bool:
        """Remove um arquivo temporário"""
        path = self.get_output_path(file_id) if is_output else self.get_input_path(file_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def delete_all_files(self, file_id: str) -> None:
        """Remove todos os arquivos relacionados a um ID"""
        self.delete_file(file_id, is_output=False)
        self.delete_file(file_id, is_output=True)
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """Remove arquivos temporários mais antigos que max_age_hours"""
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        for file_path in self.base_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
        
        return deleted_count

