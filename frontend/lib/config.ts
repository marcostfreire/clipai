/**
 * Frontend configuration - centralized app settings
 * 
 * This file contains all configuration values that should be centralized,
 * including Stripe price IDs, API endpoints, and other constants.
 */

// =====================
// Stripe Configuration
// =====================

/**
 * Stripe Price IDs for subscription plans.
 * These should match the price IDs configured in the backend (settings.stripe_price_*)
 * 
 * To update these values:
 * 1. Update the backend .env with STRIPE_PRICE_FREE, STRIPE_PRICE_STARTER, STRIPE_PRICE_PRO
 * 2. Update these values to match
 * 3. Deploy both frontend and backend
 */
export const STRIPE_PRICE_IDS = {
  free: process.env.NEXT_PUBLIC_STRIPE_PRICE_FREE || 'price_1SUSZdCMwpJ5YuyfbFDEQh5A',
  starter: process.env.NEXT_PUBLIC_STRIPE_PRICE_STARTER || 'price_1SUSowCMwpJ5YuyfvZq5iXYZ',
  pro: process.env.NEXT_PUBLIC_STRIPE_PRICE_PRO || 'price_1SUSowCMwpJ5YuyfiRMdGv15',
} as const;

export type PlanId = keyof typeof STRIPE_PRICE_IDS;

/**
 * Get price ID for a plan
 */
export function getPriceId(plan: PlanId): string {
  return STRIPE_PRICE_IDS[plan];
}

// =====================
// Plan Configuration
// =====================

export interface PlanLimits {
  videosPerMonth: number;
  clipsPerVideo: number | 'unlimited';
  maxDurationMinutes: number;
  watermark: boolean;
  priorityQueue: boolean;
  apiAccess: boolean;
}

export const PLAN_LIMITS: Record<PlanId, PlanLimits> = {
  free: {
    videosPerMonth: 2,
    clipsPerVideo: 3,
    maxDurationMinutes: 30,
    watermark: true,
    priorityQueue: false,
    apiAccess: false,
  },
  starter: {
    videosPerMonth: 12,
    clipsPerVideo: 'unlimited',
    maxDurationMinutes: 60,
    watermark: false,
    priorityQueue: false,
    apiAccess: false,
  },
  pro: {
    videosPerMonth: 50,
    clipsPerVideo: 'unlimited',
    maxDurationMinutes: 120,
    watermark: false,
    priorityQueue: true,
    apiAccess: true,
  },
};

// =====================
// Pricing Display
// =====================

export interface PlanPricing {
  id: PlanId;
  name: string;
  description: string;
  price: number;
  currency: string;
  interval: string;
}

export const PLAN_PRICING: Record<PlanId, PlanPricing> = {
  free: {
    id: 'free',
    name: 'Free',
    description: 'Perfeito para testar a plataforma',
    price: 0,
    currency: 'BRL',
    interval: '/mês',
  },
  starter: {
    id: 'starter',
    name: 'Starter',
    description: 'Ideal para criadores individuais',
    price: 149,
    currency: 'BRL',
    interval: '/mês',
  },
  pro: {
    id: 'pro',
    name: 'Pro',
    description: 'Para agências e alto volume',
    price: 499,
    currency: 'BRL',
    interval: '/mês',
  },
};

// =====================
// App Constants
// =====================

export const APP_CONFIG = {
  // Upload limits
  maxFileSizeMB: 500,
  chunkSizeMB: 4,
  
  // URL download limits (stricter due to timeout constraints)
  maxUrlDownloadSizeMB: 200,
  maxUrlDownloadDurationMinutes: 20,
  
  // Polling intervals
  statusPollIntervalMs: 2000,
  
  // Retry configuration
  maxRetries: 3,
  retryDelayMs: 1000,
  
  // Timeouts (in ms)
  uploadTimeout: 600000, // 10 minutes
  chunkUploadTimeout: 120000, // 2 minutes
  defaultTimeout: 300000, // 5 minutes
} as const;
