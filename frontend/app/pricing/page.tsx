'use client';

import { useState, useEffect } from 'react';
import { Check, Zap, Rocket, Star, Crown } from 'lucide-react';
import { API_BASE_URL, getSubscriptionStatus, isAuthenticated, SubscriptionStatus } from '@/lib/api';
import Link from 'next/link';

interface PricingTier {
  id: string;
  name: string;
  description: string;
  price: number;
  currency: string;
  interval: string;
  priceId: string;
  features: string[];
  highlighted?: boolean;
  icon: React.ReactNode;
  limits: {
    videos: number;
    clips: string;
    watermark: boolean;
    queue: string;
    api: boolean;
    maxDuration: number;
  };
}

const pricingTiers: PricingTier[] = [
  {
    id: 'free',
    name: 'Free',
    description: 'Perfeito para testar a plataforma',
    price: 0,
    currency: 'BRL',
    interval: '/mês',
    priceId: 'price_1SUSZdCMwpJ5YuyfbFDEQh5A',
    icon: <Star className="w-6 h-6" />,
    limits: {
      videos: 2,
      clips: '3 clips por vídeo',
      watermark: true,
      queue: 'Padrão',
      api: false,
      maxDuration: 30,
    },
    features: [
      '2 vídeos por mês',
      'Até 3 clips por vídeo',
      'Marca d\'água ClipAI',
      'Vídeos até 30 minutos',
      'Processamento com IA',
      'Legendas automáticas',
      'Detecção de momentos virais',
      'Fila padrão',
    ],
  },
  {
    id: 'starter',
    name: 'Starter',
    description: 'Ideal para criadores individuais',
    price: 149,
    currency: 'BRL',
    interval: '/mês',
    priceId: 'price_1SUSowCMwpJ5YuyfvZq5iXYZ',
    highlighted: true,
    icon: <Zap className="w-6 h-6" />,
    limits: {
      videos: 12,
      clips: 'Ilimitados',
      watermark: false,
      queue: 'Padrão',
      api: false,
      maxDuration: 60,
    },
    features: [
      '12 vídeos por mês',
      'Clips ilimitados por vídeo',
      'Sem marca d\'água',
      'Vídeos até 60 minutos',
      'Processamento com IA avançada',
      'Legendas automáticas',
      'Detecção de momentos virais',
      'Análise de engajamento',
      'Fila padrão',
      'Suporte por email',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    description: 'Para agências e alto volume',
    price: 499,
    currency: 'BRL',
    interval: '/mês',
    priceId: 'price_1SUSowCMwpJ5YuyfiRMdGv15',
    icon: <Rocket className="w-6 h-6" />,
    limits: {
      videos: 50,
      clips: 'Ilimitados',
      watermark: false,
      queue: 'Prioritária',
      api: true,
      maxDuration: 120,
    },
    features: [
      '50 vídeos por mês',
      'Clips ilimitados por vídeo',
      'Sem marca d\'água',
      'Vídeos até 120 minutos',
      'Acesso via API',
      'Fila prioritária',
      'Processamento mais rápido',
      'IA avançada com análise profunda',
      'Webhooks personalizados',
      'Análise de engajamento avançada',
      'Suporte prioritário',
      'Personalização de branding',
    ],
  },
];

export default function PricingPage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [currentPlan, setCurrentPlan] = useState<string | null>(null);
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    // Check if user is authenticated and get their current plan
    if (isAuthenticated()) {
      getSubscriptionStatus()
        .then((status) => {
          setSubscriptionStatus(status);
          setCurrentPlan(status.plan);
        })
        .catch((err) => {
          console.error('Error fetching subscription status:', err);
        });
    }
  }, []);

  const handleSubscribe = async (priceId: string, tierId: string) => {
    if (tierId === 'free') {
      // Redirect to signup for free tier
      window.location.href = '/auth/register';
      return;
    }

    // If already on this plan, go to portal
    if (currentPlan === tierId) {
      window.location.href = `${API_BASE_URL}/subscriptions/portal`;
      return;
    }

    setLoading(tierId);

    try {
      // Call backend to create checkout session
      const response = await fetch(
        `${API_BASE_URL}/subscriptions/create-checkout`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: JSON.stringify({
            price_id: priceId,
            success_url: `${window.location.origin}/videos?session_id={CHECKOUT_SESSION_ID}&upgraded=true`,
            cancel_url: `${window.location.origin}/pricing`,
          }),
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          // Not authenticated, redirect to login
          window.location.href = `/auth/login?redirect=${encodeURIComponent('/pricing')}`;
          return;
        }
        throw new Error('Failed to create checkout session');
      }

      const data = await response.json();

      if (data.url) {
        // Redirect to Stripe Checkout
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('Error creating checkout session:', error);
      alert('Erro ao criar sessão de pagamento. Tente novamente.');
    } finally {
      setLoading(null);
    }
  };

  const getButtonText = (tierId: string) => {
    if (loading === tierId) return 'Carregando...';
    if (currentPlan === tierId) return 'Plano Atual';
    if (tierId === 'free') return 'Começar Grátis';
    if (currentPlan && pricingTiers.findIndex(t => t.id === tierId) > pricingTiers.findIndex(t => t.id === currentPlan)) {
      return 'Fazer Upgrade';
    }
    return 'Assinar Agora';
  };

  return (
    <div className="min-h-screen bg-linear-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4 bg-linear-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Escolha seu plano
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Transforme seus vídeos longos em clips virais com o poder da IA.
            Comece gratuitamente e escale conforme sua necessidade.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-7xl mx-auto">
          {pricingTiers.map((tier) => (
            <div
              key={tier.id}
              className={`relative rounded-2xl border-2 p-8 ${tier.highlighted
                ? 'border-blue-500 shadow-2xl scale-105 bg-white dark:bg-gray-800'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                } transition-transform hover:scale-105`}
            >
              {tier.highlighted && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-linear-to-r from-blue-600 to-purple-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                    Mais Popular
                  </span>
                </div>
              )}

              {/* Icon */}
              <div
                className={`inline-flex p-3 rounded-xl mb-4 ${tier.highlighted
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300'
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                  }`}
              >
                {tier.icon}
              </div>

              {/* Name & Description */}
              <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                {tier.description}
              </p>

              {/* Price */}
              <div className="mb-6">
                <div className="flex items-baseline">
                  <span className="text-5xl font-bold">
                    {tier.currency === 'BRL' ? 'R$' : '$'}
                    {tier.price}
                  </span>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">
                    {tier.interval}
                  </span>
                </div>
              </div>

              {/* CTA Button */}
              <button
                onClick={() => handleSubscribe(tier.priceId, tier.id)}
                disabled={loading === tier.id || currentPlan === tier.id}
                className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors mb-8 ${currentPlan === tier.id
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100 cursor-default'
                  : tier.highlighted
                    ? 'bg-linear-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700'
                    : 'bg-gray-900 text-white hover:bg-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {currentPlan === tier.id && (
                  <Crown className="inline-block w-4 h-4 mr-2" />
                )}
                {getButtonText(tier.id)}
              </button>

              {/* Features */}
              <div className="space-y-3">
                {tier.features.map((feature, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <Check
                      className={`w-5 h-5 mt-0.5 shrink-0 ${tier.highlighted
                        ? 'text-blue-600'
                        : 'text-gray-600 dark:text-gray-400'
                        }`}
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {feature}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* FAQ or Additional Info */}
        <div className="mt-20 text-center">
          <h2 className="text-3xl font-bold mb-8">Perguntas Frequentes</h2>
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto text-left">
            <div>
              <h3 className="font-semibold mb-2 text-lg">
                Posso cancelar a qualquer momento?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Sim! Você pode cancelar sua assinatura a qualquer momento. Você
                continuará tendo acesso até o final do período pago.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 text-lg">
                O que acontece se eu exceder meu limite?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Você será notificado e poderá fazer upgrade para um plano superior
                ou aguardar o próximo ciclo de cobrança.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 text-lg">
                Como funciona a fila prioritária?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Assinantes Pro têm processamento mais rápido e seus vídeos são
                processados antes dos outros planos.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2 text-lg">
                Posso testar antes de assinar?
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Sim! O plano Free permite processar 2 vídeos por mês para você
                testar todas as funcionalidades.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
