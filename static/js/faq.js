/* FR-34: jendela chat FAQ.
   File ini hanya MENAMPILKAN. Pencocokan kata kunci dilakukan di server
   (PertanyaanFAQ.cari), termasuk mengenali sapaan dan menilai apakah
   jawaban teratas cukup yakin (field "jenis" dan "yakin"). Percakapan tidak
   disimpan: tidak ke server, tidak ke localStorage; hilang saat halaman ditutup.
   Teks dipasang lewat textContent (bukan innerHTML), jadi isi FAQ tidak
   pernah dijalankan sebagai HTML. */
(function () {
    "use strict";
    var akar = document.getElementById("faq-chat");
    if (!akar) return;

    var tombol = akar.querySelector(".faq-tombol");
    var jendela = akar.querySelector(".faq-jendela");
    var log = akar.querySelector(".faq-log");
    var form = akar.querySelector(".faq-form");
    var input = akar.querySelector(".faq-input");
    var nomorWa = akar.dataset.wa || "";
    var namaBengkel = akar.dataset.nama || "bengkel";
    var kategori = null;      // hasil faq_daftar, diambil sekali per halaman
    var sudahSapa = false;

    function el(tag, kelas, teks) {
        var e = document.createElement(tag);
        if (kelas) e.className = kelas;
        if (teks !== undefined) e.textContent = teks;
        return e;
    }
    function gulir() { log.scrollTop = log.scrollHeight; }

    function gelembung(dari, teks, judul) {
        var baris = el("div", "faq-baris " + dari);
        var isi = el("div", "faq-gelembung");
        if (judul) { isi.appendChild(el("strong", "faq-judul", judul)); }
        isi.appendChild(document.createTextNode(teks));
        baris.appendChild(isi);
        log.appendChild(baris);
        gulir();
    }

    // item: {label, aksi} untuk tombol, atau {label, href} untuk tautan
    function pilihan(items) {
        var kotak = el("div", "faq-pilihan");
        items.forEach(function (it) {
            var b;
            if (it.href) {
                b = el("a", "faq-opsi wa", it.label);
                b.href = it.href; b.target = "_blank"; b.rel = "noopener";
            } else {
                b = el("button", "faq-opsi", it.label);
                b.type = "button";
                b.addEventListener("click", it.aksi);
            }
            kotak.appendChild(b);
        });
        log.appendChild(kotak);
        gulir();
    }

    function tautanWa(teksPengguna) {
        if (!nomorWa) return [];
        var pesan = "Halo " + namaBengkel + ", saya ingin bertanya" + (teksPengguna ? ": " + teksPengguna : ".");
        return [{ label: "Tanya lewat WhatsApp", href: "https://wa.me/" + nomorWa + "?text=" + encodeURIComponent(pesan) }];
    }

    var KEMBALI = { label: "← Kembali ke kategori", aksi: function () { muatKategori(); } };

    function tombolKategori() {
        return (kategori || []).map(function (k) {
            return { label: k.nama, aksi: function () { pilihKategori(k); } };
        });
    }

    function tidakAda(teksPengguna) {
        gelembung("bot", "Maaf, belum ada jawabannya. Coba pilih topik di bawah, atau tanya langsung ke bengkel.");
        denganKategori(function () { pilihan(tombolKategori().concat(tautanWa(teksPengguna))); });
    }

    function tampilKategori() {
        if (!kategori.length) {
            gelembung("bot", "Maaf, belum ada jawabannya.");
            pilihan(tautanWa(""));
            return;
        }
        gelembung("bot", "Pilih topik yang ingin Anda tanyakan:");
        pilihan(tombolKategori());
    }

    function pilihKategori(k) {
        gelembung("pengguna", k.nama);
        gelembung("bot", "Pilih pertanyaan:");
        var items = k.pertanyaan.map(function (f) {
            return { label: f.pertanyaan, aksi: function () { tampilJawaban(f); } };
        });
        items.push(KEMBALI);
        pilihan(items);
    }

    function tombolFaq(daftar) {
        return daftar.map(function (f) {
            return { label: f.pertanyaan, aksi: function () { tampilJawaban(f); } };
        });
    }

    function tampilJawaban(f) {
        gelembung("pengguna", f.pertanyaan);
        gelembung("bot", f.jawaban);
        pilihan([KEMBALI]);
    }

    function ambil(url, sukses, gagal) {
        fetch(url, { headers: { "Accept": "application/json" } })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(sukses)
            .catch(gagal);
    }

    function gangguan() {
        gelembung("bot", "Maaf, terjadi gangguan saat memuat jawaban. Silakan coba lagi atau hubungi bengkel.");
        pilihan(tautanWa(""));
    }

    function denganKategori(lanjut) {
        if (kategori) { lanjut(); return; }
        ambil(akar.dataset.urlDaftar, function (d) { kategori = d.kategori || []; lanjut(); }, gangguan);
    }

    function muatKategori() { denganKategori(tampilKategori); }

    // d: {hasil, yakin, jenis} dari faq_cari. Keputusannya diambil server.
    function tampilHasil(d, teks) {
        if (d.jenis === "sapaan") {
            gelembung("bot", "Halo! Ada yang bisa saya bantu?");
            muatKategori();
            return;
        }
        if (d.jenis === "terima_kasih") {
            gelembung("bot", "Sama-sama! Semoga membantu.");
            pilihan([KEMBALI]);
            return;
        }
        if (!d.hasil.length) { tidakAda(teks); return; }
        if (d.yakin) {
            var utama = d.hasil[0];
            gelembung("bot", utama.jawaban, utama.pertanyaan);
            var lain = d.hasil.slice(1);
            if (lain.length) { gelembung("bot", "Pertanyaan terkait:"); }
            pilihan(tombolFaq(lain).concat([KEMBALI]));
            return;
        }
        gelembung("bot", "Maksud Anda…?");
        pilihan(tombolFaq(d.hasil).concat([KEMBALI]));
    }

    function kirim(teks) {
        gelembung("pengguna", teks);
        ambil(akar.dataset.urlCari + "?q=" + encodeURIComponent(teks), function (d) { tampilHasil(d, teks); }, gangguan);
    }

    function buka() {
        jendela.hidden = false;
        tombol.setAttribute("aria-expanded", "true");
        tombol.setAttribute("aria-label", "Tutup tanya jawab");
        if (!sudahSapa) {
            sudahSapa = true;
            gelembung("bot", "Halo! Saya asisten otomatis " + namaBengkel + ". Pilih topik di bawah, atau ketik pertanyaan Anda.");
            muatKategori();
        }
        input.focus();
    }
    function tutup() {
        jendela.hidden = true;
        tombol.setAttribute("aria-expanded", "false");
        tombol.setAttribute("aria-label", "Buka tanya jawab");
        tombol.focus();
    }

    tombol.addEventListener("click", function () { jendela.hidden ? buka() : tutup(); });
    akar.querySelector(".faq-tutup").addEventListener("click", tutup);
    jendela.addEventListener("keydown", function (e) { if (e.key === "Escape") tutup(); });
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var teks = input.value.trim();
        if (!teks) return;
        input.value = "";
        kirim(teks);
    });
})();
