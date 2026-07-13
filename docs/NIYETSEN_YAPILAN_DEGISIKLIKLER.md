# Niyetsen — Yapılan Değişiklikler (Changelog)

> Bu dosya, `NIYETSEN_BULGULAR_VE_HATALAR.md`'de listelenen bulgulardan **şu ana
> kadar düzeltilmiş olan 3 kritik maddenin** tam kod değişikliğini içerir.
> Diğer 8 madde (§4-11, bulgular dosyasında ⏳ işaretli) henüz dokunulmadı —
> onlar için ayrı bir tur gerekecek.
>
> Backend test sonucu: değişikliklerden önce **104/104 yeşil**, sonra da
> **104/104 yeşil** (regresyon yok, sıfır test kırıldı).
>
> Nasıl uygularsın: Aşağıdaki her madde "Dosya" + "Ne değişti" + tam kod bloğu
> içeriyor. Cursor'da ilgili dosyayı aç, belirtilen fonksiyon/bloğu bul, aynen
> değiştir. Sıra önemli değil, üçü de birbirinden bağımsız.

---

## Değişiklik 1 — Türkçe büyük harf normalizasyonu (kriz filtresi güvenlik açığı)

**Dosya:** `app/core/prompts.py`

**Sorun:** `"İNTİHAR".lower()` Python'da `"i̇ntihar"` üretiyor (İ → i + görünmez
birleşen nokta U+0307), bu yüzden `"intihar" in metin.lower()` büyük harfli veya
şapkalı Türkçe karakterlerde **False** dönüyordu — kriz anında sistem sessiz
kalabiliyordu.

**Çözüm:** Türkçe'ye özel `normalize_tr()` fonksiyonu eklendi: önce İ→i, I→ı
eşlemesi yapılıyor, sonra Unicode NFD ayrıştırmasıyla tüm aksan/birleşen işaretler
temizleniyor, son olarak NFC'ye geri toplanıyor. Hem aranan metin hem anahtar
kelimeler bu fonksiyondan geçiyor.

**Ekleme — `CRISIS_RESPONSE` tanımından hemen sonra:**
```python
# Türkçe'ye duyarlı küçük harfe çevirme. Python'un lower()/casefold()'u
# "İ" harfini "i̇" (i + birleşen nokta U+0307) yapar; bu yüzden
# "İNTİHAR".lower() içinde "intihar" ARANAMAZ ve kriz filtresi büyük harfli
# mesajı kaçırırdı (2026-07-12'de tespit edilen güvenlik açığı). Önce Türkçe
# harf eşlemesi yapılır, sonra kalan birleşen işaretler temizlenir.
_TR_LOWER_MAP = str.maketrans({"İ": "i", "I": "ı"})


def normalize_tr(text: str) -> str:
    """Kriz/kapsam/araç tespiti için güvenli Türkçe normalizasyon."""
    import unicodedata

    lowered = (text or "").translate(_TR_LOWER_MAP).casefold()
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    # Aksanları atınca ı/i, ö/o, ü/u, ş/s, ç/c, ğ/g birleşir; anahtar kelimeler
    # de aynı normalizasyondan geçirilerek karşılaştırılır.
    return unicodedata.normalize("NFC", stripped)


_CRISIS_KEYWORDS_NORMALIZED = tuple(normalize_tr(k) for k in CRISIS_KEYWORDS)


def contains_crisis_signal(text: str) -> bool:
    t = normalize_tr(text)
    return any(k in t for k in _CRISIS_KEYWORDS_NORMALIZED)
```

**DEĞİŞTİ — eski `contains_crisis_signal` kaldırıldı** (yukarıdaki bloğa dahil):
```python
# ESKİ (kaldırıldı):
def contains_crisis_signal(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in CRISIS_KEYWORDS)
```

**DEĞİŞTİ — `contains_out_of_scope_signal`:**
```python
# YENİ:
_OUT_OF_SCOPE_NORMALIZED = tuple(normalize_tr(m) for m in OUT_OF_SCOPE_MARKERS)


def contains_out_of_scope_signal(text: str) -> bool:
    t = normalize_tr(text)
    if any(marker in t for marker in _OUT_OF_SCOPE_NORMALIZED):
        return True
    compact = t.replace(" ", "")
    return any(op in compact for op in ("1+1", "2+2", "3*3", "10/2"))

# ESKİ (kaldırıldı):
def contains_out_of_scope_signal(text: str) -> bool:
    t = (text or "").casefold()
    if any(marker in t for marker in OUT_OF_SCOPE_MARKERS):
        return True
    compact = t.replace(" ", "")
    return any(op in compact for op in ("1+1", "2+2", "3*3", "10/2"))
```

---

**Dosya:** `app/services/intent_service.py`

Aynı normalizasyon, tool-intent ve replan tespiti için de uygulandı (kullanıcı
"MAZERET" veya "PLAN OLUŞTUR" gibi büyük harfle yazarsa artık doğru yakalanıyor).

**DEĞİŞTİ — `_wants_replan`:**
```python
# YENİ:
def _wants_replan(message: str) -> bool:
    normalized = prompts.normalize_tr(message)
    return any(prompts.normalize_tr(marker) in normalized for marker in REPLAN_MARKERS)

# ESKİ:
def _wants_replan(message: str) -> bool:
    normalized = message.casefold()
    return any(marker in normalized for marker in REPLAN_MARKERS)
```

**DEĞİŞTİ — `handle_chat` içindeki tool-intent kontrolü:**
```python
# YENİ:
    tool_calls: list[ToolCall] = []
    normalized_message = prompts.normalize_tr(last_user_msg)
    if any(
        prompts.normalize_tr(marker) in normalized_message
        for marker in TOOL_INTENT_MARKERS
    ):

# ESKİ:
    tool_calls: list[ToolCall] = []
    normalized_message = last_user_msg.casefold()
    if any(marker in normalized_message for marker in TOOL_INTENT_MARKERS):
```

---

**Dosya:** `app/services/bonus_pool.py`

Bonus görev tamamlama mesajı ("YAPTIM" büyük harfle yazılırsa) artık doğru
eşleşiyor.

**DEĞİŞTİ — `is_completion_message`:**
```python
# YENİ:
_COMPLETION_PHRASES = (
    "yaptım", "tamamladım", "bonus görevi yaptım",
)


def is_completion_message(text: str) -> bool:
    from app.core.prompts import normalize_tr

    normalized = " ".join(normalize_tr(text).split())
    ascii_form = normalized.replace("ı", "i")
    accepted = set()
    for phrase in _COMPLETION_PHRASES:
        base = " ".join(normalize_tr(phrase).split())
        accepted.add(base)
        accepted.add(base.replace("ı", "i"))
    return normalized in accepted or ascii_form in accepted

# ESKİ:
def is_completion_message(text: str) -> bool:
    normalized = " ".join((text or "").casefold().split())
    return normalized in {
        "yaptım", "yaptim", "tamamladım", "tamamladim",
        "bonus görevi yaptım", "bonus gorevi yaptim",
    }
```

---

## Değişiklik 2 — Gemini timeout'ları artık gerçekten uygulanıyor

**Dosya:** `app/core/gemini_client.py`

**Sorun:** `config.py`'deki `GEMINI_TIMEOUT_SEC` (30 sn) ve `GEMINI_PLAN_TIMEOUT_SEC`
(90 sn) hiçbir yerde kullanılmıyordu; Gemini API isteği askıda kalırsa worker
süresiz beklerdi.

**Çözüm:** `asyncio.wait_for(...)` ile her Gemini çağrısı sarmalandı; `generate_text`
ve `generate_json` artık opsiyonel `timeout_sec` parametresi alıyor, verilmezse
`settings.GEMINI_TIMEOUT_SEC` kullanılıyor.

**DEĞİŞTİ — `generate_text` imzası ve gövdesi:**
```python
async def generate_text(
    contents: Any,
    system_instruction: Optional[str] = None,
    force_json: bool = False,
    *,
    model: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    max_retries: Optional[int] = None,
    response_schema: Optional[dict] = None,
    disable_thinking: bool = False,
    timeout_sec: Optional[float] = None,          # ← YENİ parametre
) -> str:
    """
    Dayanıklı çağrı: settings.GEMINI_MAX_RETRIES kez exponential backoff.
    contents: str | list (google-genai formatında parça listesi — vision dahil).
    timeout_sec: MASTER_PLAN §1.9 — chat 30 sn, plan 90 sn. Verilmezse
    GEMINI_TIMEOUT_SEC uygulanır; takılan istek worker'ı süresiz bloklayamaz.
    """
    from google.genai import types

    resolved_model = _resolve_model(model)
    retry_limit = settings.GEMINI_MAX_RETRIES if max_retries is None else max_retries
    resolved_timeout = timeout_sec or settings.GEMINI_TIMEOUT_SEC   # ← YENİ
    config_kwargs: dict[str, Any] = {
        "system_instruction": system_instruction,
        "response_mime_type": "application/json" if force_json else None,
    }
    if max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = max_output_tokens
    if force_json and response_schema is not None:
        config_kwargs["response_schema"] = response_schema
    if disable_thinking:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    config = types.GenerateContentConfig(**config_kwargs)

    client = get_client()

    last_err: Exception | None = None
    for attempt in range(retry_limit + 1):
        try:
            resp = await asyncio.wait_for(                          # ← YENİ sarmalayıcı
                asyncio.to_thread(
                    client.models.generate_content,
                    model=resolved_model,
                    contents=contents,
                    config=config,
                ),
                timeout=resolved_timeout,
            )
            return resp.text or ""
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt >= retry_limit:
                break
            wait = min(2 ** attempt, 4)
            log.warning(
                "Gemini hatası (%s, deneme %s): %s — %ss bekleniyor",
                resolved_model, attempt + 1, e, wait,
            )
            await asyncio.sleep(wait)

    raise GeminiUnavailable(str(last_err))
```

**DEĞİŞTİ — `generate_json` imzası (yeni `timeout_sec` parametresini `generate_text`'e iletir):**
```python
async def generate_json(
    contents: Any,
    system_instruction: Optional[str] = None,
    *,
    model: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    max_retries: Optional[int] = None,
    json_retries: int = 2,
    response_schema: Optional[dict] = None,
    disable_thinking: bool = False,
    timeout_sec: Optional[float] = None,        # ← YENİ parametre
) -> dict:
    """JSON zorla + güvenli parse. Bozuk JSON'da sınırlı tekrar."""
    last_raw = ""
    for _ in range(max(1, json_retries)):
        raw = await generate_text(
            contents,
            system_instruction=system_instruction,
            force_json=True,
            model=model,
            max_output_tokens=max_output_tokens,
            max_retries=max_retries,
            response_schema=response_schema,
            disable_thinking=disable_thinking,
            timeout_sec=timeout_sec,             # ← YENİ
        )
        last_raw = raw
        try:
            return json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            log.warning("Gemini bozuk JSON döndürdü, tekrar deneniyor: %.200s", raw)
    raise GeminiUnavailable(f"Model geçerli JSON üretemedi: {last_raw[:200]}")
```

**DEĞİŞTİ — `generate_function_calls` içindeki çağrı da timeout'lu:**
```python
    client = get_client()
    resolved_model = _resolve_model(model)
    last_err: Exception | None = None
    for attempt in range(settings.GEMINI_MAX_RETRIES + 1):
        try:
            response = await asyncio.wait_for(                       # ← YENİ sarmalayıcı
                asyncio.to_thread(
                    client.models.generate_content,
                    model=resolved_model,
                    contents=contents,
                    config=config,
                ),
                timeout=settings.GEMINI_TIMEOUT_SEC,
            )
```

---

**Dosya:** `app/services/plan_service.py`

Plan üretimi artık uzun timeout'u (90 sn) açıkça talep ediyor:

**DEĞİŞTİ:**
```python
    data = await generate_json(
        instructions,
        system_instruction=prompts.SYSTEM_PROMPT,
        model=settings.GEMINI_MODEL_PLAN,
        max_output_tokens=8192,
        timeout_sec=settings.GEMINI_PLAN_TIMEOUT_SEC,   # ← YENİ satır
    )
```

---

## Değişiklik 3 — Plan üretiminde görsel çekme paralelleştirildi (event loop kilidi giderildi)

**Sorun:** `plan_service.generate_batch`, her görev için **senkron** `httpx.get()`
kullanan `image_service.get_image()`'i sıralı olarak çağırıyordu. `async def`
fonksiyon içinde `await` edilmeyen senkron I/O, FastAPI'nin event loop'unu bloklar
— o an plan üreten kullanıcı yüzünden **sunucudaki diğer tüm isteklerin** işlenmesi
durur. 7 günlük ilk parti × 5 görev = en kötü senaryoda 35 sıralı Unsplash isteği.

**Çözüm:** İki parça halinde:
1. `image_service.py`'ye **async** bir arama fonksiyonu (`_search_async`) ve
   **async** bir `get_image_async()` eklendi (paylaşılan `httpx.AsyncClient`
   kullanıyor).
2. `plan_service.generate_batch`, önce görevleri görselsiz ayrıştırıyor, sonra
   **tüm görselleri `asyncio.gather()` ile paralel** çekiyor.

**Dosya:** `app/services/image_service.py`

**DEĞİŞTİ — `_search` yardımcı parçalara bölündü + async eşleniği eklendi:**
```python
def _search(query: str) -> list[dict]:
    if not settings.UNSPLASH_ACCESS_KEY:
        return []
    resp = httpx.get(
        _UNSPLASH_SEARCH,
        params=_search_params(query),
        headers=_search_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _search_params(query: str) -> dict:
    return {
        "query": query,
        "per_page": 10,
        "orientation": "landscape",
        "order_by": "relevant",
        "content_filter": "high",
    }


def _search_headers() -> dict:
    return {"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}


async def _search_async(client: httpx.AsyncClient, query: str) -> list[dict]:
    if not settings.UNSPLASH_ACCESS_KEY:
        return []
    resp = await client.get(
        _UNSPLASH_SEARCH,
        params=_search_params(query),
        headers=_search_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])
```

**DEĞİŞTİ — `get_image` ortak bir `_build_result` yardımcısına yeniden düzenlendi
+ `get_image_async` eklendi:**
```python
def _build_result(results: list[dict], used_query: str, source: str) -> ImageResult:
    result = _pick_result(results, used_query)
    base_url = result["urls"]["regular"]
    separator = "&" if "?" in base_url else "?"
    user = result.get("user") or {}
    links = result.get("links") or {}
    attribution_url = links.get("html", "")
    if attribution_url:
        joiner = "&" if "?" in attribution_url else "?"
        attribution_url = (
            f"{attribution_url}{joiner}utm_source=niyetsen&utm_medium=referral"
        )
    return ImageResult(
        url=f"{base_url}{separator}w=800&h=600&fit=crop&q=82",
        source=source,
        attribution=(
            f"Photo by {user.get('name')} on Unsplash"
            if user.get("name") else "Photo on Unsplash"
        ),
        attribution_url=attribution_url,
    )


def get_image(keyword: str, *, categories: list[str] | None = None) -> ImageResult:
    query = normalize_image_query(keyword)
    fallback_query = category_fallback_query(categories)
    try:
        results = _search(query) if query else []
        source = "unsplash"
        used_query = query
        if not results and fallback_query != query:
            results = _search(fallback_query)
            source = "category_fallback"
            used_query = fallback_query
        if results:
            return _build_result(results, used_query, source)
    except Exception as e:  # noqa: BLE001
        log.warning("Unsplash hatası (%s): %s — yer tutucuya düşülüyor", query, e)

    return ImageResult(
        url=_placeholder(query or fallback_query),
        source="placeholder",
    )


async def get_image_async(                              # ← YENİ FONKSİYON
    client: httpx.AsyncClient,
    keyword: str,
    *,
    categories: list[str] | None = None,
) -> ImageResult:
    """Async sürüm: plan üretimi görselleri PARALEL çeker (event loop'u
    bloklamaz; 7 gün × 5 görev = 35 sıralı istek yerine eşzamanlı)."""
    query = normalize_image_query(keyword)
    fallback_query = category_fallback_query(categories)
    try:
        results = await _search_async(client, query) if query else []
        source = "unsplash"
        used_query = query
        if not results and fallback_query != query:
            results = await _search_async(client, fallback_query)
            source = "category_fallback"
            used_query = fallback_query
        if results:
            return _build_result(results, used_query, source)
    except Exception as e:  # noqa: BLE001
        log.warning("Unsplash hatası (%s): %s — yer tutucuya düşülüyor", query, e)

    return ImageResult(
        url=_placeholder(query or fallback_query),
        source="placeholder",
    )
```

---

**Dosya:** `app/services/plan_service.py`

**DEĞİŞTİ — import satırları:**
```python
from __future__ import annotations

import asyncio                                                    # ← YENİ
import logging
import uuid
from datetime import date, timedelta

import httpx                                                       # ← YENİ

from app.config import CATEGORIES, settings
from app.core import prompts
from app.core.gemini_client import generate_json
from app.models.schemas import CollectedIntent, Plan, PlanDay, Task
from app.services.image_service import category_fallback_query, get_image, get_image_async  # ← get_image_async eklendi
```

**DEĞİŞTİ — `generate_batch` gövdesi, görsel çekme mantığı iki aşamaya bölündü:**
```python
    data = await generate_json(
        instructions,
        system_instruction=prompts.SYSTEM_PROMPT,
        model=settings.GEMINI_MODEL_PLAN,
        max_output_tokens=8192,
        timeout_sec=settings.GEMINI_PLAN_TIMEOUT_SEC,
    )

    # 1) Önce görevleri ayrıştır (görselsiz), 2) tüm görselleri TEK seferde
    # paralel çek. Eski sıralı+senkron akış hem event loop'u kilitliyordu hem de
    # plan üretimini görsel sayısı × Unsplash gecikmesi kadar yavaşlatıyordu.
    parsed: list[tuple[int, str, list[dict]]] = []  # (day_no, theme, raw_tasks)
    for d in (data.get("days") or [])[:batch]:
        day_no = start_day + len(parsed)
        raw_tasks = []
        for t in (d.get("tasks") or [])[: settings.MAX_TASKS_PER_DAY]:
            title = str(t.get("title") or "").strip()
            if not title:
                continue
            categories = _sanitize_categories(t.get("categories"))
            keyword = str(t.get("image_keyword") or "").strip()
            if not keyword:
                keyword = category_fallback_query(categories)
            raw_tasks.append({**t, "title": title, "categories": categories,
                              "image_keyword": keyword})
        parsed.append((day_no, str(d.get("theme") or ""), raw_tasks))

    flat = [
        (day_no, t) for day_no, _theme, raw_tasks in parsed for t in raw_tasks
    ]
    async with httpx.AsyncClient() as client:
        images = await asyncio.gather(*(
            get_image_async(client, t["image_keyword"], categories=t["categories"])
            for _day_no, t in flat
        ))
    image_by_index = dict(zip(range(len(flat)), images))

    days: list[PlanDay] = []
    index = 0
    for day_no, theme, raw_tasks in parsed:
        tasks: list[Task] = []
        for t in raw_tasks:
            image = image_by_index[index]
            index += 1
            tasks.append(
                Task(
                    id=uuid.uuid4().hex[:12],
                    day=day_no,
                    date=start_date + timedelta(days=day_no - 1),
                    title=t["title"],
                    task_type=t.get("task_type") if t.get("task_type") in
                        ("yer", "alışkanlık", "sosyal", "kişisel_gelişim") else "alışkanlık",
                    categories=t["categories"],
                    image_keyword=t["image_keyword"],
                    image_url=image.url,
                    image_source=image.source,
                    image_attribution=image.attribution,
                    image_attribution_url=image.attribution_url,
                    duration_min=int(t.get("duration_min") or 15),
                    tiny_version=str(t.get("tiny_version") or "2 dakikanı ayır ve sadece başla."),
                )
            )
        if tasks:
            days.append(PlanDay(day=day_no, theme=theme, tasks=tasks))
```

**Not:** `get_image` (senkron versiyon) hâlâ dosyada duruyor — geriye dönük
uyumluluk için kasıtlı olarak silinmedi (başka bir yerden çağrılıyor olabilir,
grep ettim şu an çağıran yok ama silmek yerine bırakmak daha güvenli).

---

## Test doğrulaması

```
104 passed, 1 warning in 1.87s
```

Değişiklik öncesi de 104/104 idi — yani üç değişiklik de mevcut davranışı
bozmadı, sadece daha önce test edilmeyen senaryoları (büyük harfli Türkçe kriz
mesajı, timeout, event-loop bloklaması) düzeltti. Bu senaryolar için **yeni
testler henüz eklenmedi** — istersen bir sonraki turda
`test_chat_guardrails.py`'ye büyük harfli kriz mesajı testi eklenebilir.

---

## Sırada ne var

`NIYETSEN_BULGULAR_VE_HATALAR.md` dosyasındaki §4-11 arası maddeler henüz
uygulanmadı. Öncelik sırası öneriyorum:

1. **§6** — `/plan/generate` rate limit + rıza eksikliği (kolay, hızlı, maliyet riski kapatır)
2. **§4** — RevenueCat webhook sır zorunluluğu (kolay, güvenlik açığı kapatır)
3. **§8** — Çoklu plan kullanıcılarında gün kapanışının tüm planları işlemesi (orta, ücretli özelliğin doğru çalışması için kritik)
4. **§5** — İptal sonrası dönem sonuna kadar erişim (orta, kullanıcı deneyimi + mağaza politikası)
5. **§7** — Bugünün görevleri timezone düzeltmesi (kolay)
6. **§9, §11** — performans/UX iyileştirmeleri (düşük öncelik, MVP'yi bloklamaz)

Devam etmemi istersen söyle, aynı yöntemle (oku → düzelt → test et → dokümante et)
ilerlerim.
