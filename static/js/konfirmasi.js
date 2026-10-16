/* Dialog konfirmasi untuk form yang bertanda data-konfirmasi="pesan".
   Dipakai tombol Keluar di keempat kerangka halaman, dan bisa dipakai ulang
   untuk aksi lain yang perlu ditanya dulu. Tanpa JavaScript, form tetap
   terkirim seperti biasa. */
(function () {
    var semuaForm = document.querySelectorAll("form[data-konfirmasi]");
    if (!semuaForm.length) return;

    function tanya(pesan, judul, labelYa, saatSetuju) {
        var latar = document.createElement("div");
        latar.className = "konf-latar";
        latar.innerHTML =
            '<div class="konf-kotak" role="dialog" aria-modal="true">' +
            '<h3 class="konf-judul"></h3>' +
            '<p class="konf-pesan"></p>' +
            '<div class="konf-aksi">' +
            '<button type="button" class="konf-batal">Batal</button>' +
            '<button type="button" class="konf-ya"></button>' +
            "</div></div>";
        latar.querySelector(".konf-judul").textContent = judul;
        latar.querySelector(".konf-pesan").textContent = pesan;
        latar.querySelector(".konf-ya").textContent = labelYa;
        document.body.appendChild(latar);

        function tutup() {
            latar.remove();
            document.removeEventListener("keydown", padaTombol);
        }
        function padaTombol(e) {
            if (e.key === "Escape") tutup();
        }

        latar.querySelector(".konf-batal").addEventListener("click", tutup);
        latar.querySelector(".konf-ya").addEventListener("click", function () {
            tutup();
            saatSetuju();
        });
        latar.addEventListener("click", function (e) { if (e.target === latar) tutup(); });
        document.addEventListener("keydown", padaTombol);
        latar.querySelector(".konf-batal").focus();
    }

    semuaForm.forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (form.dataset.sudahDikonfirmasi === "ya") return;
            e.preventDefault();
            tanya(
                form.dataset.konfirmasi,
                form.dataset.konfirmasiJudul || "Konfirmasi",
                form.dataset.konfirmasiYa || "Ya, lanjutkan",
                function () {
                    form.dataset.sudahDikonfirmasi = "ya";
                    form.submit();
                }
            );
        });
    });
})();
