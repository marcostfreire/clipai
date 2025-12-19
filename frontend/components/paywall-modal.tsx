'use client';

import { useState } from 'react';
import { Rocket, Zap, X, Lock, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import Link from 'next/link';
import { createCheckoutSession, SubscriptionLimits } from '@/lib/api';
import { toast } from 'sonner';

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
  limits?: SubscriptionLimits | null;
  reason?: string;
  type?: 'limit_reached' | 'duration_exceeded' | 'feature_locked';
}

const PRICE_IDS = {
  starter: 'price_1SUSowCMwpJ5YuyfvZq5iXYZ',  // R$149/month
  pro: 'price_1SUSowCMwpJ5YuyfiRMdGv15',       // R$499/month
};

export function PaywallModal({
  isOpen,
  onClose,
  limits,
  reason,
  type = 'limit_reached'
}: PaywallModalProps) {
  const [loading, setLoading] = useState<string | null>(null);

  const handleUpgrade = async (plan: 'starter' | 'pro') => {
    setLoading(plan);
    try {
      const priceId = PRICE_IDS[plan];
      const response = await createCheckoutSession(
        priceId,
        `${window.location.origin}/videos?upgraded=true`,
        window.location.href
      );

      if (response.url) {
        window.location.href = response.url;
      }
    } catch (error: any) {
      console.error('Error creating checkout session:', error);
      if (error.response?.status === 401) {
        toast.error('Faça login para continuar');
        window.location.href = `/auth/login?redirect=${encodeURIComponent(window.location.pathname)}`;
      } else {
        toast.error('Erro ao criar sessão de pagamento. Tente novamente.');
      }
    } finally {
      setLoading(null);
    }
  };

  const getTitle = () => {
    switch (type) {
      case 'limit_reached':
        return 'Limite de vídeos atingido';
      case 'duration_exceeded':
        return 'Duração do vídeo excedida';
      case 'feature_locked':
        return 'Recurso Premium';
      default:
        return 'Upgrade necessário';
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'limit_reached':
        return <AlertTriangle className="h-12 w-12 text-amber-500" />;
      case 'duration_exceeded':
        return <AlertTriangle className="h-12 w-12 text-amber-500" />;
      case 'feature_locked':
        return <Lock className="h-12 w-12 text-primary" />;
      default:
        return <Rocket className="h-12 w-12 text-primary" />;
    }
  };

  const currentPlan = limits?.plan || 'free';

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader className="text-center">
          <div className="flex justify-center mb-4">
            {getIcon()}
          </div>
          <DialogTitle className="text-2xl">{getTitle()}</DialogTitle>
          <DialogDescription className="text-base">
            {reason || 'Faça upgrade do seu plano para continuar usando o ClipAI.'}
          </DialogDescription>
        </DialogHeader>

        {limits && (
          <div className="bg-muted/50 rounded-lg p-4 my-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium">Uso este mês</span>
              <span className="text-sm text-muted-foreground">
                {limits.usage.videos_this_month} / {limits.limits.videos_per_month} vídeos
              </span>
            </div>
            <Progress
              value={limits.usage.percentage_used}
              className="h-2"
            />
            <p className="text-xs text-muted-foreground mt-2">
              Renova em {limits.reset.days_until_reset} dias
            </p>
          </div>
        )}

        <div className="grid gap-4 py-4">
          {/* Starter Plan */}
          {currentPlan === 'free' && (
            <div className="border rounded-lg p-4 hover:border-primary transition-colors">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-blue-500" />
                    <h3 className="font-semibold">Starter</h3>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    12 vídeos/mês • Sem marca d&apos;água
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold">R$149<span className="text-sm font-normal">/mês</span></p>
                </div>
              </div>
              <Button
                className="w-full mt-3"
                onClick={() => handleUpgrade('starter')}
                disabled={loading !== null}
              >
                {loading === 'starter' ? 'Carregando...' : 'Escolher Starter'}
              </Button>
            </div>
          )}

          {/* Pro Plan */}
          <div className="border-2 border-primary rounded-lg p-4 relative">
            <div className="absolute -top-3 left-4 bg-primary text-primary-foreground px-2 py-0.5 rounded text-xs font-semibold">
              Recomendado
            </div>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Rocket className="h-5 w-5 text-purple-500" />
                  <h3 className="font-semibold">Pro</h3>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  50 vídeos/mês • Fila prioritária • API
                </p>
              </div>
              <div className="text-right">
                <p className="font-bold">R$499<span className="text-sm font-normal">/mês</span></p>
              </div>
            </div>
            <Button
              className="w-full mt-3 bg-linear-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              onClick={() => handleUpgrade('pro')}
              disabled={loading !== null}
            >
              {loading === 'pro' ? 'Carregando...' : 'Escolher Pro'}
            </Button>
          </div>
        </div>

        <div className="text-center">
          <Link
            href="/pricing"
            className="text-sm text-muted-foreground hover:text-foreground underline"
          >
            Ver todos os planos e recursos
          </Link>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Usage indicator component for displaying in the header or sidebar
 */
interface UsageIndicatorProps {
  limits: SubscriptionLimits;
  compact?: boolean;
}

export function UsageIndicator({ limits, compact = false }: UsageIndicatorProps) {
  const isNearLimit = limits.usage.percentage_used >= 80;
  const isAtLimit = !limits.can_upload;

  if (compact) {
    return (
      <div className={`flex items-center gap-2 text-sm ${isAtLimit ? 'text-destructive' : isNearLimit ? 'text-amber-500' : 'text-muted-foreground'}`}>
        <span>
          {limits.usage.videos_remaining}/{limits.limits.videos_per_month} restantes
        </span>
      </div>
    );
  }

  return (
    <div className="bg-card border rounded-lg p-4">
      <div className="flex justify-between items-center mb-2">
        <span className="font-medium">
          Plano {limits.plan_display_name}
        </span>
        <span className={`text-sm ${isAtLimit ? 'text-destructive' : ''}`}>
          {limits.usage.videos_this_month}/{limits.limits.videos_per_month} vídeos
        </span>
      </div>
      <Progress
        value={limits.usage.percentage_used}
        className={`h-2 ${isAtLimit ? '[&>div]:bg-destructive' : isNearLimit ? '[&>div]:bg-amber-500' : ''}`}
      />
      <div className="flex justify-between mt-2">
        <span className="text-xs text-muted-foreground">
          {limits.usage.videos_remaining} restantes
        </span>
        <span className="text-xs text-muted-foreground">
          Renova em {limits.reset.days_until_reset}d
        </span>
      </div>
      {isAtLimit && (
        <Link href="/pricing">
          <Button size="sm" className="w-full mt-3" variant="default">
            Fazer Upgrade
          </Button>
        </Link>
      )}
    </div>
  );
}
