/* Sidebar admin bisa digulir (kerangka.css), tapi setiap pindah halaman
   posisinya kembali ke atas. Posisi gulir disimpan di sessionStorage sebelum
   halaman ditinggalkan dan dipulihkan saat halaman berikutnya dimuat. Kalau
   belum ada (atau penyimpanan browser diblokir), menu yang aktif digulir
   masuk ke pandangan. */
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
