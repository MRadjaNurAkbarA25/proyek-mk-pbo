/* Overlay form tambah/ubah admin: tautan data-modal dimuat dengan header X-Modal
   dan dikirim lewat fetch; kalau fetch gagal, tautan dibuka sebagai halaman penuh. */
(function () {
    var latar = document.createElement("div");
    latar.className = "km-latar";
    latar.hidden = true;
    latar.innerHTML = '<div class="km-wadah" role="dialog" aria-modal="true"></div>';
    document.body.appendChild(latar);
    var wadah = latar.firstChild;
    var kepala = { "X-Modal": "1" };

    function tampilkan(html) {
        wadah.innerHTML = html;
        latar.hidden = false;
        document.body.classList.add("km-terbuka");
        var fokus = wadah.querySelector("input:not([type=hidden]), select, textarea");
        if (fokus) fokus.focus();
    }
    function tutup() {
        latar.hidden = true;
        wadah.innerHTML = "";
        document.body.classList.remove("km-terbuka");
    }
    function buka(url) {
        fetch(url, { headers: kepala })
            .then(function (r) { if (!r.ok) throw r; return r.text(); })
            .then(tampilkan)
            .catch(function () { window.location.href = url; });
    }

    document.addEventListener("click", function (e) {
        if (!latar.hidden && (e.target === latar || e.target.closest(".km-latar [data-tutup-modal]"))) {
            e.preventDefault();
            tutup();
            return;
        }
        var tautan = e.target.closest("a[data-modal]");
        if (tautan) { e.preventDefault(); buka(tautan.href); }
    });
    latar.addEventListener("submit", function (e) {
        var form = e.target;
        e.preventDefault();
        /* redirect: "manual" supaya halaman tujuan tidak ikut dimuat di sini
           (pesan sukses Django akan habis terbaca sebelum halaman dimuat ulang). */
        fetch(form.action, { method: "POST", body: new FormData(form), headers: kepala, redirect: "manual" })
            .then(function (r) {
                if (r.type === "opaqueredirect" || (r.status >= 300 && r.status < 400)) {
                    window.location.reload();
                    return;
                }
                if (!r.ok) throw r;
                return r.text().then(tampilkan);
            })
            .catch(function () { form.submit(); });
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !latar.hidden) tutup();
    });
})();
