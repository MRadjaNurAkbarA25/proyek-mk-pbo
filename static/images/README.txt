Taruh gambar hasil export Figma di folder ini dengan NAMA PERSIS seperti di bawah.
Kalau file belum ada, halaman tetap tampil (pakai warna abu/gradasi sebagai pengganti).

hero.jpg    -> foto latar bagian paling atas landing page   (lebar sekitar 1600px)
about.jpg   -> foto di bagian "Bagaimana Kami Membantu Anda" (sekitar 800 x 600)
alasan.jpg  -> foto di sisi "Alasan Memilih Kami"            (sekitar 800 x 800)
login.jpg   -> foto di sisi kiri halaman login & register     (sekitar 800 x 900)

Cara export di Figma: pilih frame/gambar -> panel Export (kanan bawah) -> JPG/PNG -> Export.


================== LOGO (SUDAH ADA, JANGAN DIHAPUS) ==================

Berkas logo di bawah ini sudah terpasang dan sudah dipakai halaman.
Jangan ganti namanya, karena nama inilah yang ditulis di CSS.

logo.png              Logo persegi, roda gigi abu + cincin merah, latar tembus
                      pandang. Inilah yang tampil di navbar landing, sidebar
                      semua role, dan halaman login. Dipanggil dari
                      static/css/main.css pada aturan .brand-logo.

logo-terang.png       Sama persis, tapi roda giginya putih. Khusus untuk latar
                      gelap, saat ini hanya dipakai di footer landing page
                      (static/css/landing.css, aturan .brand-terang .brand-logo).

logo-penuh.png        Logo mendatar: mark + tulisan BENGKEL SIAGA di sebelahnya.
logo-penuh-terang.png Versi tulisan untuk latar gelap.
                      Dua berkas ini BELUM dipakai halaman mana pun. Disediakan
                      untuk kop surat, slide presentasi, spanduk, dan nota cetak.

favicon.ico           Ikon tab browser (16/32/48 px dalam satu berkas).
apple-touch-icon.png  Ikon saat halaman disimpan ke layar utama HP (180 px).
                      Keduanya dipanggil dari bagian <head> tiap kerangka
                      halaman.

*.svg                 Versi vektor dari tiap berkas di atas. Ini "master"-nya:
                      tidak pecah diperbesar sampai ukuran apa pun. Pakai yang
                      .svg kalau perlu mencetak besar atau mengubah logonya;
                      yang .png tinggal hasil ekspornya.

Warna resmi logo:
    merah  #d02f3b   (sama persis dengan --merah di static/css/main.css)
    abu    #6e6e6e
    putih  #ffffff   (hanya untuk versi latar gelap)
