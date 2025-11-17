/**
 * Global state management with Zustand
 */
import { create } from 'zustand';
import { VideoStatusResponse, ClipResponse } from './api';

interface AppState {
  // Current video
  currentVideoId: string | null;
  videoStatus: VideoStatusResponse | null;
  clips: ClipResponse[];

  // UI state
  isUploading: boolean;
  uploadProgress: number;
  isProcessing: boolean;

  // Actions
  setCurrentVideoId: (id: string | null) => void;
  setVideoStatus: (status: VideoStatusResponse | null) => void;
  setClips: (clips: ClipResponse[]) => void;
  setIsUploading: (uploading: boolean) => void;
  setUploadProgress: (progress: number) => void;
  setIsProcessing: (processing: boolean) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  currentVideoId: null,
  videoStatus: null,
  clips: [],
  isUploading: false,
  uploadProgress: 0,
  isProcessing: false,

  // Actions
  setCurrentVideoId: (id) => set({ currentVideoId: id }),
  setVideoStatus: (status) => set({ videoStatus: status }),
  setClips: (clips) => set({ clips }),
  setIsUploading: (uploading) => set({ isUploading: uploading }),
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  reset: () => set({
    currentVideoId: null,
    videoStatus: null,
    clips: [],
    isUploading: false,
    uploadProgress: 0,
    isProcessing: false,
  }),
}));
