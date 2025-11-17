/**
 * Processing status component with live updates
 */
'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { VideoStatusResponse, pollVideoStatus } from '@/lib/api';

interface ProcessingStatusProps {
  videoId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export function ProcessingStatus({ videoId, onComplete, onError }: ProcessingStatusProps) {
  const [status, setStatus] = useState<VideoStatusResponse | null>(null);

  useEffect(() => {
    const startPolling = async () => {
      try {
        await pollVideoStatus(videoId, (updatedStatus) => {
          setStatus(updatedStatus);

          if (updatedStatus.status === 'completed' && onComplete) {
            onComplete();
          } else if (updatedStatus.status === 'failed' && onError) {
            onError(updatedStatus.error_message || 'Erro desconhecido');
          }
        });
      } catch (error: any) {
        if (onError) {
          onError(error.message || 'Erro ao verificar status');
        }
      }
    };

    startPolling();
  }, [videoId, onComplete, onError]);

  if (!status) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case 'completed':
        return <CheckCircle2 className="h-8 w-8 text-green-500" />;
      case 'failed':
        return <XCircle className="h-8 w-8 text-red-500" />;
      case 'processing':
        return <Loader2 className="h-8 w-8 animate-spin text-primary" />;
      default:
        return <Clock className="h-8 w-8 text-muted-foreground" />;
    }
  };

  const getStatusBadge = () => {
    switch (status.status) {
      case 'completed':
        return <Badge className="bg-green-500">Concluído</Badge>;
      case 'failed':
        return <Badge variant="destructive">Falhou</Badge>;
      case 'processing':
        return <Badge>Processando</Badge>;
      default:
        return <Badge variant="secondary">Na fila</Badge>;
    }
  };

  const getStatusMessage = () => {
    if (status.status === 'completed') {
      return 'Processamento concluído com sucesso!';
    }
    if (status.status === 'failed') {
      return status.error_message || 'Erro ao processar vídeo';
    }
    if (status.status === 'processing') {
      if (status.progress < 10) return 'Inicializando...';
      if (status.progress < 25) return 'Extraindo frames do vídeo...';
      if (status.progress < 40) return 'Analisando conteúdo visual com IA...';
      if (status.progress < 55) return 'Extraindo e transcrevendo áudio...';
      if (status.progress < 70) return 'Identificando momentos virais...';
      if (status.progress < 75) return 'Selecionando melhores segmentos...';
      if (status.progress < 100) return 'Gerando clips finais...';
    }
    return 'Aguardando na fila...';
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Status do Processamento</CardTitle>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          {getStatusIcon()}
          <div className="flex-1">
            <p className="font-medium">{getStatusMessage()}</p>
            {status.status === 'processing' && (
              <Progress value={status.progress} className="mt-2" />
            )}
          </div>
        </div>

        {status.status === 'processing' && (
          <div className="text-sm text-muted-foreground">
            <p>Progresso: {status.progress}%</p>
            <p className="text-xs mt-1">
              Este processo pode levar alguns minutos dependendo do tamanho do vídeo.
            </p>
          </div>
        )}

        {status.status === 'failed' && status.error_message && (
          <div className="p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900 rounded-md">
            <p className="text-sm text-red-800 dark:text-red-200">
              {status.error_message}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
