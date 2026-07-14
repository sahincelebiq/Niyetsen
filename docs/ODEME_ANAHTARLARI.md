# Ödeme Anahtarları — RevenueCat vs Stripe

> **Niyetsen mobil uygulama (v1):** yalnızca **RevenueCat + Apple/Google IAP**.  
> Stripe bu fazda uygulama aboneliği için **kullanılmaz** (Apple kuralları + MASTER_PLAN).

## RevenueCat — ihtiyacın olan 3 key (+ 1 senin ürettiğin secret)

| # | İsim | Nereden alınır | Nereye yazılır | Örnek prefix |
|---|------|----------------|----------------|--------------|
| 1 | **Secret API key** | RevenueCat → **Project Settings → API keys → Secret keys** | `niyetsen-backend/.env` → `REVENUECAT_API_KEY` | `sk_` (RC) |
| 2 | **iOS Public SDK key** | RevenueCat → **Apps → iOS** uygulaması ekledikten sonra | `mobile/.env` → `EXPO_PUBLIC_REVENUECAT_IOS_API_KEY` | `appl_` |
| 3 | **Android Public SDK key** | RevenueCat → **Apps → Android** uygulaması ekledikten sonra | `mobile/.env` → `EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY` | `goog_` |

### 4. şey key değil — webhook secret (zaten hazır)

`REVENUECAT_WEBHOOK_SECRET` = **senin ürettiğin** rastgele değer (script zaten yazdı).

- Backend `.env` ve Railway'de var
- RevenueCat → **Integrations → Webhooks → Authorization:** `Bearer <aynı değer>`

**Stripe `pk_test_` / `sk_test_` RevenueCat key'i DEĞİLDİR.** Karıştırma.

### Sadece 2 RC key bulduysan

Muhtemel sebepler:
1. Henüz **hem iOS hem Android** app eklemedin → tek platform key'i var
2. **Secret API key**'e bakmadın → Project Settings'te, mobil key'lerden ayrı yerde
3. Stripe key'lerini RC sanıyorsun → farklı servis

### Senkron komutu (3 RC key dolunca)

```bash
cd niyetsen-backend
.venv/bin/python -m scripts.setup_kapi5_secrets
```

---

## Stripe — v1'de ne işe yarar / yaramaz

| Kullanım | v1 mobil | Not |
|----------|----------|-----|
| App Store / Play abonelik | ❌ | RevenueCat + IAP |
| niyetsen.com web ödeme (gelecek) | ⏸ | Ayrı proje; şimdi kod yok |
| Fatura / B2B (Invoicing) | ⏸ | İleride; key'ler saklandı |
| Terminal (fiziksel POS) | ❌ | Uygulama ile ilgisiz |

Stripe key'leri: `niyetsen-backend/.env.stripe.local` (gitignore'da, commit edilmez).

### Stripe MCP (Cursor — isteğe bağlı)

Mobil ödeme için gerekli değil. İleride web/B2B için:

1. Cursor → Marketplace → **Stripe** plugin veya `~/.cursor/mcp.json`:
   ```json
   { "mcpServers": { "stripe": { "url": "https://mcp.stripe.com" } } }
   ```
2. Oturumu yenile → OAuth ile Stripe'a bağlan
3. `stripe_implementation_planner` ile plan üret

---

## Güvenlik

- Key'leri sohbete yapıştırma — göründüyse **Stripe dashboard'dan rotate** et
- `.env`, `.env.stripe.local` asla git'e girmez
- Prod mobil ödeme: harici ödeme linki yok (yalnız IAP)
