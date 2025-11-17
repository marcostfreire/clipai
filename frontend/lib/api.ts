/**
 * API client for ClipAI backend
 */
import axios, { AxiosProgressEvent } from 'axios';

const EDGE_PROXY_PATH = '/api/proxy';
const nextPublicApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const useEdgeProxy = process.env.NEXT_PUBLIC_USE_EDGE_PROXY !== 'false';

export const API_BASE_URL = useEdgeProxy
  ? EDGE_PROXY_PATH
  : nextPublicApiUrl || EDGE_PROXY_PATH;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // AGGRESSIVE CORS & CLOUDFLARE BYPASS
  timeout: 30000, // 30s timeout
  withCredentials: false, // Don't send credentials to avoid CORS issues
});

// Retry configuration for Cloudflare bypass
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1s

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Add request interceptor to attach JWT token and aggressive headers
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    
    // AGGRESSIVE HEADERS to bypass Cloudflare
    config.headers['Accept'] = 'application/json, text/plain, */*';
    config.headers['X-Requested-With'] = 'XMLHttpRequest';
    config.headers['Cache-Control'] = 'no-cache';
    config.headers['Pragma'] = 'no-cache';
    
    // Remove Content-Type header for FormData to let browser set it with boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    
    console.log(`🔵 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor with AGGRESSIVE RETRY LOGIC
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  async (error) => {
    const config = error.config;
    
    // Log the error
    console.error(`❌ API Error: ${error.message}`, {
      url: config?.url,
      status: error.response?.status,
      data: error.response?.data,
    });
    
    // Handle 401 errors
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
    
    // AGGRESSIVE RETRY LOGIC for network errors or 5xx errors
    if (!config || !config._retryCount) {
      config._retryCount = 0;
    }
    
    const shouldRetry = 
      (!error.response || error.response.status >= 500 || error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK') &&
      config._retryCount < MAX_RETRIES;
    
    if (shouldRetry) {
      config._retryCount += 1;
      const delay = RETRY_DELAY * config._retryCount; // Exponential backoff
      
      console.warn(`⚠️ Retrying request (${config._retryCount}/${MAX_RETRIES}) after ${delay}ms...`);
      
      await sleep(delay);
      return api(config);
    }
    
    return Promise.reject(error);
  }
);

export interface VideoUploadResponse {
  video_id: string;
  status: string;
  message: string;
}

export interface VideoProcessResponse {
  job_id: string;
  video_id: string;
  status: string;
}

export interface VideoStatusResponse {
  video_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  error_message?: string;
  created_at: string;
  updated_at?: string;
}

export interface ClipResponse {
  clip_id: string;
  start_time: number;
  end_time: number;
  duration: number;
  virality_score: number;
  transcript?: string;
  keywords?: string[];
  thumbnail_url: string;
  download_url: string;
  created_at: string;
}

export interface ClipsListResponse {
  video_id: string;
  clips: ClipResponse[];
  total: number;
}

/**
 * Upload video file
 */
export async function uploadVideo(
  file: File,
  onProgress?: (progress: number) => void
): Promise<VideoUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<VideoUploadResponse>('/videos/upload', formData, {
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (onProgress && progressEvent.total) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    },
  });

  return response.data;
}

/**
 * Upload video from URL
 */
export async function uploadVideoFromUrl(url: string): Promise<VideoUploadResponse> {
  const formData = new FormData();
  formData.append('url', url);

  const response = await api.post<VideoUploadResponse>('/videos/upload', formData);

  return response.data;
}

/**
 * Start video processing
 */
export async function processVideo(videoId: string): Promise<VideoProcessResponse> {
  const response = await api.post<VideoProcessResponse>(`/videos/${videoId}/process`);
  return response.data;
}

/**
 * Get video processing status
 */
export async function getVideoStatus(videoId: string): Promise<VideoStatusResponse> {
  const response = await api.get<VideoStatusResponse>(`/videos/${videoId}/status`);
  return response.data;
}

/**
 * Get all clips for a video
 */
export async function getVideoClips(
  videoId: string,
  minScore: number = 0
): Promise<ClipsListResponse> {
  const response = await api.get<ClipsListResponse>(`/videos/${videoId}/clips`, {
    params: { min_score: minScore },
  });
  return response.data;
}

/**
 * Get clip download URL
 */
export function getClipDownloadUrl(clipId: string): string {
  return `${API_BASE_URL}/clips/${clipId}/download`;
}

/**
 * Get clip thumbnail URL
 */
export function getClipThumbnailUrl(clipId: string): string {
  return `${API_BASE_URL}/clips/${clipId}/thumbnail`;
}

/**
 * Delete video
 */
export async function deleteVideo(videoId: string): Promise<void> {
  await api.delete(`/videos/${videoId}`);
}

/**
 * Poll video status until completion
 */
export async function pollVideoStatus(
  videoId: string,
  onUpdate: (status: VideoStatusResponse) => void,
  interval: number = 2000
): Promise<VideoStatusResponse> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getVideoStatus(videoId);
        onUpdate(status);

        if (status.status === 'completed' || status.status === 'failed') {
          resolve(status);
        } else {
          setTimeout(poll, interval);
        }
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
}

// =====================
// Authentication API
// =====================

export interface UserCreate {
  email: string;
  password: string;
}

export interface UserRead {
  id: string;
  email: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

/**
 * Register a new user
 */
export async function register(email: string, password: string): Promise<UserRead> {
  const response = await api.post<UserRead>('/auth/register', {
    email,
    password,
  });
  return response.data;
}

/**
 * Login and get access token
 */
export async function login(email: string, password: string): Promise<Token> {
  const formData = new FormData();
  formData.append('username', email); // OAuth2 uses 'username' field
  formData.append('password', password);

  const response = await api.post<Token>('/auth/login', formData);

  // Store token in localStorage
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', response.data.access_token);
  }

  return response.data;
}

/**
 * Get current user info
 */
export async function getCurrentUser(): Promise<UserRead> {
  const response = await api.get<UserRead>('/auth/me');
  return response.data;
}

/**
 * Logout (clear token)
 */
export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('access_token');
}

