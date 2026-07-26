# UI Cilası v2 — token + yüzey katmanı (2026-07-19)

> Karar: yatırımcı sunumundan 3 gün önce **tam yeniden tasarım YAPILMADI.**
> Mevcut marka kimliği (krem/toprak paleti, Fraunces serif başlıklar) korundu
> ve derinlik + hareketle güçlendirildi. **Layout, navigasyon, veri akışı ve
> API sözleşmelerine DOKUNULMADI** — bu yüzden demo riski minimumdur.

## Neden bu kapsam?
- 46 dosya merkezi tema katmanını kullanıyor, kodda yalnız 11 sabit renk var
  → token değişikliği tüm uygulamaya güvenle yayılır.
- Düzen/navigasyon değişikliği demo öncesi en yüksek risk kalemidir
  (kayan listeler, tıklanmayan butonlar, boş ekranlar) → yapılmadı.
- Mevcut palet piyasadaki "koyu mor + neon gradyan" AI klişesinden zaten
  ayrışıyor; onu korumak rekabet avantajıdır.

## Yapılanlar

### Tema tokenları (`constants/theme.ts`)
- `Shadows.lifted` ve `Shadows.hero`: iki katmanlı (yakın + uzak) gölge —
  kartlar zeminden kalkar, "düz beyaz kart" hissi biter.
- `SurfaceEdge`: kart üst kenarında 1px açık çizgi (ışık yukarıdan geliyor
  hissi — premium algısının en düşük maliyetli kaynağı).
- `ImageScrim`, `Motion` (fast/base/slow/stagger): tek yerden hareket ritmi.

### Tipografi (`themed-text.tsx`)
- Gövde satır yükseklikleri açıldı (24→25, 20→21), küçük metinlere hafif harf
  aralığı, serif başlıklara daha sıkı optik aralık (-0.5 → -0.8).
- **Punto ölçeği değişmedi** → hiçbir ekranda taşma/kayma olmaz.

### Yüzeyler (`ui/surface-card.tsx`)
- `elevated` artık `Shadows.lifted`, yeni `hero` bayrağı `Shadows.hero`.
- Üst kenar ışığı (tema duyarlı: açık/koyu).
- Ölçüler (padding, radius, gap) aynı.

### Sohbet ekranı
- Rehber balonu: yumuşak `FadeIn` girişi + kaldırılmış gölge + kenar ışığı.
- Kullanıcı balonu: sağdan `FadeInRight` girişi (gönderim hissi).
- "Düşünüyor" göstergesi (önceki turda): balon görünümü, sıralı üç nokta.

### Bugün ekranı (`daily.tsx`)
- Görev görselinin altına **bağımlılıksız katmanlı degrade örtü** (üç şerit) —
  metin okunurluğu artar, görsel karta yumuşak geçer.
  (`expo-linear-gradient` BİLİNÇLİ olarak eklenmedi: dev client yeniden
  derlemesi gerektirir, demo öncesi gereksiz risk.)
- Kartlar kademeli beliriyor (`FadeInDown`, ilk 6 kartta 60ms fark).

### Zincir/Rank ekranı
- `CountUpText` bileşeni: zincir günü ve toplam puan 0'dan hedefe akarak
  sayılıyor — "kazanılmış ilerleme" hissi, demo'nun en dikkat çeken anı.
- Toplam puan kartı `elevated`.

### Erişilebilirlik
- Tüm yeni animasyonlar `ReduceMotion.System` kullanır: kullanıcı sistemde
  "hareketi azalt" açtıysa animasyonlar otomatik sakinleşir.

## Geri alma (demo güvencesi)
Tüm değişiklikler görsel katmanda ve commit'siz durumda. Beğenilmezse:
```bash
cd mobile && git checkout -- src/   # her şey eski hâline döner
```
Ya da ayrı dalda tutmak için: `git switch -c ui/polish-v2` → commit → main
temiz kalır.

## Doğrulama
- `npx tsc --noEmit` → **0 hata**
- Mükerrer import / kullanılmayan sembol yok
- Backend'e dokunulmadı (175 test etkilenmedi)

## Demo öncesi elle bakılacaklar (5 dakika)
1. Bugün ekranı: kartlar kademeli beliriyor mu, görsel altı okunur mu?
2. Zincir ekranı: sayılar akıyor mu?
3. Sohbet: balonlar yumuşak giriyor mu, klavye açılınca liste düzgün mü?
4. Koyu tema: kenar ışığı ve gölgeler koyu zeminde de doğru mu?
5. Küçük ekran (iPhone SE): hiçbir metin taşmıyor mu?
