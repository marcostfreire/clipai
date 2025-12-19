/**
 * Individual clip page
 */
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Image from 'next/image';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ClipPlayer } from '@/components/clip-player';
import { Skeleton } from '@/components/ui/skeleton';
import { getVideoClips, ClipResponse } from '@/lib/api';
import { toast } from 'sonner';
import Link from 'next/link';

export default function ClipPage() {
  const params = useParams();
  const clipId = params.id as string;

  const [clip, setClip] = useState<ClipResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchClip = async () => {
      try {
        // Extract video ID from clip ID (format: videoId_clip_N)
        const videoId = clipId.split('_clip_')[0];

        const response = await getVideoClips(videoId);
        const foundClip = response.clips.find((c) => c.clip_id === clipId);

        if (foundClip) {
          setClip(foundClip);
        } else {
          toast.error('Clip não encontrado');
        }
      } catch (error: any) {
        console.error('Error fetching clip:', error);
        toast.error('Erro ao carregar clip');
      } finally {
        setIsLoading(false);
      }
    };

    fetchClip();
  }, [clipId]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => window.history.back()}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex items-center gap-2">
              <Image
                src="/logo.png"
                alt="ClipAI Logo"
                width={32}
                height={32}
                className="h-8 w-8 object-contain"
              />
              <h1 className="text-2xl font-bold">ClipAI</h1>
            </div>
          </div>
          <Link href="/">
            <Button variant="outline">Nova Análise</Button>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {isLoading ? (
          <div className="max-w-md mx-auto space-y-4">
            <Skeleton className="aspect-9/16 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : clip ? (
          <ClipPlayer clip={clip} />
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">Clip não encontrado</p>
            <Link href="/">
              <Button>Voltar ao Início</Button>
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
