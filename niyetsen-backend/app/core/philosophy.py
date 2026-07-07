"""
Niyetsen — ANA FELSEFE (kodun anayasası)
=========================================

Bu dosya süs değildir. Cursor ve her katkıcı, bir özellik yazarken buradaki
yasalarla çelişip çelişmediğini kontrol eder. Çelişiyorsa özellik yanlıştır.

AMAÇ
----
İnsanlar hedef koyar, başlar, bitiremez. Niyetsen'in tek işi şudur:
kullanıcının "bu yıl nasıl bir hayat istiyorum" niyetini söze, sözü GÜNLÜK
GÖREVLERE, görevleri de kırılmayan bir ZİNCİRE dönüştürmek. Yıl sonunda
kullanıcının elinde hayal edilmiş değil, YAŞANMIŞ bir vizyon listesi kalır.

Fal, tarot, burç bir kader fermanı değil; kullanıcının kendine bakacağı bir
AYNADIR. Korku satmayız, merak ve anlam satarız. Dürüstlük, Niyetsen'i diğer
fal uygulamalarından ayıran şeydir.

TASARIM YASALARI
----------------
1. KAYIP HİSSİ + KİMLİK, ASLA SUÇLULUK.
   "23 günlük zincirin seni bekliyor" ✅   "Yine yapmadın" ❌
   Kendini hırpalayan kullanıcı bırakır; öz-şefkatli kullanıcı devam eder.
   Ceza mekanikleri caydırır ama asla aşağılamaz: katlanma TAVANLIDIR (200),
   puan asla negatife düşmez, dürüstçe mazeret bildiren katlanmadan kurtulur.

2. EN KÜÇÜK HALKA > MÜKEMMEL GÜN.
   Yorgun günde 2 dakikalık görev, zinciri kırmaktan iyidir (Atomik
   Alışkanlıklar / 2 dakika kuralı). Sistem her zaman bir "en küçük halka"
   çıkışı sunar; asla ya-hep-ya-hiç dayatmaz.

3. PLAN UYDURULMAZ, HAYATTAN TÜRETİLİR.
   Her görev, kullanıcının sohbette anlattığı hayattan çıkar. Şablon görev
   üreten kod hatalıdır.

4. MODEL SADECE TANIMLI ARAÇLARI KULLANIR.
   alarm, takvim, görev, kanıt, puan, mazeret, (v2: harita, görsel).
   Bilet, ödeme, dosya işlemi YOK. Araç listesi core/tools.py'de kapalıdır.

5. TERAPİST DEĞİLİZ.
   Kriz sinyalinde motivasyon konuşması DURUR; şefkatle profesyonel desteğe
   yönlendirilir. Bu kural koddadır (safety kontrolü), sadece prompt'ta değil.

6. KULLANICIYI TANIMAK = HER İSTEKTE BELLEĞİ ENJEKTE ETMEK.
   Modelin hafızası yoktur. "Hep hatırlar" hissi, prompt_builder'ın her
   istekte KULLANICI BELLEĞİ bloğunu kurmasıyla yaratılır.

7. SIR KODA YAZILMAZ. Anahtarlar .env'de; kod os.environ'dan okur.

8. ÖLÇÜLMEYEN ŞEY YOKTUR.
   Aha anı, tamamlanan görev, paywall — hepsi event'tir. Yatırımcı hikâyesi
   projeksiyon değil, gerçek retention eğrisidir.
"""

# Bildirim/mesaj tonu için hızlı kontrol listesi (UI metni yazan herkes için):
TONE_ALLOWED = ("kayıp hissi", "kimlik hatırlatması", "nazik dürtme", "yarına davet")
TONE_FORBIDDEN = ("suçlama", "utandırma", "tembelsin", "başaramıyorsun", "yine mi")
