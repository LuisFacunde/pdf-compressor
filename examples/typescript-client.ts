/**
 * Cliente TypeScript para a API de Compressão de PDFs
 * 
 * Exemplo de uso:
 * ```typescript
 * const client = new PDFCompressorClient('http://localhost:8000');
 * const result = await client.compressFile(file, 'prepress');
 * ```
 */

export interface CompressionResponse {
  success: boolean;
  message: string;
  original_size?: number;
  compressed_size?: number;
  compression_ratio?: number;
  original_size_formatted?: string;
  compressed_size_formatted?: string;
  file_id?: string;
}

export interface BatchFileResult {
  file_name: string;
  success: boolean;
  error: string | null;
  file_id: string | null;
  original_size?: number;
  compressed_size?: number;
  compression_ratio?: number;
  original_size_formatted?: string;
  compressed_size_formatted?: string;
}

export interface BatchCompressionResponse {
  success: boolean;
  message: string;
  total_files: number;
  successful: number;
  failed: number;
  total_original_size: number;
  total_compressed_size: number;
  overall_compression_ratio: number;
  files: BatchFileResult[];
}

export interface HealthResponse {
  status: string;
  ghostscript_available: boolean;
  ghostscript_command: string;
}

export type QualityLevel = 'screen' | 'ebook' | 'printer' | 'prepress' | 'default';

export class PDFCompressorClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
  }

  /**
   * Verifica se o serviço está disponível
   */
  async checkHealth(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Comprime um único arquivo PDF
   * 
   * @param file Arquivo PDF a ser comprimido
   * @param quality Nível de qualidade (padrão: 'prepress')
   * @returns Resposta com informações da compressão
   */
  async compressFile(
    file: File,
    quality: QualityLevel = 'prepress'
  ): Promise<CompressionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('quality', quality);

    const response = await fetch(`${this.baseUrl}/api/v1/compress`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `Erro na compressão: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Comprime múltiplos arquivos PDF em lote
   * 
   * @param files Array de arquivos PDF a serem comprimidos
   * @param quality Nível de qualidade (padrão: 'prepress')
   * @returns Resposta com resultados de todos os arquivos
   */
  async compressBatch(
    files: File[],
    quality: QualityLevel = 'prepress'
  ): Promise<BatchCompressionResponse> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('quality', quality);

    const response = await fetch(`${this.baseUrl}/api/v1/compress/batch`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `Erro na compressão em lote: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Baixa um arquivo comprimido pelo ID
   * 
   * @param fileId ID do arquivo retornado pela API
   * @returns Blob do arquivo PDF comprimido
   */
  async downloadFile(fileId: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/api/v1/download/${fileId}`);
    
    if (!response.ok) {
      throw new Error(`Erro ao baixar arquivo: ${response.statusText}`);
    }

    return await response.blob();
  }

  /**
   * Baixa um arquivo comprimido e cria um link de download
   * 
   * @param fileId ID do arquivo retornado pela API
   * @param filename Nome do arquivo para download (opcional)
   */
  async downloadFileAsLink(fileId: string, filename?: string): Promise<void> {
    const blob = await this.downloadFile(fileId);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `compressed_${fileId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  /**
   * Remove arquivos temporários do servidor
   * 
   * @param fileId ID do arquivo a ser removido
   */
  async cleanupFile(fileId: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/cleanup/${fileId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Erro ao limpar arquivo: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Obtém as configurações de qualidade disponíveis
   */
  async getQualitySettings(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/v1/quality-settings`);
    if (!response.ok) {
      throw new Error(`Erro ao obter configurações: ${response.statusText}`);
    }
    return await response.json();
  }
}

// Exemplo de uso
export async function example() {
  const client = new PDFCompressorClient('http://localhost:8000');

  // Verificar saúde do serviço
  const health = await client.checkHealth();
  console.log('Serviço disponível:', health.ghostscript_available);

  // Comprimir um arquivo único
  const fileInput = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (fileInput?.files?.[0]) {
    const file = fileInput.files[0];
    const result = await client.compressFile(file, 'prepress');
    
    if (result.success && result.file_id) {
      console.log(`Compressão bem-sucedida! Redução: ${result.compression_ratio}%`);
      
      // Baixar arquivo comprimido
      await client.downloadFileAsLink(result.file_id, `compressed_${file.name}`);
      
      // Limpar arquivo temporário
      await client.cleanupFile(result.file_id);
    }
  }

  // Comprimir múltiplos arquivos
  if (fileInput?.files) {
    const files = Array.from(fileInput.files);
    const batchResult = await client.compressBatch(files, 'prepress');
    
    console.log(`Processados ${batchResult.total_files} arquivos:`);
    console.log(`- Sucessos: ${batchResult.successful}`);
    console.log(`- Falhas: ${batchResult.failed}`);
    console.log(`- Redução total: ${batchResult.overall_compression_ratio}%`);

    // Baixar todos os arquivos comprimidos
    for (const fileResult of batchResult.files) {
      if (fileResult.success && fileResult.file_id) {
        await client.downloadFileAsLink(
          fileResult.file_id,
          `compressed_${fileResult.file_name}`
        );
      }
    }
  }
}

