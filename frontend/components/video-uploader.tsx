/**
 * Video uploader component with drag-and-drop
 */
'use client';

import { useState, useCallback, useEffect } from 'react';
import { Upload, Link as LinkIcon, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { uploadVideo, uploadVideoFromUrl, getSubscriptionLimits, isAuthenticated, SubscriptionLimits } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { toast } from 'sonner';
import { PaywallModal, UsageIndicator } from '@/components/paywall-modal';

export function VideoUploader({ onSuccess }: { onSuccess: (videoId: string) => void }) {
  const [dragActive, setDragActive] = useState(false);
  const [url, setUrl] = useState('');
  const [limits, setLimits] = useState<SubscriptionLimits | null>(null);
  const [showPaywall, setShowPaywall] = useState(false);
  const [paywallReason, setPaywallReason] = useState('');
  const [paywallType, setPaywallType] = useState<'limit_reached' | 'duration_exceeded' | 'feature_locked'>('limit_reached');
  const { isUploading, uploadProgress, setIsUploading, setUploadProgress } = useAppStore();

  // Fetch subscription limits on mount
  useEffect(() => {
    if (isAuthenticated()) {
      getSubscriptionLimits()
        .then(setLimits)
        .catch((err) => {
          console.error('Error fetching limits:', err);
        });
    }
  }, []);

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
  }, [limits]);

  const checkCanUpload = (): boolean => {
    // If not authenticated, allow upload (backend will handle anonymous users)
    if (!isAuthenticated()) {
      return true;
    }

    // If we have limits info and user can't upload, show paywall
    if (limits && !limits.can_upload) {
      setPaywallReason(`Você atingiu o limite de ${limits.limits.videos_per_month} vídeos por mês no plano ${limits.plan_display_name}.`);
      setPaywallType('limit_reached');
      setShowPaywall(true);
      return false;
    }

    return true;
  };

  const handleFileUpload = async (file: File) => {
    if (!checkCanUpload()) {
      return;
    }

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

      // Check for paywall error (402 Payment Required)
      if (error.response?.status === 402) {
        const errorData = error.response.data?.detail;
        if (errorData?.error === 'subscription_limit_reached') {
          setPaywallReason(errorData.message);
          setPaywallType('limit_reached');
          setShowPaywall(true);
          // Refresh limits
          if (isAuthenticated()) {
            getSubscriptionLimits().then(setLimits).catch(console.error);
          }
        } else if (errorData?.error === 'video_too_long') {
          setPaywallReason(errorData.message);
          setPaywallType('duration_exceeded');
          setShowPaywall(true);
        }
      } else {
        toast.error(error.response?.data?.detail || 'Erro ao enviar vídeo');
      }
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

    if (!checkCanUpload()) {
      return;
    }

    try {
      setIsUploading(true);
      const response = await uploadVideoFromUrl(url);
      toast.success('Vídeo carregado com sucesso!');
      onSuccess(response.video_id);
    } catch (error: any) {
      console.error('URL upload error:', error);

      // Check for specific error types
      const errorData = error.response?.data?.detail;
      
      if (error.response?.status === 402) {
        if (errorData?.error === 'subscription_limit_reached') {
          setPaywallReason(errorData.message);
          setPaywallType('limit_reached');
          setShowPaywall(true);
        }
      } else if (error.response?.status === 400 && errorData?.error) {
        // Handle video_too_large and video_too_long errors with friendly messages
        if (errorData.error === 'video_too_large') {
          toast.error(
            <div className="space-y-1">
              <p className="font-medium">Vídeo muito grande (~{errorData.estimated_size_mb}MB)</p>
              <p className="text-sm">Limite para URL: {errorData.max_size_mb}MB</p>
              <p className="text-sm text-muted-foreground">Baixe o vídeo manualmente e faça upload do arquivo.</p>
            </div>,
            { duration: 8000 }
          );
        } else if (errorData.error === 'video_too_long') {
          toast.error(
            <div className="space-y-1">
              <p className="font-medium">Vídeo muito longo ({Math.floor(errorData.duration_seconds / 60)}min)</p>
              <p className="text-sm">Limite para URL: {Math.floor(errorData.max_duration_seconds / 60)} minutos</p>
              <p className="text-sm text-muted-foreground">Baixe o vídeo manualmente e faça upload do arquivo.</p>
            </div>,
            { duration: 8000 }
          );
        } else {
          toast.error(errorData.message || errorData || 'Erro ao carregar vídeo da URL');
        }
      } else if (error.response?.status === 504) {
        toast.error(
          <div className="space-y-1">
            <p className="font-medium">Timeout no download</p>
            <p className="text-sm">O vídeo é muito grande para baixar via URL.</p>
            <p className="text-sm text-muted-foreground">Baixe o vídeo manualmente e faça upload do arquivo.</p>
          </div>,
          { duration: 8000 }
        );
      } else {
        const message = typeof errorData === 'string' ? errorData : errorData?.message || 'Erro ao carregar vídeo da URL';
        toast.error(message);
      }
    } finally {
      setIsUploading(false);
      setUrl('');
    }
  };

  return (
    <>
      <Card className="w-full max-w-2xl mx-auto p-6">
        {/* Usage indicator for authenticated users */}
        {limits && (
          <div className="mb-4">
            <UsageIndicator limits={limits} />
          </div>
        )}

        <Tabs defaultValue="file" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="file">Upload de Arquivo</TabsTrigger>
            <TabsTrigger value="url">URL do YouTube</TabsTrigger>
          </TabsList>

          <TabsContent value="file">
            <div
              className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
                } ${limits && !limits.can_upload ? 'opacity-50' : ''}`}
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
              ) : limits && !limits.can_upload ? (
                <div className="space-y-4">
                  <AlertCircle className="h-12 w-12 mx-auto text-amber-500" />
                  <div>
                    <p className="text-lg font-medium">Limite atingido</p>
                    <p className="text-sm text-muted-foreground">
                      Você usou todos os {limits.limits.videos_per_month} vídeos do mês
                    </p>
                  </div>
                  <Button onClick={() => setShowPaywall(true)}>
                    Fazer Upgrade
                  </Button>
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
                    Tamanho máximo: 500 MB | Duração máxima: {limits ? limits.limits.max_video_duration_minutes : 60} minutos
                  </p>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="url">
            <div className="space-y-4 p-6">
              {limits && !limits.can_upload ? (
                <div className="text-center space-y-4">
                  <AlertCircle className="h-12 w-12 mx-auto text-amber-500" />
                  <p className="text-muted-foreground">Limite de vídeos atingido</p>
                  <Button onClick={() => setShowPaywall(true)}>
                    Fazer Upgrade
                  </Button>
                </div>
              ) : (
                <>
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
                    Cole a URL de um vídeo do YouTube (máx. 20 min / 200MB)
                    <br />
                    Para vídeos maiores, baixe manualmente e faça upload do arquivo
                  </p>
                </>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </Card>

      {/* Paywall Modal */}
      <PaywallModal
        isOpen={showPaywall}
        onClose={() => setShowPaywall(false)}
        limits={limits}
        reason={paywallReason}
        type={paywallType}
      />
    </>
  );
}
