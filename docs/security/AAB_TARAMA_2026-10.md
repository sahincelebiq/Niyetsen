# AAB Güvenlik Taraması — niyetsen-v9-play-internal (2026-10-17)

**Tarih:** 2026-10-17  
**Hedef:** `niyetsen-v9-play-internal.aab` — bizim ürettiğimiz Android App Bundle (`com.niyetsenai`, versionCode 9, versionName 1.0.0, Expo SDK 54 / React Native 0.81.5 / Hermes HBC v96). Rakip paket değildir.  
**SHA-256:** `841492869efcae9139e015b849670095d7bbc653d3d35af468dd30e38c14f234` (85.085.924 bayt, derleme 2026-08-11)  
**Yöntem:** Salt okunur statik tarama. Hiçbir kaynak/paket dosyası değiştirilmedi; tek yazılan dosya bu rapor. Geçici çıktı yalnız `/tmp/niyetsen-aab/`.  
**Denetçi notu:** Bu AAB 11 Ağustos tarihli; `eas.json`/`app.json`'daki bazı düzeltmeler (ör. RevenueCat anahtarı 2026-08-20) bu pakete girmemiştir. Bulgular **bu paket** içindir; F1 AAB'si üretilince aynı tarama tekrarlanmalıdır.

---

## 1. Kapsam ve yöntem

### Hangi araç çalıştı?

| Adım | Araç | Sonuç |
|------|------|-------|
| 1 | REA MCP `inspect_android_package` (JADX sağlayıcısı) | **Çalışmadı** — `capability_unavailable`: "Target … is zip; provide one standalone APK". AAB kabul edilmiyor. |
| 1 | REA MCP `inspect_apktool_client` / `decode_android_resources` | **Çalışmadı** — `apktool` başlatıcısı yok (`REA_APKTOOL_COMMAND` tanımsız). |
| 1 | Evrensel APK üretip REA'ya verme | **Mümkün değil** — makinede Java runtime, `bundletool`, `apktool`, `jadx`, `aapt2` yok; kurulum yapılmadı (salt okunur görev). |
| 2 | **Yerel yöntem (kullanılan)** | `unzip` + `/tmp` içinde yazılan 3 küçük Python aracı: (a) genel protobuf tel-format çözücü ile aapt2 proto-XML (`AndroidManifest.xml`, `res/xml/*`) ve `app_dependencies.proto` (`dependencies.pb`) okuma; (b) Hermes bytecode (HBC v96) **string tablosu ayrıştırıcı** (`strings` komutu Hermes'te string'leri birbirine yapıştırdığı için gerekli oldu); (c) maskeli regex sır taraması. Ek: `strings -n 8` (dex/lib/res), `openssl pkcs7/x509` (imza), `shasum`. |

### Taranan içerik

| Yol | Ne bakıldı |
|-----|------------|
| `base/manifest/AndroidManifest.xml` (protobuf) | izinler, bileşenler, `exported`, intent-filter/scheme, `allowBackup`, `debuggable`, `usesCleartextTraffic`, SDK seviyeleri |
| `base/dex/classes{,2..6}.dex` (57 MB, 6 dosya) | sınıf envanteri (604.218 string), dev-client/debug kalıntıları, R8 izi |
| `base/assets/index.android.bundle` (4,2 MB Hermes) | 35.625 string: `EXPO_PUBLIC_*`, URL/host, sır desenleri, dev kalıntıları |
| `base/assets/app.config` | gömülü Expo yapılandırması |
| `base/res/xml/*.xml` | backup/data-extraction kuralları, FileProvider yolları |
| `base/res/raw`, `base/resources.pb` | Firebase `google-services` kalıntısı, fontlar |
| `base/lib/<abi>/*.so` (4 ABI) | mimari/boyut, string sızıntısı |
| `BUNDLE-METADATA/*` | bağımlılık listesi (370 Maven artefaktı), AGP/D8 sürümü, debug sembolleri, obfuscation haritası var mı |
| `META-INF/*.RSA` | imza sertifikası |
| `base/root/META-INF/version-control-info.textproto` | VCS (git) sızıntısı |

Sır deseni listesi: `AIza[0-9A-Za-z_-]{35}`, `sk-…`, `sb_secret_…`, `sb_publishable_…`, `service_role`, JWT (`eyJ…\.…\.…`), RevenueCat (`goog_/appl_/amzn_/test_/rcb_`), PostHog `phc_`, Sentry DSN, `*.supabase.co`, `*.up.railway.app`, AWS `AKIA…`, `-----BEGIN … PRIVATE KEY-----`, Stripe `sk_live/pk_`, URL içi basic-auth, `X-User-Id`, `AUTH_DISABLED`, `localhost:`, `10.0.2.2`, `192.168.*`, düz `http://`.

---

## 2. Yönetici özeti

**KRİTİK: 0 — YÜKSEK: 2 — ORTA: 5 — DÜŞÜK: 6 — BİLGİ: 12.**

Pakette gizli anahtar sızıntısı **yok**: `service_role`, `sb_secret`, Gemini `AIza…`, JWT, özel anahtar, Sentry DSN, PostHog anahtarı bulunmadı; yalnız beklenen Supabase **publishable** anahtarı + Supabase/Railway origin'leri gömülü. `debuggable` yok (false), cleartext kapalı (targetSdk 36 varsayılanı), Expo Updates kapalı, `AUTH_DISABLED`/`X-User-Id` dev kalıntısı yok.

İki YÜKSEK bulgu: (1) **`RECORD_AUDIO`** izni yayın manifestinde — `app.json`'da `recordAudioAndroid:false` olmasına rağmen `expo-camera`'nın kendi manifesti ekliyor; mikrofon uygulamada gerekmiyor (Play izin politikası + Data Safety tutarsızlığı). (2) **Deep-link oturum sabitleme yüzeyi** — yalnız özel scheme (`niyetsen://`, `exp+niyetsen://`), doğrulanmış App Links yok; `completeAuthFromUrl` herhangi bir URL'den gelen `access_token`+`refresh_token` çiftini `setSession` ile kabul ediyor → kötü niyetli uygulama/link kurbanı saldırganın hesabına oturtabilir.

ORTA grubu "yayın hijyeni": R8/ProGuard kapalı (57 MB okunabilir dex), `expo-dev-launcher`/`dev-menu` tam implementasyonu (472 sınıf) release'te, Compose `PreviewActivity` `exported=true`, şablon kalıntısı `SYSTEM_ALERT_WINDOW`, ve bu AAB'de RevenueCat anahtarı / `google-services.json` / Sentry bulunmaması (paywall, uzak push ve çökme telemetrisi bu pakette çalışmaz).

**Karar:** Bu AAB **F1 adayı olamaz** (zaten 11 Ağustos tarihli). F1 AAB'si için Y-01, Y-02, O-01, O-03, O-04, O-05 kapatılmalı; D grubu tercihen.

---

## 3. Özet tablo

| ID | Bulgu | Seviye | Kanıt (pakette) | Aksiyon |
|----|-------|--------|-----------------|---------|
| Y-01 | Gereksiz tehlikeli izin `android.permission.RECORD_AUDIO` yayın manifestinde | **YÜKSEK** | `AndroidManifest.xml` `<uses-permission android:name="android.permission.RECORD_AUDIO">`; `app.config` içinde `"recordAudioAndroid":false` + `"microphonePermission":false`; kaynak: `node_modules/expo-camera/android/src/main/AndroidManifest.xml:3` (merger ekliyor; plugin yalnız **eklemeyi** atlıyor, kaldırmıyor) | `app.json` → `expo.android.blockedPermissions: ["android.permission.RECORD_AUDIO"]` (config-plugins `withBlockedPermissions` → `tools:node="remove"`); F1 manifestinde yokluğunu doğrula |
| Y-02 | Özel scheme deep link + URL'den token kabulü = oturum sabitleme (login CSRF) | **YÜKSEK** | Manifest: `MainActivity` `exported=true`, `<data android:scheme="niyetsen">`, `<data android:scheme="exp+niyetsen">`; `https` applink/`autoVerify` **yok**. Kod: [`auth-redirect.ts:100-115`](../../mobile/src/lib/auth-redirect.ts) `access_token`+`refresh_token` varsa `supabase.auth.setSession(...)` (nonce/state yok). PKCE açık ([`supabase.ts:113`](../../mobile/src/lib/supabase.ts)) ama token yolu yedek olarak duruyor | Token (implicit) yolunu kaldır — PKCE `code` + `token_hash` (`verifyOtp`) yeterli; auth dönüşünü ayrı yola kilitle (`niyetsen://auth/callback`) ve akış başlamadan üretilen `state`'i doğrula; mümkünse `https://niyetsen.com/auth/*` **App Links** (`assetlinks.json`, `android:autoVerify="true"`) |
| O-01 | R8/ProGuard (minify + shrink) kapalı | ORTA | 6 dex = 57 MB; tüm sınıf adları açık (`Lcom/niyetsenai/MainActivity;`, `Lexpo/modules/devlauncher/...`); kısaltılmış `La/b;` sınıfı 0; `BUNDLE-METADATA/com.android.tools.build.obfuscation/` **yok** | `android/gradle.properties` (veya EAS `expo-build-properties`): `enableMinifyInReleaseBuilds=true`, `enableShrinkResourcesInReleaseBuilds=true`; Reanimated/Expo keep kuralları ile gerçek cihazda smoke |
| O-02 | `expo-dev-launcher` / `expo-dev-menu` tam implementasyonu release'te | ORTA | dex'te **472** sınıf: `DevLauncherController`, `DevLauncherReactHost`, `DevLauncherRemoteLogManager`, `DevMenuManager`, Apollo GraphQL `GetBranchesQuery`/`MeQuery`, Koin; `app.config` plugins: `"expo-dev-client"`. Manifestte `DevLauncherActivity` **yok** → etkin değil (ölü kod) | O-01 (R8) çoğunu siler. Ek: production EAS profilinde `expo-dev-client` plugin'ini `app.config.js` ile profil-şartlı yap (yalnız `development`) |
| O-03 | `androidx.compose.ui.tooling.PreviewActivity` `exported=true` | ORTA | Manifest: `<activity android:exported="true" android:name="androidx.compose.ui.tooling.PreviewActivity">`; bağımlılık `androidx.compose.ui:ui-tooling:1.9.0` release classpath'inde | Herhangi bir uygulama bu activity'yi başlatıp keyfi `@Preview` composable çizdirebilir (crash/DoS, içerik gösterimi). `ui-tooling`'i release'ten dışla (`configurations.releaseRuntimeClasspath.exclude group:'androidx.compose.ui', module:'ui-tooling'`) veya manifestte `tools:node="remove"` |
| O-04 | `SYSTEM_ALERT_WINDOW` (başka uygulamaların üzerinde göster) izni | ORTA | `<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW">` — Expo şablon/RN debug kalıntısı; uygulama kullanmıyor | `blockedPermissions`'a ekle; Play "sensitive permission" incelemesi ve Data Safety tutarlılığı |
| O-05 | Bu AAB'de RevenueCat anahtarı, `google-services.json`, Sentry/PostHog **yok** (işlev, güvenlik değil) | ORTA (yayın hazırlığı) | Hermes: `goog_…` deseni **0**, `phc_` 0, DSN 0; `resources.pb`'de `google_app_id`/`gcm_defaultSenderId` yok; dex'te `io/sentry` 0, `posthog` 0; eas.json RC anahtarı 2026-08-20'de eklendi (AAB 08-11) | F1 AAB'sinde doğrula: `goog_…` gömülü, `google_app_id` resource var, Sentry DSN var. Yoksa paywall "Abonelik bulunamadı", uzak push sessiz, çökme görünmez |
| D-01 | `android:allowBackup="true"` | DÜŞÜK | Manifest `allowBackup=true`, `fullBackupContent=@xml/secure_store_backup_rules`, `dataExtractionRules=@xml/secure_store_data_extraction_rules` → yalnız `sharedpref` dahil, `SecureStore` hariç; AsyncStorage DB dahil değil. Yedeğe giren: RevenueCat/expo-notifications/Firebase installations tercihleri | F1'de `android:allowBackup=false` (önceki rapor M-09 ile aynı) |
| D-02 | Eski depolama izinleri | DÜŞÜK | `WRITE_EXTERNAL_STORAGE` (maxSdk yok), `READ_EXTERNAL_STORAGE` (maxSdk 32) — galeri picker yok, kullanılmıyor | `blockedPermissions`'a ekle; Play "storage" sorgularını azaltır |
| D-03 | `expo.modules.clipboard.ClipboardFileProvider` `exported=true` | DÜŞÜK | Manifest provider exported; `clipboard_provider_paths.xml` yalnız `cache/.clipboard/` | Expo tasarımı (panoya görsel için gerekli). Kabul; görsel kopyalama kullanılmıyorsa `expo-clipboard` çıkarılabilir |
| D-04 | Amazon Appstore IAP SDK + `com.amazon.device.iap.ResponseReceiver` `exported=true` | DÜŞÜK | `com.amazon.device:amazon-appstore-sdk:3.0.5`, `purchases-store-amazon:10.16.0`; receiver `android:permission="com.amazon.inapp.purchasing.Permission.NOTIFY"` ile korunuyor | Play-only ise RN purchases Amazon modülünü dışla (gradle exclude) — izin korumalı olduğu için acil değil |
| D-05 | Eski/kullanılmayan geçişli kütüphaneler | DÜŞÜK | `com.google.guava:guava:28.1-android` (2019), `commons-io:commons-io:2.6` (CVE-2021-29425 `FilenameUtils.normalize`; kullanıcı: expo-constants/document-picker), `commons-codec:1.10`; `play-services-location:19.0.0` + `places-placereport` (konum izni **yok**, kullanılmıyor); `play-services-ads-identifier:17.0.1` (RevenueCat; `AD_ID` izni yok → Android 13+'da sıfır döner) | `npm audit`/`gradle dependencies` ile F1'de güncelle; Data Safety'de "reklam kimliği toplanmıyor" tutarlı kalsın |
| D-06 | ML Kit barkod modelleri + `libbarhopper_v3.so` | DÜŞÜK | `base/assets/mlkit_barcode_models/` 868 KB (3 `.tflite`), `libbarhopper_v3.so` 4,9 MB/ABI, `play-services-mlkit-barcode-scanning:18.3.1`, `com.google.mlkit.vision.DEPENDENCIES=barcode_ui` | Niyetsen barkod okumuyor; `expo-camera`'nın sabit bağımlılığı. Boyut/yüzey — kabul edilebilir, not düşüldü |
| B-01 | Supabase publishable anahtarı gömülü | BİLGİ | Hermes: `sb_pub…` (46 kar.) — **beklenen**, RLS ile korunur | Prod RLS doğrulaması (önceki rapor H-05) hâlâ ön şart |
| B-02 | Supabase + API origin gömülü | BİLGİ | `https://ktweah….supabase.co`, `https://api-production-….up.railway.app` | Beklenen (public endpoint) |
| B-03 | Dev kalıntısı yok | BİLGİ | `AUTH_DISABLED` 0, `X-User-Id` 0; `localhost:8081`/`localhost:9999`/`10.0.2.2:8081`/`localhost:19006` yalnız RN Metro / supabase-js / dev-launcher kütüphane varsayılanları | — |
| B-04 | `debuggable` yok, `testOnly` yok, `usesCleartextTraffic` yok (API 28+ varsayılan **false**), `networkSecurityConfig` yok | BİLGİ | Manifest `<application …>` | Tercihen F1'de açık `network_security_config` (cleartext false, sistem CA) |
| B-05 | `minSdk 24 / targetSdk 36 / compileSdk 36`, AGP 8.11.0, D8 8.11.18 (`isDebugModeEnabled:false`), Kotlin 2.1.20, `extractNativeLibs=false` | BİLGİ | `uses-sdk`, `BUNDLE-METADATA` | Play API-36 şartı karşılanıyor |
| B-06 | Expo Updates **kapalı** | BİLGİ | `expo.modules.updates.ENABLED=false`; `expo.modules.updates` dex'te yok | OTA saldırı yüzeyi yok (bu pakette) |
| B-07 | İmza: EAS upload anahtarı | BİLGİ | `META-INF/72C67BC6.RSA` — Subject/Issuer `C=US` dışı boş DN, geçerlilik 2026-08-04 → 2053-12-20, SHA-256 `C4:2A:7F:C9:…:A6:93`; AAB v1 (jarsigner) imzalı — Play App Signing yeniden imzalar | Upload key kaybına karşı Play App Signing açık olduğunu doğrula; `.jks`/`credentials.json` mobil repoda **gitignore'da** (tracked değil) |
| B-08 | Native lib: 4 ABI, 25 `.so`/ABI | BİLGİ | arm64-v8a 22 MB, armeabi-v7a 15 MB, x86 24 MB, x86_64 24 MB; `libhermes.so` release | Play ABI split sunar; x86/x86_64 yalnız emülatör — istenirse çıkarılabilir (upload boyutu) |
| B-09 | Native debug sembolleri | BİLGİ | `BUNDLE-METADATA/com.android.tools.build.debugsymbols/` 73 MB (`.sym`, 4 ABI) — Play native crash sembolizasyonu; cihaza inmez | İyi uygulama, koru |
| B-10 | `app.config` gömülü | BİLGİ | `owner:"sahincelebiq"`, EAS `projectId`, iOS `bundleIdentifier com.niyetsen.app`, plugin listesi, izin metinleri | Sır değil (expo-constants davranışı) |
| B-11 | Yasal metinler + iletişim e-postası gömülü | BİLGİ | `ai@niyetsen.com`, veri sorumlusu adı, KVKK metinleri; `https://niyetsen.com/gizlilik.html`, `/kullanim-kosullari.html` | Beklenen |
| B-12 | VCS sızıntısı yok | BİLGİ | `version-control-info.textproto`: `NO_SUPPORTED_VCS_FOUND` | — |

---

## 4. İzinler

Toplam **35** `uses-permission` (16'sı üretici rozet izni). Uygulama gereksinimi: in-app kamera, push bildirim, takvim yazma (araç `takvime_ekle`), IAP. Mikrofon / konum / kişiler **gerekmez**.

| İzin | Kaynak | Değerlendirme |
|------|--------|---------------|
| `CAMERA` | `app.json` + expo-camera | ✅ Gerekli (kanıt fotoğrafı, fal) |
| `INTERNET`, `ACCESS_NETWORK_STATE` | şablon / RN / Firebase | ✅ |
| `READ_CALENDAR`, `WRITE_CALENDAR` | `app.json` + expo-calendar 15.0.8 | ✅ Gerekli (takvim aracı). Tehlikeli izin → runtime istemi + Data Safety "Takvim" beyanı |
| `com.android.vending.BILLING` | `app.json` + billing 8.3.0 | ✅ |
| `POST_NOTIFICATIONS`, `VIBRATE`, `WAKE_LOCK`, `RECEIVE_BOOT_COMPLETED`, `com.google.android.c2dm.permission.RECEIVE` | expo-notifications 0.32.17 / FCM | ✅ (BOOT_COMPLETED zamanlanmış bildirim için) |
| **`RECORD_AUDIO`** | expo-camera native manifest (plugin `recordAudioAndroid:false` kaldırmıyor) | ❌ **Y-01** — kaldır |
| **`SYSTEM_ALERT_WINDOW`** | Expo şablonu / RN debug kalıntısı | ❌ **O-04** — kaldır |
| `WRITE_EXTERNAL_STORAGE` (maxSdk yok), `READ_EXTERNAL_STORAGE` (maxSdk 32) | şablon / kütüphane | ⚠️ **D-02** — kullanılmıyor (galeri picker yok), kaldır |
| `USE_BIOMETRIC`, `USE_FINGERPRINT` | androidx.biometric 1.1.0 (expo-secure-store) | ℹ️ normal seviye, runtime istemi yok; `requireAuthentication` kullanılmıyorsa zararsız |
| `com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE` | installreferrer 2.2 (RevenueCat atıf) | ℹ️ |
| `com.niyetsenai.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` (signature) | androidx.core | ℹ️ standart |
| 16× üretici rozet izni (`com.sec.android.provider.badge.*`, `com.huawei.*`, `com.oppo.*`, `com.htc.*`, `com.sonyericsson.*`, `me.everything.*`, `com.anddoes.*`, `com.majeur.*`, `android.permission.READ_APP_BADGE`) | ShortcutBadger 1.1.22 (expo-notifications) | ℹ️ normal seviye; Play'de göstermez |

**Olmayanlar (iyi):** `ACCESS_FINE/COARSE_LOCATION`, `READ_CONTACTS`, `READ_MEDIA_IMAGES/VIDEO`, `READ_PHONE_STATE`, `com.google.android.gms.permission.AD_ID`, `REQUEST_INSTALL_PACKAGES`, `FOREGROUND_SERVICE`.

`<queries>`: `VIEW https`, `VIEW content`, `OPEN_DOCUMENT(_TREE)`, `SEND */*`, CustomTabs, CameraX vendor extension, Play Billing bind, Billing test companion — paket görünürlüğü makul.

---

## 5. Bileşenler ve deep link

### `exported="true"` bileşenler (6)

| Bileşen | Tür | Koruma | Değerlendirme |
|---------|-----|--------|---------------|
| `com.niyetsenai.MainActivity` | activity, `singleTask` | — (launcher) | ✅ Beklenen; deep link alıcısı (bkz. Y-02) |
| `expo.modules.clipboard.ClipboardFileProvider` | provider | yol: `cache/.clipboard/` | ⚠️ D-03 |
| `com.google.firebase.iid.FirebaseInstanceIdReceiver` | receiver | `com.google.android.c2dm.permission.SEND` | ✅ standart FCM |
| `androidx.compose.ui.tooling.PreviewActivity` | activity | **yok** | ❌ **O-03** |
| `com.amazon.device.iap.ResponseReceiver` | receiver | `com.amazon.inapp.purchasing.Permission.NOTIFY` | ⚠️ D-04 |
| `androidx.profileinstaller.ProfileInstallReceiver` | receiver | `android.permission.DUMP` (yalnız shell/sistem) | ✅ standart |

`exported` olmayan 23 bileşen (expo-notifications servis/receiver/forwarder, `FileSystemFileProvider`, `SharingFileProvider`, Firebase servisleri, RevenueCat `PaywallActivity`/`CustomerCenterActivity`, Billing proxy activity'leri, ML Kit, CameraX, androidx-startup, datatransport) — sorun yok. `ProxyAmazonBillingActivity` ve `SimulatedStoreErrorDialogActivity` `exported` belirtmiyor ve intent-filter'ı yok → API 31+'da varsayılan **false**.

### Deep link

| Öğe | Değer |
|-----|-------|
| Scheme'ler | `niyetsen://` (app.json `scheme`), `exp+niyetsen://` (Expo otomatik — dev-client için üretilir, release'te de kalır) |
| `https` App Links | **yok** (`android:autoVerify` yok, `niyetsen.com` host filtresi yok) |
| Rotalar (Hermes'te görülen) | `/paywall`, `/rapor`, `/mystic`, expo-router tab grupları |
| Auth dönüşü | `completeAuthFromUrl(url)` — `code` (PKCE ✅), `token_hash`+`type` (OTP/recovery ✅), **`access_token`+`refresh_token` (implicit — ❌ Y-02)** |

**Y-02 senaryosu:** Cihazdaki kötü niyetli uygulama (veya tarayıcı/QR'dan açılan link) `niyetsen://x#access_token=<saldırganın>&refresh_token=<saldırganın>` fırlatır → `setSession` başarılı → kurban saldırganın hesabında oturum açmış olur; sonraki kanıt fotoğrafları, sohbet ve plan verisi saldırganın hesabına yazılır. Supabase `setSession` token'ın bu cihaza ait olduğunu bilemez. Özel scheme Android'de tekil değildir (başka uygulama da `niyetsen` kaydedebilir); App Links ile `https` dönüşü yalnız doğrulanmış uygulamaya iner.

---

## 6. Sır taraması (maskeli)

Desenler 4 kaynakta tarandı: Hermes string tablosu (35.625), dex (604.218), res/root/assets (84.364), native lib (167.210).

| Desen | Hermes | Dex | Res/Lib | Sonuç |
|-------|--------|-----|---------|-------|
| `AIza…` (Google/Gemini) | 0 | 0 | 0 | ✅ Gemini istemcide yok |
| `sk-…` | 0 | 0 | 0 | ✅ |
| `sb_secret_…` | yalnız **ön ek literal'i** (`sb_secret_` — anahtar reddi kontrol kodu) | 0 | 0 | ✅ değer yok |
| `service_role` | 3 — hepsi **koruma mesajı** ("…service_role yalnızca backend'de yaşar", "Legacy service_role JWT mobilde kullanılamaz…") | 0 | 0 | ✅ |
| JWT `eyJ…\.…\.…` | 0 | 0 | 0 | ✅ legacy anon JWT bile yok |
| `sb_publishable_…` | **1** → `sb_pub…` (46 kar.) | 0 | 0 | ℹ️ B-01 beklenen public anahtar |
| RevenueCat `goog_/appl_/amzn_/test_/rcb_` | **0** | 0 | 0 | ⚠️ O-05 — anahtar bu pakette **yok** |
| PostHog `phc_` | 0 (`https://us.i.posthog.com` varsayılan host string'i var) | 0 | 0 | ℹ️ PostHog bu pakette etkin değil |
| Sentry DSN | 0 | 0 (`io/sentry` sınıfı yok) | 0 | ℹ️ Sentry bu pakette yok |
| `*.supabase.co` | 1 → `ktweah…` | 0 | 0 | ℹ️ B-02 |
| `*.up.railway.app` | 1 → `api-pr…` | 0 | 0 | ℹ️ B-02 |
| AWS / private key / Stripe live / Slack / GitHub token | 0 | 0 | 0 | ✅ (`js.stripe.com`, `cdn.paddle.com` string'leri RevenueCat web-billing SDK sabitleri) |
| URL içi basic-auth | 0 | 0 | 0 | ✅ |
| `X-User-Id`, `AUTH_DISABLED` | 0 | 0 | 0 | ✅ |
| `localhost:*`, `10.0.2.2` | 2 / 0 | 1 / 2 | 4 / 0 | ℹ️ kütüphane varsayılanları (Metro 8081, GoTrue 9999, web 19006) |
| düz `http://` (standart XML ns dışı) | 0 | 2 (Metro `http://10.0.2.2:8081`, `http://filesystem.local`) | 5 (lib içi `http://` ön ekleri) | ✅ uygulama trafiği yok |
| E-posta | `ai@niyetsen.com` (yasal metin), `krzys.magiera@gmail.com` (react-native-gesture-handler lisans/author string'i) | — | — | ℹ️ |

Dosya sistemi kontrolü: `base/assets/` içinde yalnız `app.config`, `index.android.bundle`, `mlkit_barcode_models/` — **`.env`, `google-services.json`, `.jks`, `credentials.json` yok** ✅. Mobil repodaki `credentials.json`, `credentials/`, `@sahincelebiq__niyetsen.bak.jks` git-ignore'da (`.gitignore:45-48`), tracked değil ✅.

---

## 7. Gömülü env değerleri (`EXPO_PUBLIC_*`)

Expo, `process.env.EXPO_PUBLIC_X` ifadelerini derlemede **değere** çevirir; ad yalnız string literal olarak kullanıldığında kalır.

| Değişken | Bu pakette | Not |
|----------|-----------|-----|
| `EXPO_PUBLIC_API_URL` | ✅ değer gömülü (`https://api-production-….up.railway.app`) | Public origin |
| `EXPO_PUBLIC_SUPABASE_URL` | ✅ (`https://ktweah….supabase.co`) | Public |
| `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | ✅ (`sb_pub…`) | Public; RLS şart |
| `EXPO_PUBLIC_REVENUECAT_API_KEY` / `_ANDROID_API_KEY` | ❌ **yok** (hata metni var: "RevenueCat yapılandırılamadı. EXPO_PUBLIC_REVENUECAT_API_KEY kontrol et.") | O-05 — eas.json'a 08-20'de eklendi |
| `EXPO_PUBLIC_RC_ENTITLEMENT_ID` / `_MONTHLY_PACKAGE` / `_YEARLY_PACKAGE` | ✅ `premium`, `$rc_monthly`, `$rc_annual` | Sır değil |
| `EXPO_PUBLIC_POSTHOG_KEY` / `_HOST` | ❌ anahtar yok; host varsayılanı var | Telemetri kapalı |
| `EXPO_PUBLIC_SENTRY_DSN` | ❌ yok | Çökme telemetrisi kapalı |
| `EXPO_PUBLIC_SUPABASE_SECRET_KEY`, `EXPO_PUBLIC_SUPABASE_SERVICE_KEY` | yalnız **ad** (literal) — `supabase-keys.ts` koruma kontrolü | Değer yok ✅ |

Dev kalıntısı: `AUTH_DISABLED` / `X-User-Id` **yok**. `__DEV__`, `HMRClient`, `Remote JS Debugging` gibi 7 string RN çekirdeğinin olağan release string'leri (koşullu dal, etkin değil). `babel.config.js`'te `transform-remove-console` yok → `console.*` çağrıları bundle'da kalır (önceki rapor D-03; `src/` içinde `console.log` yok).

---

## 8. Kütüphane envanteri

`dependencies.pb`: **370** Maven artefaktı. Öne çıkanlar:

| Grup | Artefakt(lar) | Sürüm | Not |
|------|---------------|-------|-----|
| React Native | `react-android`, `hermes-android` | 0.81.5 | ✅ güncel (SDK 54) |
| Expo modülleri | application 7.0.8, calendar 15.0.8, camera 17.0.10, clipboard 8.0.8, crypto 15.0.9, device 8.0.10, documentpicker 14.0.8, filesystem 19.0.23, font 14.0.12, keepawake 15.0.8, linking 8.0.12, notifications 0.32.17, securestore 15.0.8, sharing 14.0.8, splashscreen 31.0.13, systemui 6.0.9, webbrowser 15.0.11, image 3.0.11, asset 12.0.13 | SDK 54 | `expo-updates` **yok** (kapalı) |
| Expo dev araçları | `expo-dev-launcher`, `expo-dev-menu` (dex'te; AAR listesinde `expo-dev-client` plugin) + Apollo 4.3.1, Koin 3.5.6, Compose Multiplatform 1.8.1 | — | **O-02** — yalnız dev-launcher için gelen ~20 artefakt |
| RevenueCat | `purchases` 10.16.0, `purchases-ui` 10.16.0, `purchases-store-amazon` 10.16.0, `purchases-hybrid-common(-ui)` 18.28.0 | ✅ güncel | Amazon modülü D-04 |
| Play Billing | `com.android.billingclient:billing` | 8.3.0 | ✅ Play şartı (≥7) |
| Firebase | `firebase-messaging` 24.0.1, `firebase-installations`, `datatransport` | ✅ | `google-services` resource **yok** (O-05) |
| Play Services | base 18.5.0, basement 18.9.0, tasks 18.2.0, cloud-messaging 17.2.0, **location 19.0.0**, places-placereport 17.0.0, **ads-identifier 17.0.1**, auth-blockstore 16.4.0, code-scanner 16.1.0, mlkit-barcode-scanning 18.3.1, stats 17.0.2 | — | location/ads-identifier geçişli, kullanılmıyor (D-05) |
| ML Kit | barcode-scanning 17.3.0, vision-common 17.3.0, common 18.11.0 | — | D-06 |
| Ağ | okhttp 4.12.0, okio, okhttp-urlconnection | ✅ | — |
| Kripto | `com.google.crypto.tink:tink-android` 1.8.0 (expo-secure-store) | ✅ güncel | — |
| JSON | gson 2.8.9 (CVE-2022-25647 düzeltilmiş) | ✅ | — |
| Eski | **guava 28.1-android**, **commons-io 2.6**, commons-codec 1.10 | ⚠️ | D-05 |
| Görsel | Fresco (RN), Glide 4.16.0 (+avif), Coil 2.4.0 + Coil3 3.0.4, androidsvg 1.4, apng/awebp decoders | — | expo-image + RevenueCat UI |
| Compose | ui 1.9.0, material3 1.3.0, **ui-tooling 1.9.0** (release'te) | ⚠️ | O-03 |
| Kotlin | stdlib 2.1.21, coroutines 1.9.0, serialization-json 1.7.3, datetime | ✅ | — |
| AndroidX | biometric 1.1.0, browser 1.8.0, camera-* 1.5.0-rc01, webkit 1.12.1, core-splashscreen, profileinstaller | ✅ | WebView bileşeni kullanılmıyor (webkit geçişli) |

Build: AGP 8.11.0, Gradle 8.14.3, Kotlin plugin 2.1.20, D8 8.11.18, Java 17 hedef, `minSdk 24`.

### Manifest bayrakları

| Bayrak | Değer | Durum |
|--------|-------|-------|
| `android:debuggable` | belirtilmemiş → **false** | ✅ |
| `android:usesCleartextTraffic` | belirtilmemiş → targetSdk 36'da **false** | ✅ |
| `android:allowBackup` | **true** (+ kurallar) | ⚠️ D-01 |
| `android:extractNativeLibs` | false | ✅ |
| `android:testOnly` | yok | ✅ |
| `networkSecurityConfig` | yok | ℹ️ B-04 |
| Expo Updates | `ENABLED=false` | ✅ |

### Native kütüphaneler (`base/lib`)

| ABI | Dosya | Boyut | Not |
|-----|-------|-------|-----|
| arm64-v8a | 25 `.so` | 22 MB | gerçek cihazların çoğu |
| armeabi-v7a | 25 | 15 MB | eski cihazlar |
| x86 | 25 | 24 MB | emülatör; isteğe bağlı |
| x86_64 | 25 | 24 MB | emülatör/Chromebook |

Büyükler (arm64): `libreactnative.so` 5,9 MB, `libbarhopper_v3.so` 4,9 MB (ML Kit), `libhermes.so` 2,1 MB, `libreanimated.so` 1,4 MB, `libexpo-modules-core.so` 1,3 MB, `libc++_shared.so` 1,3 MB. `libhermes.so` içinde debugger/inspector string'i yok (release derleme). Toplam AAB 85 MB (sıkıştırılmış); Play cihaza ABI/yoğunluk split'i indirir.

---

## 9. Sonuç ve F1 için öneriler

### Bu AAB için karar
`niyetsen-v9-play-internal.aab` **sır sızdırmıyor** ve temel sertleştirmeleri (debuggable=false, cleartext kapalı, OTA kapalı, service_role/Gemini istemcide yok) karşılıyor. Ancak **F1 adayı değildir**: RevenueCat/FCM/Sentry bu pakette yok, mikrofon izni var, oturum sabitleme yüzeyi açık, R8 kapalı.

### F1 öncesi yapılacaklar (öncelik sırası)

1. **Y-02 — auth deep link sertleştirme (kod):** `auth-redirect.ts`'te `access_token`/`refresh_token` dalını kaldır (PKCE `code` + `token_hash` yolları kalsın); dönüş URL'sini `niyetsen://auth/callback` ile sınırla ve OAuth başlatılırken üretilen `state`'i SecureStore'da tutup dönüşte doğrula. Orta vadede `https://niyetsen.com/auth/*` App Links (`/.well-known/assetlinks.json`, SHA-256 = Play App Signing anahtarı) + `android:autoVerify="true"`.
2. **Y-01 / O-04 / D-02 — izin temizliği (config):** `app.json` → `"android": { "blockedPermissions": ["android.permission.RECORD_AUDIO", "android.permission.SYSTEM_ALERT_WINDOW", "android.permission.WRITE_EXTERNAL_STORAGE", "android.permission.READ_EXTERNAL_STORAGE"] }`. F1 AAB'sinde manifest tekrar okunup doğrulanır.
3. **O-01 — R8 aç (build):** `expo-build-properties` ile `enableMinifyInReleaseBuilds: true`, `enableShrinkResourcesInReleaseBuilds: true`; Reanimated/Worklets/RevenueCat/Expo keep kuralları varsayılan AAR'larda gelir; gerçek cihazda sohbet + kanıt + paywall + bildirim smoke'u şart. Mapping dosyasını Play'e yükle (çökme sembolizasyonu).
4. **O-02 — dev-client'ı production'dan ayır:** `app.config.js` içinde `plugins`'e `expo-dev-client`'ı yalnız `process.env.EAS_BUILD_PROFILE === 'development'` iken ekle. R8 zaten ölü kodu siler ama scheme `exp+niyetsen` ve Apollo/Koin bağımlılıkları da gider.
5. **O-03 — Compose tooling'i release'ten dışla:** `expo-build-properties` `extraMavenRepos` değil; `android/app/build.gradle`'a (prebuild sonrası veya config-plugin ile) `configurations.releaseRuntimeClasspath { exclude group: 'androidx.compose.ui', module: 'ui-tooling' }` veya manifestte `<activity android:name="androidx.compose.ui.tooling.PreviewActivity" tools:node="remove"/>`.
6. **O-05 — F1 AAB doğrulama listesi:** Hermes'te `goog_…` var, `resources.pb`'de `google_app_id` var, dex'te `io/sentry` var, `EXPO_PUBLIC_SENTRY_DSN` değeri gömülü, `expo.modules.updates.ENABLED` bilinçli (OTA açılacaksa code-signing).
7. **D-01 — `allowBackup=false`** (`expo-build-properties` → `android.allowBackup: false`).
8. **D-04 / D-05 / D-06 — bağımlılık diyeti (isteğe bağlı):** Amazon IAP modülünü dışla; `npm audit` + `gradle dependencies` ile guava/commons-io güncel sürümlere çekilebiliyorsa çek; ML Kit barkod kabul edilebilir.
9. **Tekrar tarama:** F1 AAB için bu rapordaki yöntem aynen tekrarlanır (`/tmp` araçları yeniden yazılabilir; repoya alınmadı). Mümkünse Java + `bundletool build-apks --mode=universal` ile evrensel APK üretip REA `inspect_android_package` / `decode_android_resources` ile çapraz doğrulama.

### Önceki raporla ilişki (`DENETIM_RAPORU.md`, 2026-08-02)
- M-09 (targetSdk/allowBackup/cleartext **DOĞRULANAMADI**) → artık **doğrulandı**: targetSdk 36 ✅, cleartext kapalı ✅, `allowBackup=true` ⚠️ (D-01).
- "service_role mobilde reddedilir" / "İstemci Gemini yok" → pakette **doğrulandı** (bölüm 6).
- EXPO_PUBLIC envanteri → bu pakette RC/Sentry/PostHog **boş** (O-05).
- Y-02 yeni bulgudur; önceki rapor deep-link yüzeyine bakmamıştı.
