# Tugas: Buat caption meme singkat dan lucu berdasarkan deskripsi gambar
# tentang kehidupan mahasiswa universitas.
#
# Aturan:
# - Bahasa Indonesia santai
# - Maksimal 10 kata per caption
# - Jangan menjelaskan gambar
# - Fokus punchline
# - Tanpa emoji
# - Satu baris
# - Jika 2 box, pisahkan dengan " || "

# Few-shot caption per subtopic (format: "teks box 1 || teks box 2")
# Untuk box_count=1, di prompt dipakai dengan menggabungkan (replace " || " jadi spasi).
# Tugas: Buat caption meme singkat dan lucu berdasarkan deskripsi gambar
# tentang kehidupan mahasiswa universitas.
#
# Aturan:
# - Bahasa Indonesia santai
# - Maksimal 10 kata per caption
# - Jangan menjelaskan gambar
# - Fokus punchline
# - Tanpa emoji
# - Satu baris
# - Jika 2 box, pisahkan dengan " || "

# Few-shot caption per subtopic dengan deskripsi
FEWSHOT_CAPTIONS = {
    "thesis": [
        {
            "description": "mahasiswa lelah menatap laptop di malam hari, burnout karena skripsi",
            "caption": "skripsi jalan || mental tertinggal"
        },
        {
            "description": "mahasiswa bingung membaca revisi dari chat dosen, stres karena bimbingan skripsi",
            "caption": "revisi dikit || kepikiran seminggu"
        },
        {
            "description": "mahasiswa kosong menatap layar dokumen skripsi, buntu saat nulis skripsi",
            "caption": "judul ada || isinya belum"
        },
        {
            "description": "mahasiswa panik melihat kalender di kamar, cemas karena deadline sidang",
            "caption": "sidang dekat || revisi jauh"
        },
        {
            "description": "mahasiswa lelah minum kopi di meja belajar, capek karena skripsi malam",
            "caption": "kopi habis || skripsi belum"
        }
    ],
    "lecturer": [
        {
            "description": "dosen serius menjelaskan materi di kelas, netral karena kuliah teori",
            "caption": "yang paham || cuma dosennya"
        },
        {
            "description": "mahasiswa bingung menatap papan tulis di kelas, tidak paham karena materi sulit",
            "caption": "datang kuliah || pulang kebingungan"
        },
        {
            "description": "mahasiswa mengantuk menahan mata di kelas pagi, lelah karena kuliah pagi",
            "caption": "otak offline || badan online"
        },
        {
            "description": "dosen tenang berkata santai di kelas, netral karena materi sulit",
            "caption": "ini gampang || katanya"
        },
        {
            "description": "mahasiswa kosong melihat slide di presentasi, bingung karena kuliah online",
            "caption": "slide jalan || otak diam"
        }
    ],
    "assignment": [
        {
            "description": "mahasiswa panik melihat deadline di laptop, stres karena tugas kuliah",
            "caption": "tugas banyak || waktu sedikit"
        },
        {
            "description": "mahasiswa lelah mengerjakan tugas di malam hari, capek karena tugas numpuk",
            "caption": "niat cicil || ketiduran"
        },
        {
            "description": "mahasiswa bingung melihat instruksi di dokumen tugas, ragu karena instruksi tidak jelas",
            "caption": "soalnya ada || maksudnya ga"
        },
        {
            "description": "mahasiswa panik mengetik cepat menjelang deadline, cemas karena tugas mepet",
            "caption": "deadline jam dua || mulai jam satu"
        },
        {
            "description": "mahasiswa lega menutup laptop di malam hari, lega karena tugas selesai",
            "caption": "kumpul dulu || mikir belakangan"
        }
    ]
}

