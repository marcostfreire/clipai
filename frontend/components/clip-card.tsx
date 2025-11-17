/**
 * Clip card component
 */
'use client';

import { Download, Play, Star } from 'lucide-react';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ClipResponse, getClipThumbnailUrl, getClipDownloadUrl } from '@/lib/api';
import Image from 'next/image';
import Link from 'next/link';

interface ClipCardProps {
  clip: ClipResponse;
}

export function ClipCard({ clip }: ClipCardProps) {
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 9) return 'bg-green-500';
    if (score >= 7) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  const handleDownload = () => {
    const url = getClipDownloadUrl(clip.clip_id);
    const link = document.createElement('a');
    link.href = url;
    link.download = `clip_${clip.clip_id}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      <div className="relative aspect-[9/16] bg-muted">
        <Image
          src={getClipThumbnailUrl(clip.clip_id)}
          alt="Clip thumbnail"
          fill
          className="object-cover"
          unoptimized
        />
        <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center">
          <Link href={`/clips/${clip.clip_id}`}>
            <Button size="lg" variant="secondary">
              <Play className="h-6 w-6 mr-2" />
              Assistir
            </Button>
          </Link>
        </div>

        {/* Score badge */}
        <div className="absolute top-2 right-2">
          <Badge className={`${getScoreColor(clip.virality_score)} text-white font-bold`}>
            <Star className="h-3 w-3 mr-1 fill-current" />
            {clip.virality_score.toFixed(1)}
          </Badge>
        </div>

        {/* Duration badge */}
        <div className="absolute bottom-2 right-2">
          <Badge variant="secondary">
            {formatDuration(clip.duration)}
          </Badge>
        </div>
      </div>

      <CardContent className="pt-4">
        {clip.transcript && (
          <p className="text-sm text-muted-foreground line-clamp-3">
            {clip.transcript}
          </p>
        )}

        {clip.keywords && clip.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {clip.keywords.slice(0, 3).map((keyword, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {keyword}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>

      <CardFooter className="gap-2">
        <Link href={`/clips/${clip.clip_id}`} className="flex-1">
          <Button variant="default" className="w-full">
            <Play className="h-4 w-4 mr-2" />
            Assistir
          </Button>
        </Link>
        <Button variant="outline" onClick={handleDownload}>
          <Download className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
