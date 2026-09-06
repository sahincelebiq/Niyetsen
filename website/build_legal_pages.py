#!/usr/bin/env python3
"""Generate localized legal HTML (Play/App Store public URLs). Run from website/."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

LANGS = {
    "tr": {"label": "TR", "privacy": "gizlilik.html", "terms": "kullanim-kosullari.html", "deletion": "hesap-silme.html"},
    "en": {"label": "EN", "privacy": "privacy.html", "terms": "terms.html", "deletion": "account-deletion.html"},
    "de": {"label": "DE", "privacy": "datenschutz.html", "terms": "nutzungsbedingungen.html", "deletion": "konto-loeschen.html"},
    "fr": {"label": "FR", "privacy": "confidentialite.html", "terms": "conditions.html", "deletion": "suppression-compte.html"},
    "ar": {"label": "AR", "privacy": "privacy-ar.html", "terms": "terms-ar.html", "deletion": "account-deletion-ar.html"},
}

NAV_TR = [
    ("/", "Ana Sayfa"),
    ("/blog/", "Blog"),
    ("/gelistirme.html", "Geliştirme"),
]
NAV = {
    "tr": NAV_TR + [("mailto:ai@niyetsen.com", "İletişim")],
    "en": [("/", "Home"), ("/blog/", "Blog"), ("mailto:ai@niyetsen.com", "Contact")],
    "de": [("/", "Start"), ("/blog/", "Blog"), ("mailto:ai@niyetsen.com", "Kontakt")],
    "fr": [("/", "Accueil"), ("/blog/", "Blog"), ("mailto:ai@niyetsen.com", "Contact")],
    "ar": [("/", "الرئيسية"), ("/blog/", "المدونة"), ("mailto:ai@niyetsen.com", "تواصل")],
}

COPY = {
    "en": {
        "privacy_title": "Privacy Policy — Niyetsen",
        "privacy_desc": "How Niyetsen collects, uses, shares and deletes personal data. For Google Play, the App Store, KVKK, GDPR and CCPA.",
        "terms_title": "Terms of Use — Niyetsen",
        "terms_desc": "Account, AI, subscriptions (App Store / Google Play) and acceptable use.",
        "del_title": "Account and data deletion — Niyetsen",
        "del_desc": "How to delete your Niyetsen account. Required Google Play account-deletion page.",
        "h1_privacy": "Privacy Policy",
        "h1_terms": "Terms of Use",
        "h1_del": "Account and data deletion",
        "effective": "Effective date and last update: 6 September 2026",
        "nav_privacy": "Privacy",
        "nav_terms": "Terms",
        "nav_del": "Delete account",
        "footer": "© 2026 Niyetsen",
    },
    "de": {
        "privacy_title": "Datenschutzerklärung — Niyetsen",
        "privacy_desc": "Welche Daten Niyetsen verarbeitet. Für Google Play, App Store, KVKK, DSGVO und CCPA.",
        "terms_title": "Nutzungsbedingungen — Niyetsen",
        "terms_desc": "Konto, KI, Abos (App Store / Google Play) und zulässige Nutzung.",
        "del_title": "Konto- und Datenlöschung — Niyetsen",
        "del_desc": "So löschen Sie Ihr Niyetsen-Konto. Google-Play-Löschseite.",
        "h1_privacy": "Datenschutzerklärung",
        "h1_terms": "Nutzungsbedingungen",
        "h1_del": "Konto- und Datenlöschung",
        "effective": "Gültig ab und zuletzt geändert: 6. September 2026",
        "nav_privacy": "Datenschutz",
        "nav_terms": "Bedingungen",
        "nav_del": "Konto löschen",
        "footer": "© 2026 Niyetsen",
    },
    "fr": {
        "privacy_title": "Politique de confidentialité — Niyetsen",
        "privacy_desc": "Données collectées par Niyetsen. Play Store, App Store, KVKK, RGPD et CCPA.",
        "terms_title": "Conditions d’utilisation — Niyetsen",
        "terms_desc": "Compte, IA, abonnements (App Store / Google Play) et usage acceptable.",
        "del_title": "Suppression du compte et des données — Niyetsen",
        "del_desc": "Comment supprimer votre compte Niyetsen. Page exigée par Google Play.",
        "h1_privacy": "Politique de confidentialité",
        "h1_terms": "Conditions d’utilisation",
        "h1_del": "Suppression du compte et des données",
        "effective": "Date d’entrée en vigueur et dernière mise à jour : 6 septembre 2026",
        "nav_privacy": "Confidentialité",
        "nav_terms": "Conditions",
        "nav_del": "Supprimer le compte",
        "footer": "© 2026 Niyetsen",
    },
    "ar": {
        "privacy_title": "سياسة الخصوصية — نيتسن",
        "privacy_desc": "كيف تجمع نيتسن البيانات. لمتجر Play وApp Store وقانون حماية البيانات التركي واللائحة الأوروبية.",
        "terms_title": "شروط الاستخدام — نيتسن",
        "terms_desc": "الحساب والذكاء والاشتراكات (App Store / Google Play).",
        "del_title": "حذف الحساب والبيانات — نيتسن",
        "del_desc": "كيف تحذف حساب نيتسن. صفحة حذف حساب Google Play.",
        "h1_privacy": "سياسة الخصوصية",
        "h1_terms": "شروط الاستخدام",
        "h1_del": "حذف الحساب والبيانات",
        "effective": "تاريخ السريان وآخر تحديث: 6 سبتمبر 2026",
        "nav_privacy": "الخصوصية",
        "nav_terms": "الشروط",
        "nav_del": "حذف الحساب",
        "footer": "© 2026 نيتسن",
    },
}


def langs_bar(current: str, kind: str) -> str:
    parts = []
    for code, meta in LANGS.items():
        href = meta[kind]
        cur = ' aria-current="page"' if code == current else ""
        parts.append(f'<a href="/{href}" hreflang="{code}"{cur}>{meta["label"]}</a>')
    return '<nav class="legal-langs" aria-label="Language">' + " · ".join(parts) + "</nav>"


def hreflang(kind: str) -> str:
    tags = []
    for code, meta in LANGS.items():
        tags.append(f'  <link rel="alternate" hreflang="{code}" href="https://niyetsen.com/{meta[kind]}">')
    tags.append(f'  <link rel="alternate" hreflang="x-default" href="https://niyetsen.com/{LANGS["en"][kind]}">')
    return "\n".join(tags)


def shell(
    lang: str,
    title: str,
    desc: str,
    canonical: str,
    og_locale: str,
    body: str,
    kind: str,
    dir_attr: str = "",
) -> str:
    nav = "".join(
        f'<a href="{href}">{label}</a>' for href, label in NAV[lang]
    )
    html_lang = "ar" if lang == "ar" else lang
    return f"""<!DOCTYPE html>
<html lang="{html_lang}"{dir_attr}>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index, follow">
  <meta name="theme-color" content="#d89b7c">
  <link rel="canonical" href="https://niyetsen.com/{canonical}">
{hreflang(kind)}
  <link rel="icon" href="https://niyetsen.com/favicon-48x48.png?v=20260726-7" type="image/png" sizes="48x48">
  <link rel="stylesheet" href="/css/fonts.css?v=20260906">
  <link rel="stylesheet" href="/css/style.css?v=20260906">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="https://niyetsen.com/{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="{og_locale}">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"{title}","description":"{desc}","url":"https://niyetsen.com/{canonical}","inLanguage":"{html_lang}","isPartOf":{{"@type":"WebSite","name":"Niyetsen","url":"https://niyetsen.com/"}}}}
  </script>
  <script src="/js/site-config.js?v=20260726-7" defer></script>
  <script src="/js/marketing.js?v=20260726-7" defer></script>
</head>
<body>
  <header>
    <nav class="nav" aria-label="Menu">
      <a class="logo" href="/" aria-label="Niyetsen"><img class="logo-mark" src="https://niyetsen.com/images/logo-mark.png?v=20260726-7" srcset="https://niyetsen.com/images/logo-mark.png?v=20260726-7 1x, https://niyetsen.com/images/logo-mark-2x.png?v=20260726-7 2x" width="40" height="40" alt="Niyetsen" loading="eager">Niyetsen</a>
      <div class="nav-links">{nav}</div>
    </nav>
  </header>
  <main>
    {body}
  </main>
  <footer>
    <div class="footer-inner">
      <span>{COPY[lang]["footer"]}</span>
      <div class="footer-links">
        <a href="/{LANGS[lang]["privacy"]}">{COPY[lang]["nav_privacy"]}</a>
        <a href="/{LANGS[lang]["terms"]}">{COPY[lang]["nav_terms"]}</a>
        <a href="/{LANGS[lang]["deletion"]}">{COPY[lang]["nav_del"]}</a>
        <a href="mailto:ai@niyetsen.com">ai@niyetsen.com</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""


PRIVACY = {
    "en": """
      <p class="disclaimer">This policy covers niyetsen.com and the Niyetsen iOS/Android apps (com.niyetsenai / com.niyetsen.app). Controller: Şahin Çelebi. Requests: <a href="mailto:ai@niyetsen.com">ai@niyetsen.com</a>. Written for Google Play, the App Store, KVKK, GDPR/UK GDPR and CCPA.</p>
      <h2>1. Data we process</h2>
      <ul>
        <li>Account: name, email, Apple/Google ids, Supabase user id.</li>
        <li>Profile: date of birth, zodiac, timezone, language, optional gender for address only.</li>
        <li>Content: chat, plans, tasks, mystic guide.</li>
        <li>Proof/fortune photos: in-app camera only. No gallery. No biometrics.</li>
        <li>Gameplay, optional nickname league (alias only), subscription status (no card numbers).</li>
        <li>Technical logs. Website early-access form only if you submit it.</li>
      </ul>
      <p>We do not collect location, do not use an advertising id, do not sell data, and do not share it for cross-context ads.</p>
      <h2>2. Purposes and legal bases</h2>
      <ul>
        <li>Account, tasks, points: contract (KVKK 5/2-c; GDPR 6/1-b).</li>
        <li>AI chat, plans, fortune, proof photos: consent (KVKK 5/1 / 6; GDPR 6/1-a / 9).</li>
        <li>Security and debugging: legitimate interests (GDPR 6/1-f).</li>
        <li>Store billing records: legal obligation (GDPR 6/1-c).</li>
      </ul>
      <h2>3. Recipients</h2>
      <p>Google Gemini (replies; we do not train our own model on your data), Supabase, Railway, Apple / Google Play / RevenueCat (they control payments), Unsplash (images only), PostHog/Sentry if configured, authorities if required. Transfers may leave the EEA under GDPR Arts. 44–49.</p>
      <h2>4. Retention</h2>
      <ul>
        <li>Account: membership + up to 3 years after deletion request.</li>
        <li>Chat, plans, fortune: + up to 1 year after deletion.</li>
        <li>Proof photos: up to 1 year or until account deletion.</li>
        <li>Points / league alias: + up to 2 years.</li>
        <li>Invoices: as tax law requires (often up to 10 years, usually at the store).</li>
        <li>Security logs: up to 6 months.</li>
      </ul>
      <h2>5. Your rights</h2>
      <p>KVKK Art. 11; GDPR / UK GDPR Arts. 15–21; CCPA know/delete/correct. Email <a href="mailto:ai@niyetsen.com">ai@niyetsen.com</a> (subject “Privacy Request”). Reply within 30 days. Complaints: KVKK Board, CNIL, BfDI, ICO as applicable. We do not sell California personal information.</p>
      <h2>6. Fortune and children</h2>
      <p>Tarot, coffee, palm and horoscope are entertainment — not medical, legal or financial advice. The service is 18+ only. Under-18 data is deleted if discovered.</p>
      <h2>7. Account deletion</h2>
      <p>In-app: Profile → Delete my account. Or <a href="/account-deletion.html">account-deletion.html</a>.</p>
    """,
    "de": """
      <p class="disclaimer">Gilt für niyetsen.com und die Apps (com.niyetsenai / com.niyetsen.app). Verantwortlicher: Şahin Çelebi. <a href="mailto:ai@niyetsen.com">ai@niyetsen.com</a>.</p>
      <h2>1. Daten</h2>
      <ul>
        <li>Konto, Profil (Geburtsdatum, Sprache, optionales Geschlecht nur Anrede), Chat, Pläne, Nachweisfotos nur In-App-Kamera, Spielstand, optionale Liga (nur Alias), Abo-Status ohne Kartennummer, Techniklogs.</li>
      </ul>
      <p>Kein Standort, keine Werbe-ID, kein Verkauf, kein Sharing für Cross-Context-Werbung.</p>
      <h2>2. Zwecke und Rechtsgrundlagen</h2>
      <ul>
        <li>Vertrag, Einwilligung (KI/Fotos), berechtigte Interessen (Sicherheit), rechtliche Pflicht (Store-Buchhaltung) — KVKK und DSGVO Art. 6/9.</li>
      </ul>
      <h2>3. Empfänger</h2>
      <p>Google Gemini, Supabase, Railway, Apple/Google Play/RevenueCat, Unsplash (nur Bilder), ggf. PostHog/Sentry. Drittlandtransfer nach DSGVO Art. 44–49.</p>
      <h2>4. Speicherung</h2>
      <p>Konto bis 3 Jahre nach Löschantrag; Chat/Fotos in der Regel 1 Jahr; Rechnungen gesetzliche Frist; Sicherheitslogs 6 Monate.</p>
      <h2>5. Rechte</h2>
      <p>KVKK, DSGVO Art. 15–21, CCPA. E-Mail ai@niyetsen.com. Beschwerde u. a. bei BfDI/Landesbeauftragten, CNIL, ICO. Antwort binnen 30 Tagen.</p>
      <h2>6. Wahrsagen und Alter</h2>
      <p>Unterhaltung, keine Beratung. Nur 18+.</p>
      <h2>7. Löschung</h2>
      <p>Profil → Konto löschen oder <a href="/konto-loeschen.html">konto-loeschen.html</a>.</p>
    """,
    "fr": """
      <p class="disclaimer">Couvre niyetsen.com et les apps (com.niyetsenai / com.niyetsen.app). Responsable : Şahin Çelebi. <a href="mailto:ai@niyetsen.com">ai@niyetsen.com</a>.</p>
      <h2>1. Données</h2>
      <ul>
        <li>Compte, profil, chat, plans, photos de preuve (caméra in-app), jeu, ligue optionnelle (surnom), statut d’abonnement sans carte, journaux techniques.</li>
      </ul>
      <p>Pas de localisation, pas d’identifiant pub, pas de vente ni de share publicitaire.</p>
      <h2>2. Bases légales</h2>
      <p>Contrat, consentement (IA/photos), intérêts légitimes (sécurité), obligation légale (boutique) — KVKK et RGPD art. 6/9.</p>
      <h2>3. Destinataires</h2>
      <p>Google Gemini, Supabase, Railway, Apple/Google Play/RevenueCat, Unsplash (images). Transferts RGPD art. 44–49.</p>
      <h2>4. Durées</h2>
      <p>Compte jusqu’à 3 ans après demande ; chat/photos en général 1 an ; factures selon la loi ; sécurité 6 mois.</p>
      <h2>5. Droits</h2>
      <p>KVKK, RGPD art. 15–21, CCPA. E-mail ai@niyetsen.com. Réclamation CNIL / ICO / KVKK. Réponse sous 30 jours.</p>
      <h2>6. Voyance et âge</h2>
      <p>Divertissement uniquement. 18+ seulement.</p>
      <h2>7. Suppression</h2>
      <p>Profil → Supprimer mon compte ou <a href="/suppression-compte.html">suppression-compte.html</a>.</p>
    """,
    "ar": """
      <p class="disclaimer">تسري على niyetsen.com والتطبيق (com.niyetsenai / com.niyetsen.app). المسؤول: شاهين جلبي. <a href="mailto:ai@niyetsen.com">ai@niyetsen.com</a>.</p>
      <h2>1. البيانات</h2>
      <ul>
        <li>الحساب والملف والدردشة والخطط وصور الإثبات (كاميرا التطبيق فقط) واللعب والدوري الاختياري (اسم مستعار) وحالة الاشتراك دون رقم بطاقة والسجلات التقنية.</li>
      </ul>
      <p>لا موقع ولا معرّف إعلاني ولا بيع للبيانات.</p>
      <h2>2. الأسس القانونية</h2>
      <p>العقد والموافقة (الذكاء/الصور) والمصلحة المشروعة (الأمن) والالتزام القانوني (المتجر).</p>
      <h2>3. المستلمون</h2>
      <p>Google Gemini وSupabase وRailway وApple/Google Play/RevenueCat وUnsplash (صور فقط).</p>
      <h2>4. المدد</h2>
      <p>الحساب حتى 3 سنوات بعد طلب الحذف؛ الدردشة/الصور عادة سنة؛ الفواتير حسب القانون؛ الأمن 6 أشهر.</p>
      <h2>5. الحقوق</h2>
      <p>القانون التركي واللائحة الأوروبية وCCPA. راسل ai@niyetsen.com. الرد خلال 30 يومًا.</p>
      <h2>6. الفأل والعمر</h2>
      <p>للترفيه فقط. الخدمة 18+.</p>
      <h2>7. الحذف</h2>
      <p>الملف → حذف حسابي أو <a href="/account-deletion-ar.html">account-deletion-ar.html</a>.</p>
    """,
}

TERMS = {
    "en": """
      <p class="disclaimer">Using the service means you accept these terms and the <a href="/privacy.html">Privacy Policy</a>.</p>
      <h2>1. Service and age</h2>
      <p>Niyetsen turns an intention into a daily plan. No result guarantee. Not medical, legal or financial advice. You must be 18 or older.</p>
      <h2>2. Acceptable use</h2>
      <ul>
        <li>In-app camera only for proof. Do not upload another person’s data without permission. No cheating, harassment or illegal content.</li>
      </ul>
      <h2>3. AI and fortune</h2>
      <p>AI replies can be wrong. Fortune/horoscope is entertainment. Not therapy or emergency care — contact local emergency services if there is a risk of harm.</p>
      <h2>4. Subscriptions (Apple Guideline 3.1.2 / Google Play)</h2>
      <ul>
        <li>Chat stays free. A second plan, proof, bonuses, Idol paths and some mystic rights need a subscription or trial.</li>
        <li>Payment only via App Store / Google Play IAP and RevenueCat. No external payment link.</li>
        <li>Price and length are whatever the store shows. The app never invents a price.</li>
        <li>Apple: charged to your Apple ID at confirmation. Auto-renews unless cancelled at least 24 hours before the period ends. Renewal charged within 24 hours prior to the end. Manage: Settings → Apple ID → Subscriptions.</li>
        <li>Google Play: recurring billing on your Play account. Manage: Play → Payments &amp; subscriptions.</li>
        <li>Restore purchases reloads the same store account. Unused trial time may be forfeited on purchase. Refunds follow the store.</li>
      </ul>
      <h2>5. Liability and law</h2>
      <p>Service “as is” except mandatory law. Türkiye law applies; EU consumers keep mandatory home-country protections. Contact: ai@niyetsen.com.</p>
    """,
    "de": """
      <p class="disclaimer">Nutzung bedeutet Zustimmung zu diesen Bedingungen und der <a href="/datenschutz.html">Datenschutzerklärung</a>.</p>
      <h2>1. Dienst und Alter</h2>
      <p>Kein Erfolgsversprechen. Keine Beratung. Nur 18+.</p>
      <h2>2. Nutzung</h2>
      <p>Nur In-App-Kamera für Nachweise. Kein fremdes Material ohne Erlaubnis. Kein Missbrauch.</p>
      <h2>3. KI und Wahrsagen</h2>
      <p>KI kann irren. Wahrsagen ist Unterhaltung. Keine Notfallhilfe.</p>
      <h2>4. Abos (Apple 3.1.2 / Google Play)</h2>
      <ul>
        <li>Zahlung nur über den Store / RevenueCat. Preis wie im Store angezeigt.</li>
        <li>Apple: Belastung der Apple-ID; automatische Verlängerung, wenn nicht 24 Stunden vorher aus; Verwaltung unter Abonnements.</li>
        <li>Google Play: wiederkehrende Zahlung; Verwaltung unter Zahlungen und Abos.</li>
        <li>Käufe wiederherstellen. Erstattungen nach Store-Politik.</li>
      </ul>
      <h2>5. Haftung und Recht</h2>
      <p>Recht der Türkei; zwingender EU-Verbraucherschutz bleibt. ai@niyetsen.com.</p>
    """,
    "fr": """
      <p class="disclaimer">L’usage vaut acceptation de ces conditions et de la <a href="/confidentialite.html">politique de confidentialité</a>.</p>
      <h2>1. Service et âge</h2>
      <p>Pas de garantie de résultat. Pas un conseil. 18+ seulement.</p>
      <h2>2. Usage</h2>
      <p>Caméra in-app pour la preuve. Pas de données d’autrui sans permission.</p>
      <h2>3. IA et voyance</h2>
      <p>L’IA peut se tromper. Voyance = divertissement. Pas une urgence médicale.</p>
      <h2>4. Abonnements (Apple 3.1.2 / Google Play)</h2>
      <ul>
        <li>Paiement uniquement via la boutique / RevenueCat. Prix affiché par la boutique.</li>
        <li>Apple : débit Apple ID ; renouvellement auto sauf annulation 24 h avant ; Réglages → Abonnements.</li>
        <li>Google Play : facturation récurrente ; Paiements et abonnements.</li>
        <li>Restaurer les achats. Remboursements selon la boutique.</li>
      </ul>
      <h2>5. Responsabilité</h2>
      <p>Droit de Türkiye ; protections impératives UE réservées. ai@niyetsen.com.</p>
    """,
    "ar": """
      <p class="disclaimer">استخدام الخدمة يعني قبول هذه الشروط و<a href="/privacy-ar.html">سياسة الخصوصية</a>.</p>
      <h2>1. الخدمة والعمر</h2>
      <p>لا ضمان نتيجة. ليست مشورة. 18+ فقط.</p>
      <h2>2. الاستخدام</h2>
      <p>كاميرا التطبيق للإثبات. لا بيانات الغير دون إذن.</p>
      <h2>3. الذكاء والفأل</h2>
      <p>قد يخطئ الذكاء. الفأل ترفيه. ليست طوارئ.</p>
      <h2>4. الاشتراك (Apple 3.1.2 / Google Play)</h2>
      <ul>
        <li>الدفع عبر المتجر وRevenueCat فقط. السعر كما يظهر في المتجر.</li>
        <li>Apple: خصم من Apple ID؛ تجديد تلقائي ما لم يُلغَ قبل 24 ساعة؛ الإدارة من الاشتراكات.</li>
        <li>Google Play: فوترة متكررة من المدفوعات والاشتراكات.</li>
        <li>استعادة المشتريات. الاسترداد وفق المتجر.</li>
      </ul>
      <h2>5. المسؤولية</h2>
      <p>قانون تركيا مع حماية المستهلك الأوروبية الإلزامية. ai@niyetsen.com.</p>
    """,
}

DELETION = {
    "en": """
      <p class="disclaimer">Google Play and App Store account-deletion page. Privacy: <a href="/privacy.html">Privacy Policy</a>.</p>
      <h2>1. In the app (recommended)</h2>
      <ol>
        <li>Open Niyetsen and sign in.</li>
        <li>Go to <strong>Profile</strong>.</li>
        <li>Tap <strong>Delete my account</strong> and confirm.</li>
      </ol>
      <h2>2. By email</h2>
      <p>Write to <a href="mailto:ai@niyetsen.com?subject=Account%20deletion">ai@niyetsen.com</a> with subject <strong>Account deletion</strong> and your registered email. We complete verified requests within <strong>30 days</strong>.</p>
      <h2>3. What is deleted</h2>
      <ul>
        <li>Account, profile, chat, plans, proof photos, points, streak, consents, fortune logs, league alias.</li>
      </ul>
      <h2>4. What may remain</h2>
      <ul>
        <li>Store invoices as tax law requires (often up to 10 years; cancel subscriptions in Apple/Google settings).</li>
        <li>Security logs up to 6 months.</li>
      </ul>
    """,
    "de": """
      <p class="disclaimer">Löschseite für Google Play / App Store. <a href="/datenschutz.html">Datenschutz</a>.</p>
      <h2>1. In der App</h2>
      <ol><li>Anmelden → <strong>Profil</strong> → <strong>Konto löschen</strong>.</li></ol>
      <h2>2. Per E-Mail</h2>
      <p><a href="mailto:ai@niyetsen.com?subject=Konto%20loeschen">ai@niyetsen.com</a>, Betreff <strong>Konto löschen</strong>. Innerhalb von <strong>30 Tagen</strong>.</p>
      <h2>3. Was gelöscht wird</h2>
      <p>Konto, Chat, Pläne, Fotos, Punkte, Kette, Einwilligungen, Wahrsagelog, Liga-Alias.</p>
      <h2>4. Was bleiben kann</h2>
      <p>Store-Rechnungen nach Steuerrecht; Sicherheitslogs bis 6 Monate. Abo im Store kündigen.</p>
    """,
    "fr": """
      <p class="disclaimer">Page de suppression Play / App Store. <a href="/confidentialite.html">Confidentialité</a>.</p>
      <h2>1. Dans l’app</h2>
      <ol><li>Connexion → <strong>Profil</strong> → <strong>Supprimer mon compte</strong>.</li></ol>
      <h2>2. Par e-mail</h2>
      <p><a href="mailto:ai@niyetsen.com?subject=Suppression%20compte">ai@niyetsen.com</a>, objet <strong>Suppression de compte</strong>. Sous <strong>30 jours</strong>.</p>
      <h2>3. Données effacées</h2>
      <p>Compte, chat, plans, photos, points, chaîne, consentements, voyance, surnom de ligue.</p>
      <h2>4. Ce qui peut rester</h2>
      <p>Factures boutique selon la loi ; journaux de sécurité 6 mois. Annulez l’abonnement dans la boutique.</p>
    """,
    "ar": """
      <p class="disclaimer">صفحة حذف الحساب لمتجر Play وApp Store. <a href="/privacy-ar.html">الخصوصية</a>.</p>
      <h2>1. من التطبيق</h2>
      <ol><li>دخول → <strong>الملف</strong> → <strong>حذف حسابي</strong>.</li></ol>
      <h2>2. بالبريد</h2>
      <p><a href="mailto:ai@niyetsen.com?subject=Account%20deletion">ai@niyetsen.com</a> بعنوان <strong>حذف الحساب</strong>. خلال <strong>30 يومًا</strong>.</p>
      <h2>3. ما يُحذف</h2>
      <p>الحساب والدردشة والخطط والصور والنقاط والسلسلة والموافقات والفأل واسم الدوري.</p>
      <h2>4. ما قد يبقى</h2>
      <p>فواتير المتجر حسب القانون؛ سجلات الأمن حتى 6 أشهر. ألغِ الاشتراك من المتجر.</p>
    """,
}

OG = {"en": "en_US", "de": "de_DE", "fr": "fr_FR", "ar": "ar_AR"}


def article(lang: str, kind: str, h1: str, inner: str) -> str:
    c = COPY[lang]
    rtl = ' dir="rtl"' if lang == "ar" else ""
    return f"""    <article class="legal"{rtl}>
      {langs_bar(lang, kind)}
      <h1>{h1}</h1>
      <p>{c["effective"]}</p>
      {inner}
    </article>"""


def main() -> None:
    for lang in ("en", "de", "fr", "ar"):
        c = COPY[lang]
        files = [
            (LANGS[lang]["privacy"], c["privacy_title"], c["privacy_desc"], "privacy", c["h1_privacy"], PRIVACY[lang]),
            (LANGS[lang]["terms"], c["terms_title"], c["terms_desc"], "terms", c["h1_terms"], TERMS[lang]),
            (LANGS[lang]["deletion"], c["del_title"], c["del_desc"], "deletion", c["h1_del"], DELETION[lang]),
        ]
        for name, title, desc, kind, h1, inner in files:
            dir_attr = ' dir="rtl"' if lang == "ar" else ""
            html = shell(lang, title, desc, name, OG[lang], article(lang, kind, h1, inner), kind, dir_attr)
            (ROOT / name).write_text(html, encoding="utf-8")
            print("wrote", name)


if __name__ == "__main__":
    main()
