# Niyetsen — Bulgular ve Hatalar Raporu

> Bu dosya Claude tarafından `niyetsen-backend` ve `mobile` kod tabanının satır satır
> incelenmesiyle üretildi (2026-07-12). Backend testleri incelemeye başlamadan önce
> **104/104 yeşildi** — yani mevcut testler bu hataların hiçbirini yakalamıyordu; hepsi
> test kapsamının dışında kalan senaryolar.
>
> Kullanım: Bu dosyayı `NIYETSEN_YAPILAN_DEGISIKLIKLER.md` ile birlikte oku. Bu dosya
> NE bulunduğunu, diğeri NE yapıldığını anlatır. ✅ = düzeltildi ve indirdiğin zip'te
> mevcut. ⏳ = tespit edildi, henüz düzeltilmedi (Faz 4 kapanmadan önce bakılmalı).

---

## 🔴 Kritik (güvenlik / veri bütünlüğü)

### 1. ✅ Kriz filtresi Türkçe büyük harfte hiç çalışmıyordu
**Dosya:** `app/core/prompts.py` → `contains_crisis_signal`

Python'un `"İNTİHAR".lower()` çağrısı `"i̇ntihar"` üretir (İ harfi, i + görünmez
"birleşen nokta" karakterine dönüşür — U+0307). Bu yüzden `"intihar" in metin.lower()`
kontrolü, kullanıcı **büyük harfle veya Caps Lock açıkken** yazdığında **False**
dönüyordu. Kriz anında (intihar, kendine zarar verme niyeti) yanlış yazım/büyük harf
en olası senaryolardan biri — sistem tam da en kritik anda sessiz kalıyordu.

Aynı hata `contains_out_of_scope_signal`, tool-intent tespiti (`intent_service.py`)
ve bonus tamamlama mesajı eşleştirmesinde (`bonus_pool.py`) de vardı.

**Etki:** Kullanıcı güvenliği. **Önem: en yüksek.**

### 2. ✅ Gemini timeout ayarları tanımlıydı ama hiç kullanılmıyordu
**Dosya:** `app/core/gemini_client.py`

`config.py`'de `GEMINI_TIMEOUT_SEC=30` ve `GEMINI_PLAN_TIMEOUT_SEC=90` tanımlı, ama
`generate_text`/`generate_json`/`generate_function_calls` içinde hiçbir yerde
kullanılmıyordu. Gemini API bir isteği askıda bırakırsa (nadir ama olur), o worker
süresiz bekler — retry/backoff hiç devreye girmez çünkü hata fırlamaz, sadece bekler.
Yoğun trafikte bu tek istek tüm worker havuzunu tüketebilir.

**Etki:** Kararlılık, olası tam kesinti riski. **Önem: yüksek.**

### 3. ✅ Plan üretimi 35'e kadar sıralı senkron HTTP isteği yapıyordu
**Dosya:** `app/services/plan_service.py`, `app/services/image_service.py`

`generate_batch` her görev için `image_service.get_image()` çağırıyordu; bu fonksiyon
**senkron `httpx.get()`** kullanıyor. `async def generate_batch` içinde `await`
edilmeden çağrılan senkron bir HTTP isteği, FastAPI'nin event loop'unu **bloklar** —
yani o an plan üreten kullanıcı yüzünden, sunucudaki **diğer tüm kullanıcıların**
istekleri (chat, kanıt yükleme, health check) o süre boyunca bekler.

7 günlük ilk parti × maks 5 görev = 35 sıralı Unsplash isteği; her biri ~200-500ms
sürerse bu tek `/plan/generate` çağrısı 7-15 saniye boyunca **tüm sunucuyu** kilitler.

**Etki:** Ölçeklenebilirlik — kullanıcı sayısı arttıkça belirgin biçimde kötüleşir.
**Önem: yüksek**, MVP'de az kullanıcıyla fark edilmeyebilir ama store yayınından
hemen sonra sorun çıkarır.

---

## 🟠 Önemli (henüz düzeltilmedi — ⏳)

### 4. ⏳ RevenueCat webhook sırrı prod'da zorunlu değil
**Dosya:** `app/api/routes.py` → `revenuecat_webhook`

```python
secret = settings.REVENUECAT_WEBHOOK_SECRET
if secret:
    ...
```

`REVENUECAT_WEBHOOK_SECRET` boşsa doğrulama tamamen atlanıyor. `main.py`'deki
"prod'da X olmadan açılamaz" kilitleri (`AUTH_DISABLED`, `USE_SUPABASE_DB`,
`CRON_SECRET`) bu değişkeni kontrol etmiyor. Yani prod'a `.env`'de bu sır
girilmeden deploy edilirse, **herkes** `POST /webhooks/revenuecat` çağırıp
istediği kullanıcıyı "active" abone yapabilir (ücretsiz premium erişim açığı).

**Öneri:** `main.py`'deki prod-kilit desenine ekle: `ENV=prod` iken
`REVENUECAT_WEBHOOK_SECRET` boşsa `RuntimeError`.

### 5. ⏳ Abonelik iptali anında erişimi kesiyor (dönem sonuna kadar sürmeli)
**Dosya:** `app/services/subscription_service.py` → `apply_revenuecat_event`

```python
inactive_events = {"CANCELLATION", "EXPIRATION", "BILLING_ISSUE"}
```

RevenueCat `CANCELLATION` event'i kullanıcı "yenilemeyi kapat" dediğinde **hemen**
gelir — abonelik süresi bitmeden. Kod bu event'i `EXPIRATION` ile aynı kefeye koyup
anında erişimi kesiyor. Doğrusu: kullanıcı zaten ödediği dönemin sonuna kadar
(`expiration_at`) erişime devam etmeli; `CANCELLATION` sadece "yenilenmeyecek"
bilgisini not almalı, erişimi kesmemeli.

**Etki:** Parayı ödemiş kullanıcıya haksız erişim kesintisi → App Store/Play Store
şikayeti ve iade riski.

### 6. ⏳ `/plan/generate` rate limit'siz ve rıza kontrolsüz
**Dosya:** `app/api/routes.py` → `generate_plan`

Diğer maliyetli/hassas endpoint'lerin (`/chat`, `/task/{id}/proof`) hepsinde
`@limiter.limit(...)` ve `_require_consent(...)` var. `generate_plan`'da **ikisi de
yok**. Bu endpoint `GEMINI_MODEL_PLAN` (pro model, 8192 token) çağırıyor — en
pahalı endpoint tam da limitsiz olan. Ayrıca KVKK/AI-chat rızası vermemiş bir
kullanıcı da plan üretebiliyor (rıza akışını bypass ediyor).

**Öneri:** `_require_consent(user_id, "chat")` + rate limit ekle (örn. dakikada 2).

### 7. ⏳ Günlük görev listesi sunucu saatine göre hesaplanıyor
**Dosya:** `app/services/project_service.py` → `get_today_tasks`

```python
def get_today_tasks(repo, user_id, *, today=None):
    current = today or date.today()
```

`date.today()` **sunucunun** (muhtemelen UTC) tarihini verir; kullanıcının
timezone'u hesaba katılmıyor. Master Plan §1.3 zincir hesaplamasında kullanıcı
saat dilimini doğru kullanıyor (`task_lifecycle_service.py`), ama "bugünün
görevleri" ekranı bunu yapmıyor. Sonuç: gece yarısına yakın saatlerde (örn.
İstanbul'da 02:00, UTC'de hâlâ önceki gün) kullanıcı yanlış günün görevlerini
görebilir veya tamamladığı görev "bugün" listesinden düşmeyebilir.

**Öneri:** `profile_service`'ten kullanıcı timezone'unu al, `task_lifecycle_service.
_local_today`'daki gibi hesapla.

### 8. ⏳ Gün kapanışı yalnız aktif planı işliyor — çoklu plan kullanıcıları puan kaçırıyor
**Dosya:** `app/services/task_lifecycle_service.py` → `close_user_day`

```python
plan = repository.get_plan(user_id)  # sadece AKTİF planı döner
```

Master Plan §1.1.1: abone kullanıcılar birden fazla plan/proje açabiliyor
(`Plan 1`, `Plan 2`...). Ama gün kapanış cron'u yalnızca **aktif** planın
görevlerine bakıyor. Kullanıcı Plan 2'yi aktif bırakıp Plan 1'deki görevleri
kaçırırsa, o görevler **hiçbir zaman** "sessiz kaçırma" cezasına uğramıyor —
sonsuza kadar `pending` kalıyor, ceza da uygulanmıyor. Bu tam da ücretli
özelliğin (çoklu plan) en çok kullanılacağı senaryoda puan/ceza motorunun
sessizce devre dışı kalması demek.

**Öneri:** `close_user_day`, `list_plan_summaries` ile kullanıcının **tüm**
planlarını gezmeli, her birinin o günkü görevlerini kapatmalı.

### 9. ⏳ Chat mesaj kaydında olası N+1 sorgu büyümesi (Supabase)
**Dosya:** `app/storage/supabase_repository.py` → `append_chat_message`

Her `/chat` çağrısında **istemci geçmişteki tüm mesajları tekrar gönderiyor**
(routes.py: `for message in req.messages: repo.append_chat_message(...)`).
Sohbet uzadıkça (`CHAT_HISTORY_LIMIT=24` mesaj sınırı olsa da, gönderilen
`req.messages` listesi sınırsız) her istek, zaten kayıtlı onlarca mesaj için
gereksiz `upsert` çağrısı yapıyor. `ignore_duplicates=True` sayesinde veri
bozulmuyor ama gereksiz DB round-trip'i birikiyor; sohbet 100+ mesaja
ulaştığında gecikme hissedilir hale gelebilir.

**Öneri:** İstemci tarafında yalnızca **yeni** (henüz `message_id`'si
bilinmeyen) mesajları göndersin, ya da backend zaten kayıtlı `client_message_id`
kümesini tek sorguda çekip yalnız eksik olanları yazsın.

### 10. ⏳ Mobil: `/projects/new` 409'da kullanıcıyı bilgilendirmiyor
**Dosya:** `mobile/src/components/project-sheets.tsx` (gözlem — routes.py 400/402
dönebiliyor ama UI genel hata mesajı gösteriyor olabilir; detaylı UI incelemesi
henüz yapılmadı, sıradaki turda netleştirilecek)

### 11. ⏳ Mobil `api.ts`'te `fetch` çağrısına timeout yok
**Dosya:** `mobile/src/lib/api.ts` → `request()`

Ağ isteği hiç zaman aşımına uğramıyor; backend yanıt vermezse (örn. Railway
soğuk başlangıcı) kullanıcı arayüzde süresiz "gönderiliyor" durumunda kalabilir.
`AbortController` ile 15-20 sn timeout eklenmesi öneriliyor.

---

## 🟡 Küçük / kozmetik (öncelik düşük)

- `app/config.py`'de `LEGAL_DATA_CONTROLLER` varsayılanı gerçek bir isim
  (`"Şahin Çelebi"`) — `.env`'de eksik kalırsa bu prod'a sızabilir; büyük risk
  değil ama `.env.example`'da açıkça doldurulması hatırlatılmalı.
- `image_service.py`'deki `get_image_url()` (eski sözleşme) artık hiçbir yerde
  çağrılmıyor gibi görünüyor — kullanılmıyorsa temizlenebilir.
- `tests/` klasöründe İrade Modu'nun otomatik `alarm_kur` tetikleme testi yok
  (zaten Master Plan'da "eksik" olarak işaretli — §1.12).

---

## ℹ️ Genel gözlem — kod kalitesi

Mimari genel olarak **sağlam**: net katmanlama (routes → services → storage),
Repository pattern iki farklı implementasyonla (in-memory/Supabase) doğru
soyutlanmış, kapalı-liste tool-calling güvenlik yaklaşımı isabetli, puan/ceza
motoru saf fonksiyonlarla %100 test edilebilir tasarlanmış. Yukarıdaki bulgular
mimariyi değiştirmiyor — nokta atışı düzeltmeler.
