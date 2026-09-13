# Geri alma betikleri

Bu klasördeki `*_down.sql` dosyaları `migrations/` dışında tutulur; `supabase db push`
yalnız `migrations/<timestamp>_<ad>.sql` desenini uygular, geri almalar yanlışlıkla
çalışmasın. Gerekirse SQL Editor'da tek seferde, ilgili up migration'ın tersi sırayla çalıştır.
