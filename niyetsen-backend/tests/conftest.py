"""
Niyetsen — test ortamı kilidi.
.env'de USE_SUPABASE_DB=true olsa bile testler HER ZAMAN InMemoryRepository
kullanmalı: izolasyon, hız ve gerçek Supabase projesini kirletmemek için.
Bu satır app.* modülleri import edilmeden ÖNCE çalışmalı (python-dotenv'in
load_dotenv() zaten set edilmiş bir env değişkenini override ETMEZ, bu yüzden
conftest.py'nin en tepesinde olması yeterli — pytest bunu her test dosyasından
önce import eder).
"""
import os

os.environ["USE_SUPABASE_DB"] = "false"
