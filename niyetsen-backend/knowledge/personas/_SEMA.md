# Persona Dossier Şeması (İdol Modu — Dalga 4.3)

Her idol için `knowledge/personas/<slug>.json` dosyası açılır; script
`python -m scripts.ingest_personas` ile Supabase'e (idol_personas +
persona_chunks) yazar. DB ASIL KAYNAKTIR; JSON dosyaları versiyonlanmış tohum.

## Zorunlu alanlar
```json
{
  "slug": "greenlights-yolu",
  "path_name": "Greenlights Yolu",
  "tagline": "engeli fırsata çevirmek",
  "category": "sanat",
  "inspired_by": "Matthew McConaughey",
  "source_note": "Bu yol Matthew McConaughey'nin 'Greenlights' kitabında anlattığı yaklaşımdan ilham alır; kendisiyle bağlantılı değildir.",
  "tags": ["direnç", "engel", "günlük tutma"],
  "dossier": {
    "why_important": "…",
    "core_beliefs": ["…"],
    "mindset": "…",
    "habits": ["…"],
    "daily_routine": "…",
    "sports_or_physical_practice": "…",
    "reading_profile": "…",
    "books_read_or_recommended": ["…"],
    "decision_style": "…",
    "failure_and_recovery": "…",
    "public_quotes": ["…"],
    "lessons_for_users": ["…"],
    "sources": ["https://…"]
  }
}
```

## Kurallar (ihlal = store/hukuk riski)
1. `path_name` FELSEFE adıdır, kişi adı değildir. Arayüzde bu görünür.
2. Kişi adı yalnız `inspired_by` + `source_note` içinde geçer.
3. Yalnız KAMUYA AÇIK üretkenlik/disiplin pratikleri; özel hayat, sağlık,
   din, siyaset, tartışmalı görüşler YASAK.
4. `public_quotes`: kısa alıntı (≤25 kelime) + kaynak zorunlu.
5. `lessons_for_users`: Niyetsen görevine çevrilebilir, 2 dakikaya küçülebilir
   maddeler (taklit değil TERCÜME ilkesi).
6. `sources`: en az 2 güvenilir kaynak URL'si.

## Üç katman (RAG için)
- Kısa profil: 150-250 kelime → `dossier.why_important` + `mindset`
- Derin profil: 800-1200 kelime → diğer alanlara dağıtılır
- Chunk'lar: 80-150 kelime → ingest scripti otomatik böler
