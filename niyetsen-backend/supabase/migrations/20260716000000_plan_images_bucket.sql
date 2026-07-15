-- Plan görev kartı görselleri (Nano Banana / Gemini image generation)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'plan-images',
  'plan-images',
  true,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do nothing;

-- Herkes okuyabilir (public bucket); yazma yalnız service_role (backend)
drop policy if exists "plan_images_public_read" on storage.objects;
create policy "plan_images_public_read"
on storage.objects for select
to public
using (bucket_id = 'plan-images');
