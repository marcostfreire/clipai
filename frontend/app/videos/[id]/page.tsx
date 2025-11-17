/**
 * Video processing page
 */
'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Download, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProcessingStatus } from '@/components/processing-status';
import { ClipCard } from '@/components/clip-card';
import { processVideo, getVideoClips, ClipResponse } from '@/lib/api';
import { toast } from 'sonner';
import Link from 'next/link';

export default function VideoPage() {
  const params = useParams();
  const router = useRouter();
  const videoId = params.id as string;

  const [isStarting, setIsStarting] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [clips, setClips] = useState<ClipResponse[]>([]);

  const handleStartProcessing = async () => {
    try {
      setIsStarting(true);
      await processVideo(videoId);
      setHasStarted(true);
      toast.success('Processamento iniciado!');
    } catch (error: any) {
      console.error('Error starting processing:', error);
      toast.error(error.response?.data?.detail || 'Erro ao iniciar processamento');
    } finally {
      setIsStarting(false);
    }
  };

  const handleProcessingComplete = async () => {
    setIsCompleted(true);

    try {
      const response = await getVideoClips(videoId);
      setClips(response.clips);
      toast.success(`${response.clips.length} clips gerados com sucesso!`);
    } catch (error: any) {
      console.error('Error fetching clips:', error);
      toast.error('Erro ao carregar clips');
    }
  };

  const handleProcessingError = (error: string) => {
    toast.error(`Erro no processamento: ${error}`);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold">ClipAI</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="space-y-8">
          {/* Title */}
          <div className="text-center space-y-2">
            <h2 className="text-3xl font-bold">
              {isCompleted ? 'Clips Gerados' : 'Processamento de Vídeo'}
            </h2>
            <p className="text-muted-foreground">
              {isCompleted
                ? 'Seus clips estão prontos para download!'
                : 'Aguarde enquanto processamos seu vídeo'}
            </p>
          </div>

          {/* Start Processing Button */}
          {!hasStarted && !isCompleted && (
            <div className="flex flex-col items-center gap-4">
              <div className="text-center space-y-4 max-w-md">
                <p className="text-muted-foreground">
                  Clique no botão abaixo para iniciar o processamento do seu vídeo.
                  A IA irá analisar o conteúdo e gerar clips virais automaticamente.
                </p>
                <Button
                  onClick={handleStartProcessing}
                  disabled={isStarting}
                  size="lg"
                  className="w-full"
                >
                  {isStarting ? 'Iniciando...' : 'Iniciar Processamento'}
                  <Sparkles className="ml-2 h-5 w-5" />
                </Button>
              </div>
            </div>
          )}

          {/* Processing Status */}
          {hasStarted && !isCompleted && (
            <div className="max-w-2xl mx-auto">
              <ProcessingStatus
                videoId={videoId}
                onComplete={handleProcessingComplete}
                onError={handleProcessingError}
              />
            </div>
          )}

          {/* Clips Grid */}
          {isCompleted && clips.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-semibold">
                  {clips.length} {clips.length === 1 ? 'Clip Gerado' : 'Clips Gerados'}
                </h3>
                <Button variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Baixar Todos
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {clips.map((clip) => (
                  <ClipCard key={clip.clip_id} clip={clip} />
                ))}
              </div>
            </div>
          )}

          {/* No clips message */}
          {isCompleted && clips.length === 0 && (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                Nenhum clip foi gerado. O vídeo pode não ter momentos suficientemente virais.
              </p>
              <Link href="/">
                <Button className="mt-4">
                  Tentar Outro Vídeo
                </Button>
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
