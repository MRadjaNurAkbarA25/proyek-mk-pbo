"""Context processor untuk kerangka halaman admin/kasir."""


def kerangka(request):
    """Pilih kerangka form: _kerangka_modal.html untuk overlay (header X-Modal), kerangka penuh selain itu.

    Template cukup menulis {% extends kerangka_dasar %}, view tidak perlu membedakannya.
    """
    modal = bool(request.headers.get("X-Modal"))
    return {"kerangka_dasar": "_kerangka_modal.html" if modal else "kerangka.html"}
