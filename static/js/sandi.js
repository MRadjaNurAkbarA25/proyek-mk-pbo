/* Tombol tampilkan/sembunyikan kata sandi di halaman Login dan Buat Akun.
   Dipasang pada setiap tombol bertanda data-lihat-sandi="<id input>". */
(function () {
    var tombolSemua = document.querySelectorAll("[data-lihat-sandi]");
    if (!tombolSemua.length) return;

    tombolSemua.forEach(function (tombol) {
        var input = document.getElementById(tombol.getAttribute("data-lihat-sandi"));
        if (!input) return;

        tombol.hidden = false;
        tombol.addEventListener("click", function () {
            var tersembunyi = input.type === "password";
            input.type = tersembunyi ? "text" : "password";
            tombol.classList.toggle("terlihat", tersembunyi);
            tombol.setAttribute("aria-pressed", tersembunyi ? "true" : "false");
            tombol.setAttribute("aria-label", tersembunyi ? "Sembunyikan kata sandi" : "Tampilkan kata sandi");
            tombol.title = tersembunyi ? "Sembunyikan kata sandi" : "Tampilkan kata sandi";
            input.focus();
        });
    });
})();
