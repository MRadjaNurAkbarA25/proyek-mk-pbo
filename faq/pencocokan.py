"""FR-34: pencocokan teks chatbot FAQ. Berbasis aturan, hanya pustaka standar.

Urutan pemrosesan ketikan (dan teks FAQ, dengan cara yang sama):
normalisasi -> frasa jadi satu token -> kata umum dibuang -> sinonim/ejaan ->
stemming ringan -> koreksi salah ketik. Lalu diberi skor mirip IDF.
Semua fungsi di sini murni (tanpa database) supaya mudah dites.
"""
import difflib
import math
import re

# ---- 1. normalisasi --------------------------------------------------------
_GABUNG = [
    (r"\be ?wallet\b", "ewallet"),
    (r"\be ?money\b", "emoney"),
    (r"\bsign ?up\b", "signup"),
    (r"\blog ?in\b", "login"),
    (r"\b(no|nmr|nomor|nomer) ?(hp|telp|telpon|telepon|tlp|wa|whatsapp)\b", "nohp"),
]


def normalisasi(teks):
    teks = re.sub(r"[^\w]+", " ", (teks or "").lower()).replace("_", " ")
    for pola, ganti in _GABUNG:
        teks = re.sub(pola, ganti, teks)
    return " ".join(teks.split())


# ---- 2. frasa -> satu token (sebelum kata dipecah) --------------------------
# Kata penyusun frasa tidak ikut dihitung lagi: "home service" tidak boleh
# menyumbang skor ke FAQ servis bengkel.
FRASA = {
    "home_service": [
        "home service", "homeservice", "home servis", "home servise", "home serpis", "home srvis",
        "servis panggilan", "service panggilan", "servis ke rumah", "service ke rumah",
        "servis di rumah", "service di rumah", "servis rumah", "panggil mekanik",
        "panggilan mekanik", "mekanik datang", "mekanik ke rumah", "mekanik dateng",
    ],
    "sandi": ["kata sandi", "kata kunci akun", "password", "passwd", "pasword", "pw", "sandi"],
    "nopol": ["nomor polisi", "nomer polisi", "no polisi", "plat nomor", "plat nomer", "pelat nomor",
              "nomor plat", "plat", "pelat", "nopol"],
    "qris": ["scan qr", "kode qr", "qr code", "qrcode", "qris", "emoney", "ewallet",
             "dana", "ovo", "gopay", "shopeepay", "linkaja"],
    "daftar_harga": ["daftar harga", "list harga", "price list", "pricelist", "harga layanan",
                     "harga jasa", "tarif layanan"],
    "durasi": ["berapa lama", "brp lama", "brapa lama", "berapa jam", "brp jam"],
    "terima_kasih": ["terima kasih", "terimakasih", "trima kasih", "makasih", "makasi", "mksh",
                     "thanks", "thank you", "thx", "tengkyu", "trims", "tq"],
}
_FRASA_URUT = sorted(((f, t) for t, daftar in FRASA.items() for f in daftar), key=lambda x: -len(x[0]))
_POLA_FRASA = [(re.compile(rf"\b{re.escape(f)}\b"), t) for f, t in _FRASA_URUT]


def ganti_frasa(teks):
    for pola, t in _POLA_FRASA:
        teks = pola.sub(f" {t} ", teks)
    return " ".join(teks.split())


# ---- 3. kata umum dan kata tanya ------------------------------------------
KATA_UMUM = {
    "saya", "aku", "gue", "gw", "sy", "kami", "kita", "anda", "kamu", "yang", "yg", "di", "ke", "dari",
    "dan", "atau", "apa", "apakah", "bisa", "bs", "bisakah", "dapat", "gak", "ga", "gk", "nggak",
    "ngga", "enggak", "tidak", "tdk", "tak", "mau", "ingin", "pengen", "pingin", "dong", "donk", "sih",
    "ya", "iya", "yah", "kak", "kakak", "min", "mimin", "gan", "bang", "mas", "mbak", "pak", "bu",
    "halo", "hai", "hi", "hello", "hallo", "pagi", "siang", "sore", "malam", "permisi", "selamat",
    "assalamualaikum", "ini", "itu", "ada", "adalah", "untuk", "buat", "dengan", "pada", "juga",
    "aja", "saja", "kok", "deh", "nih", "tuh", "tolong", "mohon", "please", "pls",
    "gitu", "begitu", "jadi", "karena", "krn", "kalau", "kalo", "klo", "jika", "bila",
    "terus", "trus", "lalu", "banget", "bgt", "sekali",
    "nya", "si", "pakai", "pake", "via", "lewat", "soal", "tentang", "mengenai", "banyak", "kah",
    "lah", "punya", "boleh", "akan", "harus", "perlu", "seperti", "semua", "sama", "baru", "oke",
    "terima_kasih",
}
# "cara" ikut sebagai sinyal lemah: membedakan "cara pesan" dari "setelah pesan".
KATA_TANYA = {"berapa", "kapan", "bagaimana", "dimana", "kenapa", "cara"}
BOBOT_KATA_TANYA = 0.3

# ---- 4. sinonim dan ejaan tidak baku -> kata dasar --------------------------
_SINONIM_KELOMPOK = {
    "servis": ["service", "servise", "serpis", "srvis", "servic", "servs", "srv"],
    "bayar": ["byr", "bayaran", "pembayran", "pay", "payment"],
    "batal": ["cancel", "cancle", "cansel", "batalin", "dibatalin", "hangus"],
    "berapa": ["brp", "brapa", "berapakah"],
    "kapan": ["kpn", "kapankah"],
    "bagaimana": ["gmn", "gimana", "bgmn", "gmna", "gimn", "bagaimanakah"],
    "dimana": ["dmn", "mana", "dimanakah"],
    "kenapa": ["knp", "napa", "mengapa", "kenapakah"],
    "cara": ["caranya", "carane", "gmana"],
    "motor": ["mtr", "montor", "sepeda"],
    "mobil": ["mbl", "oto"],
    "oli": ["oil", "olie"],
    "akun": ["account", "acount", "akn"],
    "daftar": ["regis", "register", "registrasi", "signup", "daftarkan", "pendaftaran"],
    "login": ["signin", "masuk"],
    "transfer": ["tf", "trf", "transfr", "trasfer"],
    "tunai": ["cash", "kes", "cas", "kontan"],
    "nota": ["struk", "kwitansi", "kuitansi", "invoice", "resi"],
    "ubah": ["ganti", "edit", "rubah", "update", "perbarui", "koreksi", "betulkan", "benerin"],
    "hapus": ["delete", "hps", "apus", "buang", "remove"],
    "tambah": ["add", "tmbh", "nambah", "bertambah"],
    "mekanik": ["montir", "teknisi", "mekanic", "mechanic", "mekanis"],
    "kendaraan": ["kndaraan", "kenderaan", "ranmor", "kendaraannya"],
    "whatsapp": ["wa", "whatsap", "watsap", "wasap", "wa'an"],
    "kontak": ["hubungi", "menghubungi", "telepon", "telpon", "nelpon", "nohp", "hp", "telp"],
    "harga": ["tarif", "hrg"],
    "biaya": ["ongkos", "byaya"],
    "lama": ["lma", "lamaa"],
    "foto": ["poto", "photo", "gambar"],
    "profil": ["profile", "propil"],
    "setuju": ["acc", "approve", "setujui", "menyetujui", "persetujuan"],
    "diagnosis": ["diagnosa", "diagnose"],
    "pesan": ["memesan", "pesanan", "booking", "order"],
    "ajukan": ["ajuan", "pengajuan", "mengajukan"],
    "tunggu": ["menunggu", "nunggu", "tunggu"],
    "kirim": ["mengirim", "ngirim", "kirimkan", "upload", "unggah", "mengunggah"],
    "terima": ["menerima", "nerima", "diterima"],
    "tolak": ["menolak", "penolakan", "reject", "ditolak"],
    "periksa": ["diperiksa", "memeriksa", "pemeriksaan", "cek", "check", "verifikasi", "diverifikasi"],
    "pantau": ["memantau", "lacak", "track", "tracking", "monitor"],
    "kerja": ["pengerjaan", "dikerjakan", "mengerjakan", "dikerjain"],
    "datang": ["kedatangan", "dateng", "tiba", "sampai"],
    "tanya": ["bertanya", "nanya", "pertanyaan", "menanyakan"],
    "lihat": ["liat", "melihat", "dilihat"],
    "selesai": ["kelar", "beres", "rampung"],
    "rumah": ["rmh"],
    "bengkel": ["bengkelnya", "workshop"],
    "sparepart": ["spare", "part", "suku", "onderdil", "parts"],
    "lanjut": ["lanjutkan", "dilanjut", "dilanjutkan", "melanjutkan"],
    "lokasi": ["daerah", "wilayah", "area", "jangkauan"],
    "alamat": ["almt"],
    "jam": ["pukul"],
    "status": ["stat", "keadaan"],
    "setelah": ["sesudah", "sudah", "udah", "udh", "sdh", "habis", "abis", "sehabis"],
    "lagi": ["ulang", "kembali"],
}
SINONIM = {kata: dasar for dasar, daftar in _SINONIM_KELOMPOK.items() for kata in daftar}

# ---- 5. stemming ringan -----------------------------------------------------
AWALAN = ("meng", "meny", "mem", "men", "me", "peng", "peny", "pem", "pen", "per", "pe", "ber", "di")
AKHIRAN = ("kan", "an", "i")
PARTIKEL = ("nya", "lah", "kah")
SISA_MIN = 4
# Kata dasar yang kebetulan mirip berimbuhan; jangan dipotong.
TIDAK_DISTEM = {
    "mekanik", "metode", "menit", "menu", "merek", "merk", "pesan", "periksa", "perlu", "pelanggan",
    "kendaraan", "layanan", "diagnosis", "dian", "bengkel", "berapa", "cara", "persen", "pemilik", "ganti",
    "tunai", "selesai", "pakai", "hari", "mulai", "sampai", "kunci", "beli", "isi", "dimana", "transfer",
    "bulan", "jalan", "dengan", "pertama", "bertanya", "tanya", "perbaikan", "teknisi", "sparepart",
    "sandi", "rantai", "aki", "ban", "rem", "oli", "durasi", "status", "nota", "login", "akun",
    "lokasi", "alamat", "profil", "foto", "harga", "biaya", "datang", "terima", "tolak", "motor",
    "mobil", "rumah", "panggilan", "pengajuan", "percobaan", "pindai", "bukti", "setelah", "lagi",
}


def akar(kata):
    """Buang satu awalan dan satu akhiran bila sisanya masih >= 4 huruf."""
    if kata in TIDAK_DISTEM or "_" in kata or not kata.isalpha():
        return kata
    for awal in AWALAN:
        if kata.startswith(awal) and len(kata) - len(awal) >= SISA_MIN:
            kata = kata[len(awal):]
            break
    for akhir in PARTIKEL:
        if kata.endswith(akhir) and len(kata) - len(akhir) >= SISA_MIN:
            kata = kata[:-len(akhir)]
            break
    if kata in TIDAK_DISTEM:
        return kata
    for akhir in AKHIRAN:
        if kata.endswith(akhir) and len(kata) - len(akhir) >= SISA_MIN:
            return kata[:-len(akhir)]
    return kata


def kata_dasar(kata):
    """Sinonim dulu, lalu stemming, lalu sinonim lagi untuk hasil stemming."""
    if kata in SINONIM:
        return SINONIM[kata]
    hasil = akar(kata)
    return SINONIM.get(hasil, hasil)


# ---- 6. token dan salah ketik ---------------------------------------------
PANJANG_MIN_KOREKSI = 5
BATAS_MIRIP = 0.8


def _koreksi(mentah, dasar, kosakata):
    if dasar in kosakata or dasar in KATA_TANYA or len(mentah) < PANJANG_MIN_KOREKSI:
        return dasar
    for calon in (mentah, dasar):
        cocok = difflib.get_close_matches(calon, kosakata, n=1, cutoff=BATAS_MIRIP)
        if cocok:
            return cocok[0]
    return dasar


def token(teks, kosakata=None):
    """Daftar token bermakna dari `teks`, urut dan tanpa dobel.

    kosakata: himpunan token yang dikenal FAQ; kalau diberikan, kata >= 5 huruf
    yang tidak dikenal dicocokkan ke kata terdekat (difflib).
    """
    hasil = []
    for mentah in ganti_frasa(normalisasi(teks)).split():
        if mentah in KATA_UMUM:
            continue
        dasar = kata_dasar(mentah)
        if dasar in KATA_UMUM:
            continue
        if kosakata:
            dasar = _koreksi(mentah, dasar, kosakata)
        if dasar not in hasil:
            hasil.append(dasar)
    return hasil


# ---- 7. sapaan, terima kasih, dan skor ---------------------------------------
SAPAAN = {"halo", "hai", "hi", "hello", "hallo", "pagi", "siang", "sore", "malam", "permisi",
          "selamat", "assalamualaikum", "salam", "hey", "hei", "p"}
_PANGGILAN = {"kak", "kakak", "min", "mimin", "gan", "bang", "mas", "mbak", "pak", "bu", "ya", "admin", "banyak"}


def jenis_sapaan(teks):
    """"sapaan" / "terima_kasih" bila ketikan HANYA itu; selain itu None."""
    kata = ganti_frasa(normalisasi(teks)).split()
    if not kata:
        return None
    if "terima_kasih" in kata and set(kata) <= {"terima_kasih"} | _PANGGILAN | SAPAAN:
        return "terima_kasih"
    if set(kata) & SAPAAN and set(kata) <= SAPAAN | _PANGGILAN:
        return "sapaan"
    return None


BOBOT_PERTANYAAN = 1.0
BOBOT_KATA_KUNCI = 0.8
CAKUPAN_MIN = 0.4   # bagian dari bobot ketikan yang harus dikenali FAQ itu


def _bobot(t, idf, idf_maks):
    return idf.get(t, idf_maks) * (BOBOT_KATA_TANYA if t in KATA_TANYA else 1.0)


def nilai(teks, dokumen):
    """Skor tiap dokumen (pertanyaan, kata_kunci) untuk `teks`; 0 bila tidak layak.

    Kata yang langka di antara semua FAQ lebih berbobot (mirip IDF). Kata ketikan
    yang tidak dikenal FAQ mana pun ikut menambah penyebut cakupan, jadi ketikan
    yang sebagian besar tidak nyambung (misalnya "harga saham") ditolak.
    """
    dok = [(set(token(p)), set(token(k))) for p, k in dokumen]
    kosakata = set().union(*(a | b for a, b in dok)) if dok else set()
    q = token(teks, kosakata)
    if not q or not dok:
        return [0] * len(dok)

    n = len(dok)
    idf = {}
    for t in kosakata:
        df = sum(1 for a, b in dok if t in a or t in b)
        idf[t] = 1 + math.log(n / df)
    idf_maks = 1 + math.log(n + 1)
    total = sum(_bobot(t, idf, idf_maks) for t in q)

    hasil = []
    for tanya, kunci in dok:
        skor = 0.0
        for t in q:
            if t in tanya:
                skor += _bobot(t, idf, idf_maks) * BOBOT_PERTANYAAN
            elif t in kunci:
                skor += _bobot(t, idf, idf_maks) * BOBOT_KATA_KUNCI
        # Hanya kata tanya yang cocok tidak cukup ("berapa" saja).
        isi = any(t in tanya or t in kunci for t in q if t not in KATA_TANYA)
        hasil.append(round(skor, 4) if isi and skor / total >= CAKUPAN_MIN else 0)
    return hasil


RASIO_YAKIN = 1.4


def yakin(skor_urut):
    """Skor teratas jelas unggul dari yang kedua."""
    if not skor_urut:
        return False
    return len(skor_urut) == 1 or skor_urut[0] >= RASIO_YAKIN * skor_urut[1]
