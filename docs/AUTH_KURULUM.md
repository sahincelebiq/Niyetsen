# Niyetsen — Auth kurulum kontrol listesi

Kod tarafı ham 5xx sızıntısını kapatır; **kayıt / şifre sıfırlama / OTP
ancak mail çıkınca** çalışır. Confirm email’i kapatmak çözüm değildir —
sıfırlama her hâlükârda mail ister.

Canlı doğrulama (2026-09-06, proje `ktweahgrrppmxpdhohdh`):

| İstek | Sonuç |
|---|---|
| `POST /auth/v1/token` (yanlış şifre) | 400 `invalid_credentials` — uç nokta ayakta |
| `POST /auth/v1/signup` (takım dışı e-posta) | 500 `Error sending confirmation email` |
| `POST /auth/v1/recover` (mevcut kullanıcı) | 500 `Error sending recovery email` |
| Google / Apple | `provider is not enabled` |
| `mailer_autoconfirm` | kapalı (doğru; kapatma) |
| `disable_signup` | kapalı (doğru; herkes kayıt olabilir) |

Auth Logs ham hata (bugün, signup + recover + otp):

```
dial tcp: address https://niyetsen.com/:465: too many colons in address
```

Yani custom SMTP **açık sanılıyor** ama Host alanı `https://niyetsen.com/`
yazılmış, port 465. GoTrue bunu TCP adresi sanıp düşüyor. Mail hiç çıkmıyor.

`niyetsen.com` DNS’inde Hostinger mail **doğru** (MX + SPF + DKIM + DMARC).
Resend şart değil — Hostinger kutusunu doğru host ile bağla.

---

## A1. Auth Logs

Supabase → **Logs → Auth**. Son `/signup`, `/recover`, `/otp` satırını aç.
`error` alanında ham metni not et. A3 kaydından sonra bu hata **0** olmalı.

## A2. Acil erişim (kök nedeni çözmez)

Authentication → **Users → Add user** → e-posta + şifre → **Auto Confirm User**.
Yalnız test / Play reviewer için. Mail hâlâ kırık kalır.

Play reviewer (`reviewer@niyetsen.com`) onaylanmamışsa burada onayla; şifreyi
Play notundaki değerle aynı tut.

Büşra (`busra.pehlivan@fauna-studio.com`): hesap **onaylı**, sağlayıcı yalnız
`email`. Son başarılı giriş 31 Ağu. Google kimliği yok. Bugün 4 kez
`invalid_credentials` — şifre hatası / unutma. “Şifremi unuttum” SMTP
düzelmeden 500 verir.

## A3. SMTP’yi düzelt (bugünün asıl işi)

Authentication → **Emails → SMTP Settings → Enable Custom SMTP**.

**Yanlış (şu an canlıda):** Host = `https://niyetsen.com/` · Port = 465

**Doğru:**

| Alan | Değer |
|---|---|
| Host | `smtp.hostinger.com` (`https://` yok, slash yok) |
| Port | **587** (STARTTLS). 465 kullanma. |
| Kullanıcı | `ai@niyetsen.com` (yoksa `no-reply@niyetsen.com`) |
| Şifre | o kutunun Hostinger şifresi |
| Sender email | aynı kutu |
| Sender name | `Niyetsen` |

Kartın kendi **Save**’ine bas. From adresi doğrulanmış alan adında olmalı.

hPanel → **Emails**: kutu yoksa oluştur, webmail’den kendine test at.

DNS (bozma):

- MX: `mx1.hostinger.com` / `mx2.hostinger.com`
- SPF: `v=spf1 include:_spf.mail.hostinger.com ~all`
- DKIM: `hostingermail-a|b|c._domainkey`
- DMARC: `v=DMARC1; p=none`

Kayıt: Authentication → **Rate Limits** — custom SMTP sonrası varsayılan
~30/saat; kapalı test + canlı için 100/saat makul.

## A4. Şablonlar

Authentication → Emails → Templates: confirm signup, magic link, recovery,
invite. Türkçeleştir. OTP şablonunda `{{ .Token }}` kalsın; mobil 6–8 hane
kabul eder. Confirm email **açık kalsın**.

## A5. Redirect URL

Authentication → **URL Configuration** (Google kartı değil).

**Site URL** yalnız bu olsun:

```
https://niyetsen.com
```

Google kartındaki `…supabase.co/auth/v1/callback` buraya **yapıştırılmaz**.
O adres Google → Supabase iç köprüsüdür; tarayıcıda sayfa değildir.
Site URL oraya yazılırsa şifre sıfırlama mailindeki link bozulur
(Şahin’in 2026-09-06 gördüğü boş / yanlış sayfa).

Redirect URLs (yoksa ekle, Save):

```
https://niyetsen.com/**
https://niyetsen.com/auth/callback
https://niyetsen.com/sifre-sifirla
niyetsen://**
niyetsen://auth/callback
niyetsen://sifre-sifirla
http://localhost:8081/**
http://localhost:3000/**
```

`niyetsen.con` yazım hatası varsa sil.

Şifre sıfırlama: kullanıcı **maildeki kodu uygulamaya yazar**. Linke
Mac/telefonda tıklaması gerekmez. Link yine de `niyetsen.com/auth/callback`
veya `niyetsen://auth/callback` olmalı — asla Google callback.

## A6. Google (kapalı test + canlı — aynı ayar)

Authentication → Providers → **Google** kartı → Enable → **o kartın Save**.
Client ID/secret boşsa Supabase kaydı sessizce geri alır; toggle yeşil
görünür, canlıda `provider is not enabled` kalır.

Google Cloud → APIs & Services → Credentials:

1. **Web** client: Client ID + secret → Supabase Google alanlarına.
2. Web client **Authorized redirect URI**:
   `https://ktweahgrrppmxpdhohdh.supabase.co/auth/v1/callback`
3. **Android** client: paket `com.niyetsenai` + SHA-1’ler.
4. Authorized Client IDs: web **ve** Android ID, virgülle. Web ID **önce**.

SHA-1 (yükleme / EAS anahtarı — 2026-09-04 keystore):

```
CC:84:4C:A5:C9:75:17:0B:CF:03:27:DC:E6:E1:0D:BB:4C:82:31:C6
```

SHA-256 (aynı yükleme anahtarı):

```
C4:2A:7F:C9:93:4A:57:D3:7D:8F:2D:C1:C1:AF:2A:DB:CF:26:48:A3:33:F8:B2:A1:DA:16:67:3F:4B:3D:A6:93
```

Play App Signing açıksa **Sürüm → Kurulum → Uygulama bütünlüğü → Uygulama
imzalama anahtarı** SHA-1 / SHA-256’yı da Android OAuth client’a ekle.
Yerel debug SHA-1 ayrıdır (`~/.android/debug.keystore`). Üçü de yoksa
cihazda `DEVELOPER_ERROR` (code 10) olur.

Uygulama akışı: Google butonu → Google hesap seçimi →
`niyetsen://auth/callback` → oturum. Kapalı test ve production aynı
provider’ı kullanır; mağaza yayınında Auth’u yeniden kapatmaya gerek yok.

Apple: Providers → Apple ayrıca açılır; iOS bundle `com.niyetsen.app`.

## A7. Attack Protection

Authentication → Attack Protection → **Leaked password protection** aç
(HaveIBeenPwned). Advisor uyarısı duruyor.

## A8. Doğrulama (takımda OLMAYAN bir e-posta)

1. Kayıt → mail geldi mi (spam dahil)?
2. Şifre sıfırlama → kod geldi, uygulamada yeni şifre kaydedildi mi?
3. Üst üste 3 istek → 60 sn cooldown, Auth Logs’ta 500 yok.
4. Google: Play build + “Google ile devam et” → hesap bağlanınca Niyetsen açılır.
5. Google ekranını kapatınca banner çıkmamalı.

KAPI: bu turda Auth Logs’ta 0 adet 500; Google `authorize` 302 (400 değil).

---

## Kod tarafı

- 5xx / `unexpected_failure` → Türkçe `sunucu_hatasi` banner; ham JSON yok.
- Ağ / timeout → `baglanti_hatasi`.
- Eşlenmeyen hata → `bilinmeyen` (sunucu metni ekrana düşmez).
- Mail gönderen butonlar 60 sn kilitli.
- `niyetsen://auth/callback` + `niyetsen://sifre-sifirla` callback rotasına düşer.
- OTP kutusu 6–8 hane (GoTrue `email_otp` 8 hane dönebiliyor).

SMTP host düzelmeden kayıt/şifre sıfırlama **sunucuda** 500 vermeye devam eder.
Mevcut **onaylı** hesap e-posta + doğru şifre ile giriş yapabilir (token
uç noktası sağlam).
