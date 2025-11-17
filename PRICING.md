# ClipAI Pricing – Koyeb L40S Edition (Nov/2025)

Esta versão substitui os cálculos antigos baseados em GPU RTX 4070/RunPod e considera o ambiente **Koyeb GPU L40S (15 vCPU / 64 GB RAM / 48 GB VRAM)** que você já ligou para o serviço (`llama.cpp`).

## 1. Entradas confirmadas

| Item | Valor | Fonte |
| --- | --- | --- |
| Tarifa on-demand L40S | **US$ 1.20 / hora = US$ 0.000333 / segundo** | [Koyeb Pricing](https://www.koyeb.com/pricing) |
| Cobrança | Contínua, "pay-per-use by the second" (não há desconto em idle se o serviço estiver ligado) | [Koyeb Pricing FAQ](https://www.koyeb.com/pricing) |
| TF32/FP32 do L40S | 91.6 TFLOPS FP32 | [NVIDIA L40S Specs](https://www.nvidia.com/en-us/data-center/l40s/) |
| Taxa de câmbio adotada | **R$ 5,00 / US$ 1,00** (mesma premissa do plano anterior) | Interna |
| Custos adicionais por vídeo | **R$ 0,20** (storage + banda Cloudflare R2) | Plano 2.0 |
| Taxas Stripe + impostos | **10% da receita bruta** (4% Stripe + R$0,40 ~ 6% impostos) | Plano 2.0 |

> ⚠️ A Koyeb cobra enquanto a VM GPU estiver ativa. Se o serviço `llama.cpp` ficar 24h/dia online, o custo fixo mensal só da GPU é **US$ 864 ≈ R$ 4.320** (1.20 × 24 × 30).

## 2. Custo variável por vídeo na GPU nova

O pipeline completo consumia ~30 minutos de GPU com a RTX 4070. O L40S tem ~3,1× mais throughput FP32 (91.6 vs ~29 TFLOPS), mas o ganho não será totalmente linear porque há gargalos de I/O e CPU. Usei três cenários para ter segurança:

| Cenário | Tempo de GPU por vídeo (30 min) | Custo GPU (US$) | Custo GPU (R$) | Custo total (R$) |
| --- | --- | --- | --- | --- |
| **Melhor caso** – 40% do tempo antigo (9–12 min) | 0,20 h | 0,24 | 1,20 | 1,40 |
| **Base recomendado** – 60% do tempo antigo (18 min) | 0,30 h | 0,36 | 1,80 | 2,00 |
| **Pior caso** – nenhum ganho real (30 min) | 0,50 h | 0,60 | 3,00 | 3,20 |

Vou usar **R$ 2,00/vídeo** como referência para montar os planos (equilíbrio entre segurança e competitividade). Se os testes mostrarem tempo mais curto, dá para aumentar os limites depois.

## 3. Planos sugeridos

### 3.1 Free (Marketing)
- **Preço:** R$ 0/mês.
- **Limites:** 2 vídeos ou 3 clips (o que acabar primeiro) por mês, com marca d'água.
- **Custo esperado:** 2 × R$ 2,00 = **R$ 4,00** por usuário realmente ativo.
- **Justificativa:** suficiente para demo sem explodir custo. Se muitos usuários atingirem o limite, force upgrade (mostrar CTA no painel).

### 3.2 Starter
- **Objetivo:** criadores individuais com 1–3 uploads por semana.
- **Limites propostos:** 12 vídeos/mês, clips ilimitados, sem marca d'água, fila padrão.
- **Custo variável:** 12 × R$ 2,00 = **R$ 24,00**.
- **Preço recomendado:** **R$ 149/mês**.
  - Receita líquida após 10% taxas ≈ R$ 134,10.
  - Margem após custo variável ≈ **R$ 110,10**.
- **Break-even de infraestrutura:** com este plano sozinho, cada cliente cobre ~R$ 110. Para pagar os ~R$ 4.600 fixos (GPU 24/7 + API/DB/Redis ≈ R$ 275) são necessários **42 clientes Starter** se não houver Pro. Qualquer automação para desligar a GPU em idle reduz essa exigência drasticamente.

### 3.3 Pro
- **Objetivo:** agências e criadores com alto volume (2+ uploads por dia) e automação/API.
- **Limites propostos:** 50 vídeos/mês, acesso via API + prioridade na fila.
- **Custo variável:** 50 × R$ 2,00 = **R$ 100,00**.
- **Preço recomendado:** **R$ 499/mês**.
  - Receita líquida pós-taxas ≈ R$ 449,10.
  - Margem após custo variável ≈ **R$ 349,10**.
- **Break-even combinado:** supondo mix 70% Starter / 30% Pro, a margem média ponderada fica ~R$ 182. Com isso o ponto de equilíbrio do stack completo cai para **26 clientes pagantes**.

## 4. Stripe
Os produtos "Starter" e "Pro" já existem no Stripe (verificado via CLI), mas estão com valores antigos (R$ 29 / R$ 119). Atualize-os ou crie novos `price_id` com os seguintes valores:

| Plano | Novo preço | Cobrança | Observações |
| --- | --- | --- | --- |
| Free | R$ 0 | Recorrência manual | Apenas criar um `plan` gratuito para controle/quota. |
| Starter | R$ 149 | Mensal | Atualize `STRIPE_PRICE_STARTER` no `.env` após criar o novo preço. |
| Pro | R$ 499 | Mensal | Atualize `STRIPE_PRICE_PRO`. |

> Sugestão: aproveite o Stripe Billing para aplicar **metered billing** futuro (cobrar excesso de vídeos a R$ 5/unid). Por enquanto mantenha limites rígidos no backend.

## 5. Próximos passos
1. **Validar custo real**: execute 5–10 vídeos no L40S e registre `pipeline_time` e `estimated GPU cost` já calculados pelo logger do `video_processor`. Se o custo ficar consistentemente abaixo de R$ 2, ajuste a tabela.
2. **Automatizar economia**: se o serviço `llama.cpp` ficar ocioso por longos períodos, considere pausar a instância via API da Koyeb (escala to zero) ou usar o recurso de autoscaling deles para reduzir horas pagas.
3. **Comunicar limites no app**: mostre no frontend (dashboard) quantos vídeos restam em cada plano.
4. **Atualizar docs públicos**: substitua os valores de `project/PRICING.md` por um resumo desta página assim que validar custo real.

---
Qualquer ajuste de preço deve sempre considerar os três cenários de custo. Quando houver dados reais da L40S (tempo médio por vídeo), repita a planilha e ajuste os limites antes de reabrir campanhas de marketing.
