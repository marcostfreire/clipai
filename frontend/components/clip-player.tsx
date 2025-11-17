/**
 * Clip player component
 */
'use client';

import { Download, Share2, Copy, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ClipResponse, getClipDownloadUrl } from '@/lib/api';
import { useState } from 'react';
import { toast } from 'sonner';

interface ClipPlayerProps {
  clip: ClipResponse;
}

export function ClipPlayer({ clip }: ClipPlayerProps) {
  const [copied, setCopied] = useState(false);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleDownload = () => {
    const url = getClipDownloadUrl(clip.clip_id);
    const link = document.createElement('a');
    link.href = url;
    link.download = `clip_${clip.clip_id}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Download iniciado!');
  };

  const handleShare = async () => {
    const url = window.location.href;

    if (navigator.share) {
      try {
        await navigator.share({
          title: 'ClipAI - Clip viral',
          text: clip.transcript || 'Confira este clip viral!',
          url: url,
        });
      } catch (error) {
        // User cancelled or share failed
      }
    } else {
      await handleCopy();
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      toast.success('Link copiado para área de transferência!');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Erro ao copiar link');
    }
  };

  return (
    <div className="max-w-md mx-auto space-y-4">
      <Card>
        <CardContent className="p-0">
          <video
            controls
            className="w-full aspect-[9/16] bg-black"
            src={getClipDownloadUrl(clip.clip_id)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="text-lg">Informações do Clip</CardTitle>
            </div>
            <Badge className="bg-primary font-bold text-lg">
              {clip.virality_score.toFixed(1)} ⭐
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Duração</p>
              <p className="font-medium">{formatDuration(clip.duration)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Tempo no vídeo</p>
              <p className="font-medium">
                {formatDuration(clip.start_time)} - {formatDuration(clip.end_time)}
              </p>
            </div>
          </div>

          <Separator />

          {clip.transcript && (
            <>
              <div>
                <p className="text-sm font-medium mb-2">Transcrição</p>
                <p className="text-sm text-muted-foreground">{clip.transcript}</p>
              </div>
              <Separator />
            </>
          )}

          {clip.keywords && clip.keywords.length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Palavras-chave</p>
              <div className="flex flex-wrap gap-2">
                {clip.keywords.map((keyword, index) => (
                  <Badge key={index} variant="secondary">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <Button onClick={handleDownload} className="flex-1">
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button variant="outline" onClick={handleShare}>
              <Share2 className="h-4 w-4 mr-2" />
              Compartilhar
            </Button>
            <Button variant="outline" size="icon" onClick={handleCopy}>
              {copied ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
