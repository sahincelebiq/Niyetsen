-- FAZ 8: sohbet kişiselleştirmesi için isteğe bağlı cinsiyet alanı.
-- KVKK notu: zorunlu değildir; yalnız hitap/örnek uyarlaması için kullanılır.
alter table public.users
  add column if not exists gender text
  check (gender is null or gender in ('kadın', 'erkek', 'belirtmek istemiyorum'));
