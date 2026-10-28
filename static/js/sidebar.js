/* Pertahankan posisi gulir sidebar admin antar halaman (sessionStorage);
   kalau belum ada, gulir menu aktif ke pandangan. */
(function () {
    var menu = document.querySelector(".app-sidebar > .menu:not(.menu-bawah)");
    if (!menu) return;
    var KUNCI = "gulir-sidebar";

    var tersimpan = null;
    try { tersimpan = sessionStorage.getItem(KUNCI); } catch (e) {}
    if (tersimpan !== null && !isNaN(parseInt(tersimpan, 10))) {
        menu.scrollTop = parseInt(tersimpan, 10);
    } else {
        var aktif = menu.querySelector("a.aktif");
        if (aktif) aktif.scrollIntoView({ block: "nearest" });
    }

    function simpan() {
        try { sessionStorage.setItem(KUNCI, String(menu.scrollTop)); } catch (e) {}
    }
    /* pagehide juga terpanggil saat pindah lewat tombol Back/formulir, tidak
       hanya saat menu diklik. */
    window.addEventListener("pagehide", simpan);
    menu.addEventListener("click", simpan);
})();
