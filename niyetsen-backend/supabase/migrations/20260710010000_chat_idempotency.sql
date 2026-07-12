-- Niyetsen — Faz 2: sohbet kayıtlarını idempotent yap.
-- İstemci aynı geçmişi yeniden gönderse veya istek retry edilse bile aynı mesaj
-- ikinci kez yazılmaz. Eski satırlar NULL kalabilir; yeni mesajlarda kimlik zorunlu.

alter table public.chat_msgs
  add column if not exists client_message_id text;

create unique index if not exists chat_msgs_user_client_message_uidx
  on public.chat_msgs(user_id, client_message_id);
