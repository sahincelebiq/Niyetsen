# Android (Play kapalı sürüm) açılışta çökme — Tanı Rehberi (2026-08-05)

## Önce büyük gerçek

Play'den indirdiğin uygulama, **EAS build alındığı andaki kodun donmuş
fotoğrafıdır.** Son haftaların düzeltmeleri (rapor, kapı-içeride, minimal UI,
mistik, thread dayanıklılığı, consent hızlı yolu) o binary'de YOK. Bu yüzden:
1. Önce push + **yeni build** al: `eas build --profile play-internal --platform android`
2. Yeni AAB'yi dahili teste yükle, cihazda tekrar dene.
Eski binary üzerinde hata avlamak, dünkü gazetede bugünün haberini aramaktır.

## Çökmenin GERÇEK satırını yakala (2 dakika, kesin yöntem)

Statik analiz şüpheli listeler; kesin tanı yalnız cihaz logundadır:

```bash
# Telefonu USB ile bağla (USB hata ayıklama açık), sonra:
adb logcat -c                        # logu temizle
# → uygulamayı aç, çökmesini bekle ←
adb logcat -d | grep -A 40 -m 1 "FATAL EXCEPTION\|AndroidRuntime"
```

Çıkan bloğu olduğu gibi Claude'a/Cursor'a yapıştır — ilk 5 satır kökü söyler.
(adb yoksa: `brew install android-platform-tools`.)

## Statik analizde ELENEN şüpheliler (2026-08-05, Claude Cowork)

- ✅ `EXPO_PUBLIC_API_URL` eksikliği: api.ts prod URL fallback'li — çökmez.
- ✅ RevenueCat: anahtar yoksa configure hiç çağrılmıyor (guard'lı) — çökmez.
- ✅ Reanimated 4 + SDK 54: worklets eklentisini babel-preset-expo yönetiyor;
  yeni mimari SDK 54 varsayılanı. app.json'da devre dışı bırakılMAMIŞ ✓.
- ✅ Sentry/PostHog: DSN/key yoksa no-op guard'lı.

## Açık kalan şüpheliler (logcat çıktısıyla eşleştir)

1. **`I18nManager.forceRTL`** (locale-provider): Arapça seçildiyse restart
   sonrası RTL zorlanır; bazı cihaz/sürümlerde açılış döngüsü yapabilir.
   Logda `I18nManager` / layout hatası görürsen → RTL'i geçici kapat.
2. **Yeni native modüller** (view-shot, sharing, purchases-ui): binary bunlar
   eklenmeden ÖNCE alındıysa ve Play'deki sürümle JS güncellemesi (EAS Update)
   eşleşmediyse → `requireNativeComponent` hatası. Çözüm zaten "yeni build".
3. **ProGuard/R8 minify** (release-only): logda `ClassNotFoundException` →
   eas.json'a `"android": {"enableProguardInReleaseBuilds": false}` dene
   veya kural ekle.
4. **google-services eksikken push kaydı**: logda FirebaseApp hatası →
   push token çağrısını try/catch + build'e google-services.json ekle.

## Bu turda koda giren ilgili düzeltmeler (yeni build'e girecek)

- Consent hızlı yolu: "Yasal tercihler kontrol ediliyor…" artık YALNIZ ilk
  kurulumda bloklar; sonraki açılışlar cache'ten anında geçer, sunucu arka
  planda doğrulanır (`consent-gate.tsx`, yasal sürüm değişince gate döner).
- i18n iskelet tespiti: `Copy.` kullanan 8 çekirdek dosya (index, daily,
  paywall, rank, explore, chat-composer, plan-task-editor, chat-header) —
  dil değişiminde iskeletin Türkçe kalma nedeni. Cursor görevi: FAZ8 8.11.
