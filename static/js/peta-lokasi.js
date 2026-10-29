/* Peta penanda lokasi di bawah kolom alamat (elemen [data-peta-lokasi]).
   Leaflet + ubin OpenStreetMap; alamat dari Nominatim, maks 1 permintaan/detik. */
(function () {
    "use strict";

    var NOMINATIM = "https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=id&zoom=18";
    var JEDA_MS = 800;
    var terakhirMinta = 0;

    function pasang(wadah) {
        if (typeof L === "undefined") return;  // Leaflet gagal dimuat (offline): form tetap bisa diisi manual.

        var alamat = document.getElementById(wadah.dataset.alamat);
        var isianLat = document.getElementById(wadah.dataset.lat);
        var isianLng = document.getElementById(wadah.dataset.lng);
        var status = wadah.querySelector(".peta-status");
        var saran = wadah.querySelector(".peta-saran");
        var tombolHapus = wadah.querySelector(".peta-hapus");
        var tombolSaya = wadah.querySelector(".peta-lokasi-saya");
        if (!alamat || !isianLat || !isianLng) return;

        wadah.hidden = false;
        L.Icon.Default.imagePath = wadah.dataset.ikon;

        var tersimpan = isianLat.value && isianLng.value;
        var pusat = tersimpan
            ? [parseFloat(isianLat.value), parseFloat(isianLng.value)]
            : [parseFloat(wadah.dataset.pusatLat), parseFloat(wadah.dataset.pusatLng)];
        var peta = L.map(wadah.querySelector(".peta-kanvas")).setView(pusat, tersimpan ? 17 : 13);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            referrerPolicy: "strict-origin-when-cross-origin",
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
        }).addTo(peta);

        var pin = L.marker(pusat, { draggable: true }).addTo(peta);
        var alamatDariPeta = "";  // teks terakhir yang diisi peta; selama sama, boleh ditimpa lagi.
        var pengatur = null;

        function tulisStatus(teks, galat) {
            status.textContent = teks;
            status.classList.toggle("galat", !!galat);
        }

        function rapikan(nama) {
            return nama.replace(/,\s*Indonesia$/, "");
        }

        function isiAlamat(teks) {
            alamat.value = teks;
            alamatDariPeta = teks;
            saran.hidden = true;
            tulisStatus("Periksa dan lengkapi alamat (nomor rumah, patokan).");
        }

        function cariAlamat(lat, lng) {
            var tunggu = Math.max(0, terakhirMinta + 1000 - Date.now());
            clearTimeout(pengatur);
            pengatur = setTimeout(function () {
                terakhirMinta = Date.now();
                tulisStatus("Mencari alamat…");
                fetch(NOMINATIM + "&lat=" + lat + "&lon=" + lng, { headers: { "Accept": "application/json" }, referrerPolicy: "strict-origin-when-cross-origin" })
                    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
                    .then(function (data) {
                        if (!data || !data.display_name) throw new Error("kosong");
                        var teks = rapikan(data.display_name);
                        var kosong = !alamat.value.trim();
                        if (kosong || alamat.value === alamatDariPeta) {
                            isiAlamat(teks);
                        } else {
                            saran.textContent = "Gunakan alamat dari peta: " + teks;
                            saran.dataset.alamat = teks;
                            saran.hidden = false;
                            tulisStatus("Titik tersimpan. Alamat yang Anda ketik tidak diubah.");
                        }
                    })
                    .catch(function () {
                        tulisStatus("Alamat untuk titik ini tidak ditemukan. Titik lokasi tetap tersimpan.", true);
                    });
            }, JEDA_MS + tunggu);
        }

        function setelTitik(latlng) {
            pin.setLatLng(latlng);
            isianLat.value = latlng.lat.toFixed(6);
            isianLng.value = latlng.lng.toFixed(6);
            tombolHapus.hidden = false;
            cariAlamat(isianLat.value, isianLng.value);
        }

        peta.on("click", function (e) { setelTitik(e.latlng); });
        pin.on("dragend", function () { setelTitik(pin.getLatLng()); });

        alamat.addEventListener("input", function () {
            if (alamat.value !== alamatDariPeta) alamatDariPeta = "";
        });
        saran.addEventListener("click", function () { isiAlamat(saran.dataset.alamat || ""); });

        tombolHapus.hidden = !tersimpan;
        tombolHapus.addEventListener("click", function () {
            isianLat.value = "";
            isianLng.value = "";
            tombolHapus.hidden = true;
            saran.hidden = true;
            clearTimeout(pengatur);
            tulisStatus("Titik dihapus. Geser pin ke lokasi Anda");
        });

        // Geolokasi hanya jalan di HTTPS atau localhost.
        if (navigator.geolocation && window.isSecureContext) {
            tombolSaya.hidden = false;
            tombolSaya.addEventListener("click", function () {
                tulisStatus("Mencari lokasi Anda…");
                navigator.geolocation.getCurrentPosition(function (pos) {
                    var latlng = L.latLng(pos.coords.latitude, pos.coords.longitude);
                    peta.setView(latlng, 17);
                    setelTitik(latlng);
                }, function (err) {
                    tulisStatus(err.code === 1
                        ? "Izin lokasi ditolak. Klik peta atau geser pin ke lokasi Anda."
                        : "Lokasi Anda tidak ditemukan. Klik peta atau geser pin ke lokasi Anda.", true);
                }, { enableHighAccuracy: true, timeout: 10000 });
            });
        }

        if (tersimpan) tulisStatus("Titik tersimpan. Geser pin bila perlu.");
        // Peta di dalam elemen yang baru tampil perlu menghitung ulang ukurannya.
        setTimeout(function () { peta.invalidateSize(); }, 0);
    }

    document.querySelectorAll("[data-peta-lokasi]").forEach(pasang);
})();
