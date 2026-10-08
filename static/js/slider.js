(function () {
    var foto = document.querySelectorAll(".slider-foto img");
    var titik = document.querySelectorAll(".slider-titik span");
    if (foto.length < 2) return;
    var i = 0;
    function tampil(n) {
        foto[i].classList.remove("aktif"); titik[i].classList.remove("aktif");
        i = n;
        foto[i].classList.add("aktif"); titik[i].classList.add("aktif");
    }
    var timer = setInterval(function () { tampil((i + 1) % foto.length); }, 4000);
    titik.forEach(function (t, n) {
        t.addEventListener("click", function () { clearInterval(timer); tampil(n); });
    });
})();
