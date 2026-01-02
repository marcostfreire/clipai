/**
 * Home page - Video upload and initial screen
 */
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { Sparkles, Zap, Brain, Video, LogOut } from 'lucide-react';
import { VideoUploader } from '@/components/video-uploader';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { isAuthenticated, logout, getCurrentUser } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated (optional)
    if (isAuthenticated()) {
      getCurrentUser()
        .then((user) => setUserEmail(user.email))
        .catch(() => {
          logout();
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const handleUploadSuccess = (videoId: string) => {
    router.push(`/videos/${videoId}`);
  };

  const handleLogout = () => {
    logout();
    setUserEmail(null);
  };

  if (isLoading) {
    return null;
  }

  return (
    <div className="min-h-screen bg-linear-to-b from-background to-muted/20">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
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
          <nav className="flex gap-4 items-center">
            {userEmail ? (
              <>
                <span className="text-sm text-muted-foreground">{userEmail}</span>
                <Button variant="ghost" onClick={handleLogout}>
                  <LogOut className="h-4 w-4 mr-2" />
                  Sair
                </Button>
              </>
            ) : (
              <Link href="/auth">
                <Button variant="default">Entrar / Criar Conta</Button>
              </Link>
            )}
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-16">
        <div className="text-center space-y-6 mb-12">
          <h2 className="text-5xl font-bold tracking-tight">
            Transforme vídeos longos em
            <span className="text-primary"> clips virais</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            IA identifica os melhores momentos do seu vídeo e cria clips verticais
            prontos para TikTok, Instagram Reels e YouTube Shorts.
          </p>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="p-6 rounded-lg border bg-card text-center space-y-2">
            <Brain className="h-12 w-12 mx-auto text-primary" />
            <h3 className="font-semibold text-lg">IA Inteligente</h3>
            <p className="text-sm text-muted-foreground">
              Identifica momentos virais por análise de expressões faciais
            </p>
          </div>
          <div className="p-6 rounded-lg border bg-card text-center space-y-2">
            <Zap className="h-12 w-12 mx-auto text-primary" />
            <h3 className="font-semibold text-lg">Processamento Rápido</h3>
            <p className="text-sm text-muted-foreground">
              Gera múltiplos clips em minutos
            </p>
          </div>
          <div className="p-6 rounded-lg border bg-card text-center space-y-2">
            <Video className="h-12 w-12 mx-auto text-primary" />
            <h3 className="font-semibold text-lg">Formato Vertical</h3>
            <p className="text-sm text-muted-foreground">
              Legendas automáticas e formato 9:16
            </p>
          </div>
        </div>

        {/* Upload Section */}
        <div className="max-w-4xl mx-auto">
          <h3 className="text-2xl font-semibold text-center mb-6">
            Faça upload do seu vídeo para começar
          </h3>
          <VideoUploader onSuccess={handleUploadSuccess} />
        </div>

        {/* How it works */}
        <div className="mt-16 max-w-3xl mx-auto">
          <h3 className="text-2xl font-semibold text-center mb-8">Como Funciona</h3>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                1
              </div>
              <div>
                <h4 className="font-semibold">Faça upload do vídeo</h4>
                <p className="text-sm text-muted-foreground">
                  Envie um arquivo ou cole uma URL do YouTube
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                2
              </div>
              <div>
                <h4 className="font-semibold">IA analisa o conteúdo</h4>
                <p className="text-sm text-muted-foreground">
                  Identificamos momentos virais, transcrevemos e analisamos visualmente
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
                3
              </div>
              <div>
                <h4 className="font-semibold">Receba clips prontos</h4>
                <p className="text-sm text-muted-foreground">
                  Downloads em formato vertical com legendas automáticas
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-16 py-8 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8 mb-6">
            <div>
              <h4 className="font-semibold mb-3">ClipAI</h4>
              <p className="text-sm text-muted-foreground">
                Gerador de clips virais com IA
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="/terms" className="hover:text-foreground">
                    Termos de Uso
                  </a>
                </li>
                <li>
                  <a href="/privacy" className="hover:text-foreground">
                    Política de Privacidade
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Tecnologias</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a
                    href="https://ai.google.dev/gemini"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground"
                  >
                    Google Gemini
                  </a>
                </li>
                <li>
                  <a
                    href="https://github.com/SYSTRAN/faster-whisper"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground"
                  >
                    Faster Whisper (MIT)
                  </a>
                </li>
                <li>
                  <a
                    href="https://ffmpeg.org/legal.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground"
                  >
                    FFmpeg (LGPL/GPL)
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Recursos</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <Link href="/pricing" className="hover:text-foreground">
                    Planos e Preços
                  </Link>
                </li>
                <li>
                  <a href="/docs" className="hover:text-foreground">
                    Documentação
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t pt-6 text-center text-sm text-muted-foreground">
            <p>© 2026 ClipAI. Código aberto sob MIT License.</p>
            <p className="mt-2">
              Desenvolvido com Next.js, FastAPI e Gemini AI
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
