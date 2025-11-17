/**
 * Video uploader component with drag-and-drop
 */
'use client';

import { useState, useCallback } from 'react';
import { Upload, Link as LinkIcon, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { uploadVideo, uploadVideoFromUrl } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { toast } from 'sonner';

export function VideoUploader({ onSuccess }: { onSuccess: (videoId: string) => void }) {
  const [dragActive, setDragActive] = useState(false);
  const [url, setUrl] = useState('');
  const { isUploading, uploadProgress, setIsUploading, setUploadProgress } = useAppStore();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileUpload = async (file: File) => {
    try {
      setIsUploading(true);
      setUploadProgress(0);

      const response = await uploadVideo(file, (progress) => {
        setUploadProgress(progress);
      });

      toast.success('Vídeo enviado com sucesso!');
      onSuccess(response.video_id);
    } catch (error: any) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Erro ao enviar vídeo');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleUrlUpload = async () => {
    if (!url.trim()) {
      toast.error('Por favor, insira uma URL válida');
      return;
    }

    try {
      setIsUploading(true);
      const response = await uploadVideoFromUrl(url);
      toast.success('Vídeo carregado com sucesso!');
      onSuccess(response.video_id);
    } catch (error: any) {
      console.error('URL upload error:', error);
      toast.error(error.response?.data?.detail || 'Erro ao carregar vídeo da URL');
    } finally {
      setIsUploading(false);
      setUrl('');
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto p-6">
      <Tabs defaultValue="file" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="file">Upload de Arquivo</TabsTrigger>
          <TabsTrigger value="url">URL do YouTube</TabsTrigger>
        </TabsList>

        <TabsContent value="file">
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
              }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {isUploading ? (
              <div className="space-y-4">
                <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
                <div>
                  <p className="text-lg font-medium">Enviando vídeo...</p>
                  <Progress value={uploadProgress} className="mt-2" />
                  <p className="text-sm text-muted-foreground mt-2">{uploadProgress}%</p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                <div>
                  <p className="text-lg font-medium">Arraste e solte seu vídeo aqui</p>
                  <p className="text-sm text-muted-foreground">ou</p>
                </div>
                <Button
                  onClick={() => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = 'video/*';
                    input.onchange = (e) => {
                      const file = (e.target as HTMLInputElement).files?.[0];
                      if (file) handleFileUpload(file);
                    };
                    input.click();
                  }}
                >
                  Selecionar Arquivo
                </Button>
                <p className="text-xs text-muted-foreground">
                  Formatos aceitos: MP4, MOV, AVI, MKV, WEBM
                  <br />
                  Tamanho máximo: 500 MB | Duração máxima: 60 minutos
                </p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="url">
          <div className="space-y-4 p-6">
            <div className="flex gap-2">
              <Input
                placeholder="Cole a URL do YouTube aqui..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isUploading}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleUrlUpload();
                }}
              />
              <Button onClick={handleUrlUpload} disabled={isUploading || !url.trim()}>
                {isUploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LinkIcon className="h-4 w-4" />
                )}
                <span className="ml-2">Carregar</span>
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Cole a URL de um vídeo do YouTube para processar
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  );
}
