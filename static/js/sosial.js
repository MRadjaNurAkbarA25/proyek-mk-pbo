/* Tombol login/daftar lewat Facebook, Google, dan Apple belum terhubung ke
   penyedia mana pun. Sebelumnya tombolnya "disabled" sehingga diklik tidak
   terjadi apa-apa dan pengguna mengira halamannya rusak. Sekarang tombolnya
   bisa diklik dan memunculkan keterangan singkat. */
(function () {
    var pesan = document.getElementById("sosialPesan");
    var tombol = document.querySelectorAll(".tombol-sosial");
    if (!pesan || !tombol.length) return;

    var jeda = null;
    tombol.forEach(function (btn) {
        btn.addEventListener("click", function () {
            var nama = btn.getAttribute("data-sosial") || "Layanan ini";
            pesan.textContent = "Masuk dengan " + nama + " belum tersedia. Silakan gunakan e-mail dan kata sandi.";
            pesan.hidden = false;
            if (jeda) clearTimeout(jeda);
            jeda = setTimeout(function () { pesan.hidden = true; }, 5000);
        });
    });
})();
