"""Context processor untuk kerangka halaman admin/kasir."""


def kerangka(request):
    """Pilih kerangka untuk form yang bisa dibuka sebagai overlay.

    static/js/modal.js memuat form dengan header X-Modal. Template form cukup
    menulis {% extends kerangka_dasar %}: dengan header itu yang dipakai
    _kerangka_modal.html (isi kartu saja), tanpa header kerangka.html penuh.
    Jadi view tidak perlu membedakan dua cara buka tersebut.
    """
    modal = bool(request.headers.get("X-Modal"))
    return {"kerangka_dasar": "_kerangka_modal.html" if modal else "kerangka.html"}
