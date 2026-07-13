# Supabase SQL Editor — Düzen rehberi

Bu klasördeki dosyalar **git’teki tek kaynak**. Supabase Dashboard’daki
kaydedilmiş sorgular (PRIVATE listesi) yalnızca UI kısayoludur; silinmeleri
uygulamayı bozmaz.

## Hangi dosyayı ne zaman çalıştır?

| Dosya | Ne zaman |
|-------|----------|
| `migrations/RUN_IN_SUPABASE_SQL_EDITOR.sql` | **Mevcut prod** — eksik kolon + veri onarımı (çoğu kurulumda yeterli) |
| `VERIFY_HEALTH.sql` | Her deploy sonrası — yalnızca okuma, uyarı çıkmaz |
| `migrations/*.sql` | Sıfırdan kurulum veya geçmiş referans (sırayla) |

## SQL Editor’da yapıştırma

1. VS Code / Cursor’da dosyayı aç
2. **Tüm içeriği** kopyala (Ctrl/Cmd+A → C)
3. Supabase → SQL Editor → yeni sorgu
4. Yapıştır → **Run**
5. `VERIFY_HEALTH.sql` ile doğrula

**Dosya yolunu yapıştırmayın** — `niyetsen-backend/...sql` yazmak syntax error verir.

## PRIVATE sorguları temizleme (önerilen)

Sidebar’daki eski denemeleri sil; şunları **tut** (yeniden oluştur):

| Tut | Ad (öneri) | İçerik |
|-----|------------|--------|
| ✅ | `Niyetsen — Prod güncelleme` | `RUN_IN_SUPABASE_SQL_EDITOR.sql` |
| ✅ | `Niyetsen — Sağlık kontrolü` | `VERIFY_HEALTH.sql` |
| ✅ | `Niyetsen — Çekirdek tablolar` | `20260707000000_niyetsen_core_tables.sql` (yedek) |

**Silinebilir** (23 PRIVATE listesindeki tümü — veritabanına dokunmaz):

- `Untitled query`
- `çoklu plan projeleri`, `çoklu plan projeleri 2`, `çoklu plan projeleri 3`
- `doğrulama`, `sadece doğrulama`
- `yıldızlara ulaşamıyorum hata...`
- `Tam düzenleme opsiyonel`, `kolon planlama`, `Çoklu Plan`
- `plan 1`, `abonelik çoklu plan`, `push token`, `Genural Versiyon`
- `Niyetsen çekirdek tablolar` (yedek olarak repoda duruyor)
- `Niyetsen sohbet geçmişi...`, `Niyetsen sohbet kayıtlarını id...`
- `onboarding profili ve KVKK r...`, `Unsplash kalite ve attribution...`
- `foto kanıtı, puan olayları...`, `public placeholder' kısmı`
- `Key kısımları`, `İlk zemin`

Hepsini silip yalnızca yukarıdaki **2 canonical** sorguyu bırak.

## Otomatik denetim (lokal)

Railway project token ile prod şema kontrolü:

```bash
cd niyetsen-backend
export RAILWAY_PROJECT_TOKEN='<project-token>'
python -m scripts.run_prod_supabase_audit
```

`.env` içine service key yazmanız gerekmez; script Railway API servisinden okur.
