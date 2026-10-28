"""Setelan Django bengkel_project; nilai server dibaca dari environment variable."""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# --- Konfigurasi dibaca dari environment variable (aman untuk hosting) ---
# Lokal: tidak perlu mengatur apa-apa, nilai bawaan di bawah cukup untuk development.
# Server : set DJANGO_SECRET_KEY, DJANGO_DEBUG=0, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS
import os


def _env_list(nama, bawaan=""):
    return [x.strip() for x in os.environ.get(nama, bawaan).split(",") if x.strip()]


# SECURITY WARNING: keep the secret key used in production secret!
_SECRET_KEY_REPO = "django-insecure-25x!%n&aappc08p%8g+_a(16h0k+h&_#)&r@c&)6pmu&s1a6!x"  # hanya untuk development
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _SECRET_KEY_REPO)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

# contoh di server: DJANGO_ALLOWED_HOSTS=bengkel.pbo.web.id
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# contoh di server: DJANGO_CSRF_TRUSTED_ORIGINS=https://bengkel.pbo.web.id
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS")


def _host_lokal(host):
    """localhost, 127.0.0.1, atau IP jaringan rumah/kampus (192.168.x.x dsb.)."""
    import ipaddress

    if host in ("localhost", "testserver"):
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False  # nama domain, atau "*"
    return ip.is_loopback or ip.is_private


# Penjaga server: kalau ALLOWED_HOSTS berisi domain publik, tolak menyala
# selama DEBUG masih menyala atau secret key masih yang tertulis di repo.
_HOST_PUBLIK = [h for h in ALLOWED_HOSTS if not _host_lokal(h)]
if _HOST_PUBLIK:
    from django.core.exceptions import ImproperlyConfigured

    if DEBUG:
        raise ImproperlyConfigured(
            f"DJANGO_ALLOWED_HOSTS berisi domain publik ({', '.join(_HOST_PUBLIK)}) "
            "tapi DEBUG masih menyala. Set DJANGO_DEBUG=0 di server."
        )
    if SECRET_KEY == _SECRET_KEY_REPO:
        raise ImproperlyConfigured(
            f"DJANGO_ALLOWED_HOSTS berisi domain publik ({', '.join(_HOST_PUBLIK)}) "
            "tapi DJANGO_SECRET_KEY belum diisi, sehingga yang dipakai kunci yang "
            "tertulis di repo publik. Isi DJANGO_SECRET_KEY dengan kunci baru."
        )


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'kendaraan',
    'pelanggan',
    'kasir',
    'mekanik',
    'adminpanel',
    'sparepart',
    # App Pembelian Sparepart (FR-35): Supplier + transaksi pembelian stok.
    # Satu app per modul (NFR-7); hanya dipakai oleh Admin.
    'pembelian',
    'servis',
    'pembayaran',
    # App Laporan sesuai struktur folder di dokumen rancangan bagian 6.
    # Tidak punya models.py: isinya hierarki class Laporan (bagian 5E) yang
    # membaca data dari servis, pembayaran, sparepart dan accounts.
    'laporan',
    'landing',
    # FR-34: FAQ chat (chatbot berbasis aturan, tanpa AI).
    'faq',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Menyajikan /static/ saat DEBUG=0; harus tepat di bawah SecurityMiddleware.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bengkel_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'accounts' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'landing.context_processors.info_bengkel',
                # Form admin sebagai overlay: pilih kerangka penuh atau kosong (X-Modal).
                'accounts.context_processors.kerangka',
                # FR-31: badge jumlah pengajuan servis di navbar kasir.
                'kasir.context_processors.pengajuan_menunggu',
                # FR-32: angka kabar baru dan persetujuan di menu pelanggan.
                'pelanggan.context_processors.kabar_pelanggan',
                # QoL A4: angka pesan pelanggan di menu mekanik.
                'mekanik.context_processors.pesan_pelanggan',
                # Badge bukti pembayaran non-tunai di menu kasir/admin.
                'pembayaran.context_processors.bukti_menunggu',
            ],
        },
    },
]

WSGI_APPLICATION = 'bengkel_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

# Data yang harus selamat saat kontainer dibangun ulang (database dan unggahan).
# Di server: volume DJANGO_DATA_DIR; di laptop: folder proyek.
DATA_DIR = Path(os.environ.get("DJANGO_DATA_DIR") or BASE_DIR)
# Folder media dibuat kalau belum ada, supaya unggahan pertama tidak gagal
# pada volume yang masih kosong.
(DATA_DIR / "media").mkdir(parents=True, exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'id'

TIME_ZONE = 'Asia/Makassar'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # tujuan `python manage.py collectstatic` di server
# Dibuat kalau belum ada, supaya WhiteNoise tidak memperingatkan folder yang hilang.
STATIC_ROOT.mkdir(exist_ok=True)
# Penyimpanan bawaan, bukan "manifest": manifest membuat ERROR 500 kalau satu
# saja {% static %} menunjuk berkas yang tidak ada.


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

# Pengiriman e-mail untuk fitur lupa kata sandi.
# Tanpa setelan apa pun, isi e-mailnya dicetak ke terminal sehingga fiturnya
# bisa diuji tanpa server SMTP. Di server sungguhan, isi DJANGO_EMAIL_HOST dan
# kawan-kawannya lewat environment.
_EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
if _EMAIL_HOST:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "HOST": _EMAIL_HOST,
            "PORT": int(os.environ.get("DJANGO_EMAIL_PORT", "587")),
            "USER": os.environ.get("DJANGO_EMAIL_USER", ""),
            "PASSWORD": os.environ.get("DJANGO_EMAIL_PASSWORD", ""),
            "USE_TLS": os.environ.get("DJANGO_EMAIL_TLS", "1") == "1",
        },
    }
else:
    MAILERS = {
        "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
    }

DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_EMAIL_FROM", "no-reply@bengkel.local")

# E-mail sungguhan terkirim hanya kalau DJANGO_EMAIL_HOST diisi.
EMAIL_AKTIF = bool(_EMAIL_HOST)

# Halaman Lupa Kata Sandi memakai e-mail kalau e-mailnya memang terkirim, atau
# di laptop (DEBUG), tempat isi e-mail tercetak di terminal untuk diuji. Di
# server tanpa SMTP, halaman itu berterus terang dan mengarahkan ke kontak
# bengkel; admin mengganti kata sandinya lewat Kelola Pelanggan/Kasir/Mekanik.
LUPA_SANDI_LEWAT_EMAIL = EMAIL_AKTIF or DEBUG

# mail.E001 (check --deploy) memperingatkan bahwa backend console tidak
# mengirim e-mail. Tanpa SMTP itu memang disengaja: tidak ada fitur yang
# bergantung pada e-mail terkirim, karena LUPA_SANDI_LEWAT_EMAIL mati.
SILENCED_SYSTEM_CHECKS = [] if EMAIL_AKTIF else ["mail.E001"]

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'login'  
LOGIN_REDIRECT_URL = 'dashboard'  
LOGOUT_REDIRECT_URL = 'login'  
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailOrUsernameBackend"]

# Berkas yang diunggah pengguna (foto profil). Ikut DATA_DIR supaya tidak
# hilang saat kontainer dibangun ulang (lihat DATA_DIR di atas).
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"

# Bukti transfer/QRIS pelanggan. SENGAJA di luar MEDIA_ROOT karena /media/
# dilayani publik; berkas ini hanya dibuka lewat view yang memeriksa akses.
BUKTI_BAYAR_ROOT = DATA_DIR / "privat"


# Kontainer berada di belakang Nginx milik admin hosting. Tanpa dua baris ini,
# Django mengira permintaannya HTTP biasa, sehingga pemeriksaan CSRF pada
# alamat https gagal dan pengalihan bisa jatuh ke http.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Dua peringatan `check --deploy` yang sengaja dibiarkan:
# - security.W008: pengalihan https diurus Nginx; kalau Django ikut mengalihkan
#   tanpa X-Forwarded-Proto, situs terjebak redirect tanpa henti.
# - security.W004 (HSTS): subdomain bersama; HSTS tidak bisa ditarik kembali.
USE_X_FORWARDED_HOST = True

# Cookie hanya dikirim lewat https. Dinyalakan dengan DJANGO_HTTPS=1 di server.
# Dibiarkan mati saat mengembangkan di laptop, karena localhost memakai http
# biasa dan kalau dinyalakan, login jadi tidak bisa.
_PAKAI_HTTPS = os.environ.get("DJANGO_HTTPS", "0") == "1"
SESSION_COOKIE_SECURE = _PAKAI_HTTPS
CSRF_COOKIE_SECURE = _PAKAI_HTTPS


# Tes memakai hasher cepat karena hampir setiap tes membuat akun dan PBKDF2
# sengaja lambat. Hanya saat `manage.py test`.
import sys as _sys  # noqa: E402

if len(_sys.argv) > 1 and _sys.argv[1] == "test":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

    # seed_demo membuat contoh bukti pembayaran, dan banyak tes menjalankannya.
    # Tanpa ini berkas contoh itu menumpuk di folder privat sungguhan.
    import atexit as _atexit  # noqa: E402
    import shutil as _shutil  # noqa: E402
    import tempfile as _tempfile  # noqa: E402

    BUKTI_BAYAR_ROOT = Path(_tempfile.mkdtemp(prefix="bukti-tes-"))
    _atexit.register(_shutil.rmtree, BUKTI_BAYAR_ROOT, ignore_errors=True)
