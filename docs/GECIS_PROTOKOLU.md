# Yedek, geri yükleme tatbikatı ve sunucu geçişi protokolü (V2 §7)

> **Veri kaybı önlem kapısı.** Yedeksiz DDL yok; haftalık tatbikat yeşil
> değilse Faz 7 (büyük sunucuya geçiş) başlamaz. İlk tatbikat: 2026-10-17
> (aşağıda "Tatbikat kayıtları").

## 1. Bileşenler (kodda, 2026-10-17)

| Parça | Yer | Ne yapar |
|---|---|---|
| Saf mantık | `niyetsen-backend/app/core/backup.py` | env → `BackupConfig`; nesne anahtarı (`niyetsen/pg/YYYY/MM/DD/niyetsen-<ts>Z.dump`); saklama süresi; `pg_dump`/`pg_restore` komutları; tablo başına **satır sayısı + md5** anlık görüntüsü; iki anlık görüntüyü karşılaştırma. `tests/test_backup.py` (18 test). |
| I/O | `scripts/backup_io.py` | `psql -At` koşucusu, `pg_dump`/`pg_restore` çağrıları, boto3 S3 istemcisi (R2/B2/MinIO uyumlu checksum ayarı). DSN her logda maskelenir. |
| Günlük yedek | `scripts/backup_pg_dump.py` | `pg_dump -Fc --no-owner --no-privileges` (şemalar `public,auth,storage`) → sha256 → snapshot → `manifest.json` → S3 upload → 30 günden eski nesneleri sil. Cron içinde `run_daily()` asla exception fırlatmaz. |
| Doğrulama | `scripts/verify_backup.py` | `snapshot` · `compare` · `fetch-latest` · `local-dump` · `drill` (boş hedefe restore + karşılaştırma; çıkış 0 = KAPI). |
| Tek komut tatbikat | `scripts/restore_drill_local.sh` | Geçici PostgreSQL 17 cluster (port 54329) → dump → restore → karşılaştır → kapat. `--from-source` (kovasız), varsayılan S3'ten en yeni. |
| Vanilla Postgres provası | `scripts/local_pg_from_migrations.sh` | Gerçek migration'ları Supabase stub'larıyla yerel PG17'de koşar (Faz 7 §7.2/1 provası + tatbikat için stand-in kaynak). |
| Cron kancası | `scripts/run_scheduled_jobs.py` → `backup` adımı | 5 dk'lık turda `BACKUP_HOUR_UTC` saatinde ve bugünün önekinde nesne yoksa yedek alır; `CRON_SKIP_BACKUP=true` kapatır. |
| İmaj | `niyetsen-backend/Dockerfile.cron` (+ `railway.cron.toml` `dockerfilePath`) | API imajı + **postgresql-client-17** (Supabase 17.6 → pg_dump 17 şart). API imajı değişmedi. |

## 2. Ortam değişkenleri (Railway `cron`)

```
BACKUP_DATABASE_URL   # session pooler 5432 (postgresql://postgres.<ref>:<şifre>@aws-1-…pooler.supabase.com:5432/postgres)
                      # boşsa DIRECT_URL kullanılır. Transaction pooler 6543 pg_dump ile ÇALIŞMAZ.
BACKUP_S3_ENDPOINT    # R2: https://<account_id>.r2.cloudflarestorage.com  | B2: https://s3.<region>.backblazeb2.com
BACKUP_S3_BUCKET      # niyetsen-backups (ÖZEL kova; public erişim kapalı)
BACKUP_S3_ACCESS_KEY / BACKUP_S3_SECRET_KEY
BACKUP_S3_REGION=auto  BACKUP_PREFIX=niyetsen/pg  BACKUP_RETENTION_DAYS=30
BACKUP_SCHEMAS=public,auth,storage  BACKUP_HOUR_UTC=1  BACKUP_VERIFY_MD5=true
```

Öneri (Şahin kararı bekliyor): **Cloudflare R2** — 10 GB/ay ücretsiz, çıkış
ücreti yok, S3 API; kova için "Object Lifecycle" kuralına gerek yok (script
30 günü kendi siler). Alternatif Backblaze B2 (10 GB ücretsiz). Hostinger
Business planında S3-uyumlu nesne deposu **yok**.

Şifre özel karakter içeriyorsa URL-encode et (`@` → `%40`, `#` → `%23`).

## 3. Haftalık tatbikat (her Pazartesi, ~2 dk)

```bash
cd niyetsen-backend
scripts/restore_drill_local.sh            # S3'teki en yeni dump → yerel PG17 → karşılaştır
# kovasız (DB'den taze dump):
scripts/restore_drill_local.sh --from-source
```

Çıktının son satırı `KAPI GEÇTİ ✅` olmalı: her tabloda satır sayısı **ve**
md5 eşit (md5 = satırların metin gösteriminin sıralı birleşimi; 500k satır
üstü tablolarda yalnız satır sayısı). Fark varsa tablo adı, tür
(`row_count|md5|missing_in_target|extra_in_target`) ve iki değer yazılır.

Sonucu aşağıdaki tabloya işle. Üç hafta üst üste kırmızı → yedek stratejisi
toplantısı; Faz 7 askıya.

Gereksinim (yerel): PostgreSQL 17 ikilileri — `brew install postgresql@17`
(PATH'e eklemeye gerek yok, script `/opt/homebrew/opt/postgresql@17/bin`'i bulur).

## 4. Üretimde ilk çalıştırma kontrol listesi

1. Supabase → Project Settings → Database → **Database password** (yoksa reset);
   `BACKUP_DATABASE_URL`'yi 5432 session pooler ile kur.
2. R2/B2'de özel kova + yalnız bu kovaya yetkili API anahtarı.
3. Railway `cron` env'ine §2 değişkenlerini gir (`api`'ye GEREKMEZ).
4. `niyetsen-backend/` içinden `railway up --service cron --ci` (Tuzak #10;
   imaj artık `Dockerfile.cron`). Log'da `cron env: {... "BACKUP": "configured"}`.
5. Elle ilk yedek: Railway shell ya da yerelde
   `python -m scripts.backup_pg_dump --force` → `backup: {"status":"done", ...}`.
6. Kovada `niyetsen/pg/YYYY/MM/DD/…dump` + `.manifest.json` görünür.
7. `scripts/restore_drill_local.sh` → `KAPI GEÇTİ ✅` → tabloya işle.
8. Ertesi gün 04:00–05:00 İstanbul arasında cron logunda `backup: {"status":"done"}`;
   sonraki turlarda `"skipped","reason":"already_today"`.

## 5. Geçiş günü (Faz 7, §7.2) — kısa protokol

1. Hedef ortam: `scripts/local_pg_from_migrations.sh` mantığıyla hedef Postgres'te
   roller + uzantılar + migration'lar koştu; `verify_backup.py drill` yeşil.
2. **Dondurma penceresi** (gece, TZ İstanbul): API 503 + mobil bakım ekranı;
   çevrimdışı kuyruk istemcide bekler.
3. Son `pg_dump` (`--force`) → hedefe `pg_restore` → `compare` **EŞİT** olmadan açılmaz
   (satır + md5 + toplam puan kontrol toplamı: `select sum(value) from points`).
4. Storage: `rclone sync` + `storage_objects` sha256 doğrulaması (Faz 2'de tablo).
5. Auth: JWKS yeni sağlayıcıya; 24 sa **çift JWKS** penceresi.
6. DNS `api.niyetsen.com` → yeni sunucu; Supabase **salt okunur** 14 gün.
7. KAPI 7: 24 sa hata < %1, puan/zincir tutarlılık raporu temiz → Supabase kapatılır.

Geri dönüş: DNS eski hedefe, Supabase salt-okunurdan yazılabilire; dondurma
penceresinde yazma olmadığı için fark yok.

## 6. Supabase-dışı Postgres provası (bugünkü sonuç)

`scripts/local_pg_from_migrations.sh` → **29 migration, 0 hata** (stub'lar:
`auth.users`, `auth.uid()`, `storage.buckets/objects`, `storage.foldername()`,
Supabase rolleri). Gerçek bağımlılık listesi: `docs/SUPABASE_BAGIMLILIK.md`.

## 7. Tatbikat kayıtları

| Tarih | Kaynak | Dump | Tablo / satır | pg_restore | Sonuç | Not |
|---|---|---|---|---|---|---|
| 2026-10-17 | **Stand-in** (gerçek migration'lar, yerel PG 17.11, örnek veri) | 84 KB, sha256 `fcc8212d…` | 24 / 24 | çıkış 1 (yalnız zararsız `schema "public" already exists`) | **EŞİT ✅** — boru hattı doğrulandı | Üretimden önce prova |
| 2026-10-18 | **Üretim Supabase** (session pooler 5432, PG 17.6 → yerel 17.11) | 364 KB, sha256 `0c6dbfd0…` | 56 / 1468 | çıkış 1, anlamlı hata 0 | **EŞİT ✅** | md5 karşılaştırması UTC + `COLLATE "C"` ile. S3'e günlük yükleme hâlâ kova anahtarı bekliyor |

KAPI 0'ın yedek yarısı: üretim satırı **yeşil** (2026-10-18). Günlük cron yüklemesi `BACKUP_S3_*` gelince başlar.
