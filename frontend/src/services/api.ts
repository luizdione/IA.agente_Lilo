import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutos
  headers: {
    'Content-Type': 'application/json'
  }
});

// Tipos
export interface TaskRequest {
  task: string;
  context?: Record<string, any>;
}

export interface TaskResponse {
  task: string;
  status: string;
  result: any;
}

export interface FileResponse {
  success: boolean;
  message: string;
  data?: any;
}

// Funções da API

/**
 * Executa uma tarefa no agente
 */
export const executeTask = async (task: string, context?: Record<string, any>): Promise<TaskResponse> => {
  const response = await apiClient.post<TaskResponse>('/agent/execute', {
    task,
    context
  });
  return response.data;
};

/**
 * Obtém status do agente
 */
export const getAgentStatus = async (): Promise<any> => {
  const response = await apiClient.get('/agent/status');
  return response.data;
};

/**
 * Lê um arquivo
 */
export const readFile = async (path: string): Promise<FileResponse> => {
  const response = await apiClient.post<FileResponse>('/files/read', { path });
  return response.data;
};

/**
 * Escreve em um arquivo
 */
export const writeFile = async (path: string, content: string): Promise<FileResponse> => {
  const response = await apiClient.post<FileResponse>('/files/write', {
    path,
    content
  });
  return response.data;
};

/**
 * Lista diretório
 */
export const listDirectory = async (path: string, recursive: boolean = false): Promise<FileResponse> => {
  const response = await apiClient.post<FileResponse>('/files/list', {
    path,
    recursive
  });
  return response.data;
};

/**
 * Deleta arquivo
 */
export const deleteFile = async (path: string): Promise<FileResponse> => {
  const response = await apiClient.delete<FileResponse>(`/files/${path}`);
  return response.data;
};

export default apiClient;
