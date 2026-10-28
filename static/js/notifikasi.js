/* Memperbarui badge menu tanpa memuat ulang halaman: tiap 30 detik dan saat tab aktif lagi.
   Angka dari /accounts/notifikasi/ (fungsi yang sama dengan context processor). */
(function () {
    "use strict";

    var URL_NOTIF = "/accounts/notifikasi/";
    var JEDA_MS = 30000;
    var judulAsli = document.title.replace(/^\(\d+\)\s*/, "");
    var pengatur = null;

    function pasangBadge(tempat, angka, data) {
        var span = tempat.querySelector("[data-badge]");
        if (!angka) {
            if (span) span.remove();
            return;
        }
        var warna = tempat.dataset.badgeWarnaDari ? data[tempat.dataset.badgeWarnaDari] : tempat.dataset.badgeWarna;
        if (!span) {
            span = document.createElement("span");
            span.dataset.badge = tempat.dataset.badgeTempat;
            tempat.appendChild(document.createTextNode(" "));
            tempat.appendChild(span);
        }
        span.className = "badge-st " + (warna || "merah");
        span.textContent = angka;
    }

    function terapkan(data) {
        var total = 0;
        document.querySelectorAll("[data-badge-tempat]").forEach(function (tempat) {
            var angka = Number(data[tempat.dataset.badgeTempat]) || 0;
            pasangBadge(tempat, angka, data);
            // Badge abu-abu hanya informasi (antrian, draf), tidak ikut dihitung di judul tab.
            if (tempat.dataset.badgeWarna !== "abu") total += angka;
        });
        document.title = total ? "(" + total + ") " + judulAsli : judulAsli;
    }

    function perbarui() {
        fetch(URL_NOTIF, { credentials: "same-origin", headers: { "Accept": "application/json" } })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(terapkan)
            .catch(function () { clearInterval(pengatur); });  // berhenti diam-diam bila gagal
    }

    if (!document.querySelector("[data-badge-tempat]")) return;
    // Judul tab langsung memakai angka yang sudah dirender server.
    var awal = {};
    document.querySelectorAll("[data-badge-tempat]").forEach(function (tempat) {
        var span = tempat.querySelector("[data-badge]");
        awal[tempat.dataset.badgeTempat] = span ? Number(span.textContent) || 0 : 0;
    });
    terapkan(awal);
    pengatur = setInterval(function () { if (!document.hidden) perbarui(); }, JEDA_MS);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) perbarui(); });
})();
