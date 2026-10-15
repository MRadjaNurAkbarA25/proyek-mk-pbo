/* Pop up konfirmasi di halaman Profil Saya.
   Muncul saat URL membawa ?sandi=ok atau ?simpan=ok, lalu penanda itu
   dibersihkan dari URL supaya pop up tidak muncul lagi kalau halaman di-refresh. */
(function () {
    var latar = document.getElementById("popupSukses");
    if (!latar) return;
    var tombol = document.getElementById("popupTutup");

    function tutup() {
        latar.remove();
        document.removeEventListener("keydown", padaTombolPapanKetik);
    }
    function padaTombolPapanKetik(e) {
        if (e.key === "Escape") tutup();
    }

    if (tombol) tombol.addEventListener("click", tutup);
    latar.addEventListener("click", function (e) { if (e.target === latar) tutup(); });
    document.addEventListener("keydown", padaTombolPapanKetik);
    if (tombol) tombol.focus();

    // Hapus ?sandi=ok / ?simpan=ok dari alamat tanpa memuat ulang halaman.
    if (window.history && window.history.replaceState) {
        window.history.replaceState({}, "", window.location.pathname);
    }
})();
