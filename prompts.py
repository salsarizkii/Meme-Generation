# ============================================================
# LANGUAGE CONFIGURATION
# ============================================================
# Pilih bahasa: "id" untuk Indonesia, "en" untuk English
DEFAULT_LANGUAGE = "id"

# ============================================================
# DESCRIBE IMAGE PROMPT
# ============================================================
DESCRIBE_IMAGE_PROMPT = {
    "id": """Deskripsikan template meme ini dalam 3–5 kalimat yang padat dan berguna:

1. Siapa atau apa yang ada di gambar? 
2. Apa ekspresi wajah dan bahasa tubuh utamanya? (contoh: pasrah, panik, sombong, bengong, frustrasi)
3. Apa mood atau emosi dominan dari gambar ini secara keseluruhan? (contoh: sedih, marah, bahagia)
4. Situasi kehidupan nyata apa yang paling cocok digambarkan dengan template ini?

Jangan bertele-tele. Fokus pada detail yang berguna untuk membuat caption meme.""",
    "en": """Describe this meme template in 3–5 concise and useful sentences:

1. Who or what is in the image?
2. What is the main facial expression and body language? (example: resigned, panicked, smug, blank, frustrated)
3. What is the dominant mood or emotion of the image overall? (example: sad, angry, happy)
4. What real-life situation is most suitable for this template?

Do not ramble. Focus on details that are useful for writing meme captions."""
}

# ============================================================
# GENERATE FINAL CAPTION PROMPT (FEW-SHOT)
# ============================================================
GENERATE_FINAL_CAPTION_PROMPT = {
    "id": {
        "single_box": """Kamu kreator meme mahasiswa Indonesia yang jago bikin caption viral.
Template: {description}

TOPIK: {topic}

CONTOH CAPTION (pelajari pola humor dan gaya bahasanya):
{fewshot_block}

TUGAS: Buat SATU caption meme (satu kalimat, tanpa ||).

PANDUAN:
- Cocokkan ekspresi/mood gambar dengan tone caption
- Caption harus MEMPERKUAT mood gambar, bukan sekadar mendeskripsikan ulang gambarnya
- Boleh pakai detail visual kalau membantu, tapi tidak wajib
- Spesifik pada topik: senggol situasi nyata mahasiswa, bukan klise generik
- Utamakan detail konkret (jam, angka, konteks kejadian), bukan kata abstrak umum
- Singkat dan langsung kena: maks 8 kata, kalimat utuh
- Bahasa gaul/santai, jangan formal
- Prioritaskan yang relatable dan punya kejutan kecil di ujung kalimat

TEKNIK HUMOR (pilih yang paling pas dengan gambar):
- Ironi pahit: ekspektasi mulia vs. realita memalukan  → "niat produktif, ketiduran jam 4 sore"
- Hiperbola relatable: dramatisasi hal kecil yang terasa besar  → "revisi titik-koma, begadang semalam"
- Self-sabotage: diri sendiri jadi musuh  → "niat cicil seminggu, kelar semalam"
- Deadpan twist: dua hal yang gak nyambung tapi justru kena  → "ini gampang, tapi yang ngomong dosen" (katanya doang padahal mah susah)

LARANGAN:
- Format label ("Dosen: ...", "Gue: ...")
- Kata "saya"/"anda"
- Jangan gunakan kata "PR" (pakai "tugas")
- Kalimat terpotong
OUTPUT: HANYA satu baris caption, tanpa penjelasan.

Caption:""",
        "multi_box": """Kamu kreator meme mahasiswa Indonesia yang jago bikin caption viral.
Template: {description}

TOPIK: {topic}

CONTOH CAPTION (pelajari struktur setup→punchline-nya):
{fewshot_block}

TUGAS: Buat SATU caption dengan {box_count} box, format SATU BARIS:
teks1 || teks2 || ... || teks{box_count}

KETENTUAN:
- 1–7 kata per box, bahasa gaul/santai
- Jangan gunakan kata "saya"/"anda"
- Caption harus MEMPERKUAT mood gambar — bukan mendeskripsikan ulang gambarnya
- Boleh pakai detail visual kalau relevan, tapi tidak wajib
- Box pertama = setup konteks, box terakhir = punchline yang lebih nyesek/ironis
- Utamakan situasi yang sering kejadian di kehidupan mahasiswa

TEKNIK HUMOR (pilih yang paling pas dengan gambar):
- Setup mulia → punchline memalukan  → "bimbingan besok || baru buka file"
- Kontras waktu spesifik  → "deadline jam 2 || mulai jam 1"
- Kesamaan nasib ironis  → "minta jawaban temen || temen juga nebak"
- Deadpan ironis  → "ini gampang || yang ngomong dosen" (katanya doang padahal mah susah)

LARANGAN: Format label, kata "saya"/"anda", dan jangan gunakan kata "PR" (pakai "tugas").
OUTPUT: HANYA satu baris dengan pemisah ||, tanpa penjelasan.

Caption:"""
    },
    "en": {
        "single_box": """You are an Indonesian college meme creator who is great at making viral captions.
Template: {description}

TOPIC: {topic}

    EXAMPLE CAPTIONS (study the humor pattern and language style):
{fewshot_block}

TASK: Create ONE meme caption (single sentence, no ||).

GUIDELINES:
- Match the image's expression/mood to the caption tone
- Caption must REINFORCE the image mood, not only restate the visual
    - Visual details are optional if helpful, not required
    - Be specific to the topic: reference real student situations, avoid generic cliches
    - Prioritize concrete details (time, numbers, event context), avoid abstract generic wording
- Short and punchy: max 8 words, complete sentence
    - Use casual/slang Indonesian, not formal
    - Prioritize relatability and a small surprise at the end of the sentence

    HUMOR TECHNIQUE (pick what best fits the image):
    - Bitter irony: noble expectation vs embarrassing reality  -> "planned to be productive, slept at 4 PM"
    - Relatable hyperbole: dramatize small things that feel huge  -> "revised one comma, up all night"
    - Self-sabotage: yourself becomes your own enemy  -> "planned one week, finished in one night"
    - Deadpan twist: two mismatched things that unexpectedly hit  -> "this is easy, said the lecturer" (only words, reality says otherwise)

FORBIDDEN:
- Label formats ("Lecturer: ...", "Me: ...")
- Words "saya" and "anda"
- Do not use the word "PR"; use "tugas"
- Cut-off sentences
    - Overused generic phrases
    OUTPUT: ONLY one caption line, no explanation.

Caption:""",
        "multi_box": """You are an Indonesian college meme creator who is great at making viral captions.
Template: {description}

TOPIC: {topic}

    EXAMPLE CAPTIONS (study the setup->punchline structure):
{fewshot_block}

TASK: Create ONE caption with {box_count} boxes in ONE LINE:
text1 || text2 || ... || text{box_count}

REQUIREMENTS:
    - 1-7 words per box, casual/slang Indonesian
    - Do not use words "saya"/"anda"
- Caption must REINFORCE the image mood, not only restate the visual
    - Visual details are optional if relevant, not required
    - First box = setup context, last box = more painful/ironic punchline
    - Prioritize situations that often happen in student life

    HUMOR TECHNIQUE (pick what best fits the image):
    - Noble setup -> embarrassing punchline  -> "supervision tomorrow || just opened file"
    - Specific time contrast  -> "deadline at 2 || started at 1"
    - Shared ironic fate  -> "asked friend for answers || friend also guessed"
    - Deadpan irony  -> "this is easy || said by lecturer" (only words, reality says otherwise)

    FORBIDDEN: Label formats, words "saya"/"anda", and do not use word "PR" (use "tugas").
    OUTPUT: ONLY one line with || separator, no explanation.

Caption:"""
    }
}

# ============================================================
# GENERATE ZEROSHOT CAPTION PROMPT
# ============================================================
GENERATE_ZEROSHOT_CAPTION_PROMPT = {
    "id": {
        "single_box": """Kamu kreator meme mahasiswa Indonesia yang jago bikin caption viral.
Buat SATU caption meme berdasarkan info berikut:

TOPIK: {topic}
DESKRIPSI GAMBAR: "{description}"

PANDUAN:
- Cocokkan ekspresi/mood gambar dengan tone caption
- Caption harus MEMPERKUAT mood gambar — bukan sekadar mendeskripsikan ulang gambarnya
- Spesifik pada topik: sesuaikan situasi nyata mahasiswa
- Utamakan detail konkret (momen, ekspresi)
- Singkat dan langsung kena: maks 8 kata, kalimat utuh
- Bahasa gaul/santai, jangan formal
- Jangan gunakan kata "saya"/"anda"
- Prioritaskan situasi yang relatable dan punchline yang kena

LARANGAN:
- Format label ("Dosen: ...", "Gue: ...")
- Jangan gunakan kata "PR" (pakai "tugas")
- Kalimat terpotong
OUTPUT: HANYA satu baris caption, tanpa penjelasan.""",
        "multi_box": """Kamu kreator meme mahasiswa Indonesia yang jago bikin caption viral.
Buat {box_count} teks meme singkat.
Format SATU BARIS: teks1 || teks2 || ... || teks{box_count}

TOPIK: {topic}
DESKRIPSI GAMBAR: "{description}"

KETENTUAN:
- 1–4 kata per box, bahasa gaul/santai
- Jangan gunakan kata "saya"/"anda"
- Box pertama setup konteks, box terakhir punchline
- Buat setup yang relate dulu, baru tabrak dengan punchline

TEKNIK HUMOR (pilih yang paling pas dengan gambar):
- Setup mulia → punchline memalukan  → "bimbingan besok || baru buka file"
- Kontras waktu spesifik  → "deadline jam 2 || mulai ngerjain jam 1"
- Kesamaan nasib ironis  → "minta jawaban temen || temen juga ngarang"
- Deadpan ironis  → "ini gampang || katanya" (katanya doang padahal mah susah)

LARANGAN: Format label, kata "saya"/"anda", dan jangan gunakan kata "PR" (pakai "tugas").
OUTPUT: HANYA satu baris dengan pemisah ||, tanpa penjelasan."""
    },
    "en": {
        "single_box": """You are an Indonesian college meme creator who is great at making viral captions.
Create ONE meme caption based on:

TOPIC: {topic}
IMAGE DESCRIPTION: "{description}"

GUIDELINES:
- Match the image's expression/mood to the caption tone
- Caption must REINFORCE the image mood, not only restate the visual
    - Be specific to the topic: adapt to real student situations
    - Prioritize concrete details (moment, expression)
- Short and punchy: max 8 words, complete sentence
    - Use casual/slang Indonesian, not formal
    - Do not use words "saya"/"anda"
    - Prioritize relatable situations and a strong punchline

FORBIDDEN:
- Label formats ("Lecturer: ...", "Me: ...")
- Do not use the word "PR"; use "tugas"
- Cut-off sentences
    OUTPUT: ONLY one caption line, no explanation.""",
        "multi_box": """You are an Indonesian college meme creator who is great at making viral captions.
Create {box_count} short meme texts.
ONE LINE format: text1 || text2 || ... || text{box_count}

TOPIC: {topic}
IMAGE DESCRIPTION: "{description}"

STRUCTURE:
- First box = situation/expectation (setup)
- Last box = bitter reality or unexpected twist (punchline)
- Middle box(es) if any = escalation or contrast
Example 3-box: "meeting tomorrow || just opened file || revision added anyway"

REQUIREMENTS:
- 1-4 words per box, casual/slang Indonesian
- Do not use words "saya"/"anda"
- First box setup context, last box punchline
- Build a relatable setup first, then hit with punchline

HUMOR TECHNIQUE (pick what best fits the image):
- Noble setup -> embarrassing punchline  -> "supervision tomorrow || just opened file"
- Specific time contrast  -> "deadline at 2 || started at 1"
- Shared ironic fate  -> "asked friend for answers || friend also guessed"
- Deadpan irony  -> "this is easy || he said" (only words, reality says otherwise)

FORBIDDEN: Label formats, words "saya"/"anda", and do not use word "PR" (use "tugas").
OUTPUT: ONLY one line with || separator, no explanation."""
    }
}

# ============================================================
# FEW-SHOT CAPTIONS PER SUBTOPIC
# Struktur: FEWSHOT_CAPTIONS[topic][language]["single"] -> list caption 1-box
#           FEWSHOT_CAPTIONS[topic][language]["multi"]  -> list caption multi-box (pakai ||)
# ============================================================
FEWSHOT_CAPTIONS = {
    "thesis": {
        "id": {
            "single": [
                {
                    "description": "mahasiswa bengong depan dokumen kosong, gak ada satu kata pun yang keluar",
                    "caption": "ngetik satu kalimat, ngehapus 3 paragraf"
                },
                {
                    "description": "mahasiswa panik buka laptop 10 menit sebelum jadwal bimbingan, file belum dibuka sama sekali",
                    "caption": "bimbingan jam 10, buka file jam 9.57"
                },
                {
                    "description": "mahasiswa membaca ulang kalimat skripsinya sendiri tapi tetap tidak paham maksudnya",
                    "caption": "pov gapaham sama apa yang lo tulis di skripsi"
                },
                {
                    "description": "mahasiswa menemukan satu jurnal yang sangat relevan setelah berjam-jam mencari",
                    "caption": "pov akhirnya nemu jurnal bagus tapi berbayar"
                },
                {
                    "description": "mahasiswa berhasil acc dosen pembimbing 1, langsung ditolak dosen pembimbing 2",
                    "caption": "pov di acc dosen pertama tapi ditolak dosen kedua"
                }
            ],
            "multi": [
                {
                    "description": "mahasiswa burnout menatap layar laptop malam hari, skripsi gak maju-maju",
                    "caption": "skripsi jalan || mental tertinggal"
                },
                {
                    "description": "mahasiswa buka laptop mau bimbingan, padahal baru buka file-nya sekarang",
                    "caption": "bimbingan besok || baru buka file"
                },
                {
                    "description": "dosen kasih revisi satu tanda baca, mahasiswa begadang semalam",
                    "caption": "cuma revisi titik-koma || begadangnya semaleman"
                },
                {
                    "description": "mahasiswa pasrah menatap dokumen kosong, buntu total nulis bab skripsi",
                    "caption": "judul ada || isinya gaada"
                },
                {
                    "description": "mahasiswa acc dosen 1, langsung ditolak dosen 2",
                    "caption": "acc dosen 1 || ditolak dosen 2"
                }
            ]
        },
        "en": {
            "single": [
                {
                    "description": "student staring at a blank document, not a single word comes out",
                    "caption": "typed one sentence, deleted three paragraphs"
                },
                {
                    "description": "student panicking, opening a laptop 10 minutes before supervision, file still untouched",
                    "caption": "meeting at 10, opened file at 9:57"
                },
                {
                    "description": "student rereading their own thesis sentence but still not understanding it",
                    "caption": "POV: not understanding your own thesis writing"
                },
                {
                    "description": "student finally found a very relevant journal after searching for hours",
                    "caption": "POV: finally found a great paper, but paywalled"
                },
                {
                    "description": "first advisor approved it, then second advisor rejected it",
                    "caption": "POV: approved by advisor one, rejected by advisor two"
                }
            ],
            "multi": [
                {
                    "description": "burned-out student staring at laptop at night, thesis not moving",
                    "caption": "thesis moves || mental left behind"
                },
                {
                    "description": "student opening laptop for supervision, but only opening the file now",
                    "caption": "meeting tomorrow || just opened file"
                },
                {
                    "description": "advisor gave one punctuation revision, student stayed up all night",
                    "caption": "just one comma fix || stayed up all night"
                },
                {
                    "description": "student staring at an empty document, fully stuck writing thesis chapter",
                    "caption": "title exists || content missing"
                },
                {
                    "description": "advisor one approved it, then advisor two rejected it",
                    "caption": "advisor one approved || advisor two rejected"
                }
            ]
        }
    },
    "lecturer": {
        "id": {
            "single": [
                {
                    "description": "dosen senyum tenang bilang 'ini gampang' di depan kelas, padahal materinya susah banget",
                    "caption": "pov dosen bilang ini gampang padahal rumusnya kaya bahasa alien"
                },
                {
                    "description": "mahasiswa sedang bersiap berangkat kuliah lalu tiba-tiba membaca pesan bahwa kelas dibatalkan",
                    "caption": "udah di jalan, kelas batal"
                },
                {
                    "description": "mahasiswa nanya satu pertanyaan ke dosen, malah dapat dua tugas tambahan",
                    "caption": "nanya satu hal, dapat dua tugas"
                },
                {
                    "description": "mahasiswa duduk di kelas dengan mata setengah tertutup mencoba tetap terlihat memperhatikan",
                    "caption": "fisik di kelas tapi jiwa di kasur"
                },
                {
                    "description": "orang berlari dengan cepat sampai terengah engah seperti mengejar sesuatu yang sangat penting",
                    "caption": "ada kuis tapi kamu telat"
                },
            ],
            "multi": [
                {
                    "description": "mahasiswa baru saja sampai kelas ketika dosen tiba-tiba mengumumkan kuis",
                    "caption": "baru sampe kelas || langsung kuis dadakan"
                },
                {
                    "description": "mahasiswa bengong menatap papan tulis penuh rumus, gak nangkep sama sekali",
                    "caption": "presensi masuk || materi ga masuk"
                },
                {
                    "description": "mahasiswa ngantuk berat kuliah pagi, badan hadir tapi otak entah kemana",
                    "caption": "otak offline || badan online"
                },
                {
                    "description": "mahasiswa bengong melihat papan tulis penuh rumus yang tidak dipahami sama sekali",
                    "caption": "papan tulis penuh || otak kosong"
                },
                {
                    "description": "mahasiswa ngantuk berat di kuliah pagi sambil mencoba tetap membuka mata",
                    "caption": "fisik di kelas || jiwa di kasur"
                }
            ]
        },
        "en": {
            "single": [
                {
                    "description": "lecturer smiles calmly and says 'this is easy', but the material is very hard",
                    "caption": "POV: lecturer says easy, formula looks alien"
                },
                {
                    "description": "student getting ready for class, then suddenly reading a message that class is canceled",
                    "caption": "already on the way, class canceled"
                },
                {
                    "description": "student asks one question to lecturer, then gets two extra assignments",
                    "caption": "asked one thing, got two assignments"
                },
                {
                    "description": "student sitting in class with half-closed eyes, trying to look attentive",
                    "caption": "body in class, soul in bed"
                },
                {
                    "description": "someone running fast and out of breath like chasing something urgent",
                    "caption": "there's a quiz and you're late"
                }
            ],
            "multi": [
                {
                    "description": "student just arrived in class, then lecturer suddenly announces a quiz",
                    "caption": "just arrived in class || surprise quiz"
                },
                {
                    "description": "student staring blankly at a whiteboard full of formulas, understanding nothing",
                    "caption": "attendance marked || lesson not absorbed"
                },
                {
                    "description": "student extremely sleepy in morning lecture, body present but mind elsewhere",
                    "caption": "brain offline || body online"
                },
                {
                    "description": "student staring at a board full of formulas that make no sense at all",
                    "caption": "board full || brain empty"
                },
                {
                    "description": "student very sleepy in morning class while trying to keep eyes open",
                    "caption": "body in class || soul in bed"
                }
            ]
        }
    },
    "assignment": {
        "id": {
            "single": [
                {
                    "description": "mahasiswa panik lihat jam, deadline 15 menit lagi tapi baru setengah jalan",
                    "caption": "deadlinenya 15 menit tapi baru dapet setengahnya"
                },
                {
                    "description": "mahasiswa begadang semalaman di depan laptop mengerjakan tugas yang sudah lama ditunda",
                    "caption": "ngerjain tugas dengan deadline seminggu dalam 1 malam"
                },
                {
                    "description": "mahasiswa baca instruksi tugas tapi tiap kalimat bikin lebih bingung dari sebelumnya",
                    "caption": "ketika baca instruksi tugas yang muter-muter"
                },
                {
                    "description": "kerja kelompok, chat grup rame ribuan pesan, tapi cuma satu orang yang ngerjain semua",
                    "caption": "ketika kerja kelompok tapi yang ngerjain gue doang"
                },
                {
                    "description": "mahasiswa kumpulin tugas tanpa sempat baca ulang, baru sadar ada yang salah sesudah submit",
                    "caption": "pov habis submit baru sadar ada yang salah"
                }
            ],
            "multi": [
                {
                    "description": "mahasiswa panik lihat deadline tugas, baru mulai mendekati deadline",
                    "caption": "deadline jam 2 || mulai jam 1.45"
                },
                {
                    "description": "chat grup kelompok ribuan pesan, tapi cuma satu orang yang ngerjain",
                    "caption": "kerja kelompok rame rame || yang ngerjain gue doang"
                },
                {
                    "description": "mahasiswa niat cicil awal, submit detik-detik terakhir juga",
                    "caption": "niat nyicil ngerjain || submit tetep jam 11.59"
                },
                {
                    "description": "mahasiswa membuka dokumen tugas yang baru setengah jadi saat waktu submit hampir tiba",
                    "caption": "deadline bentar lagi || ide belum lahir"
                },
                {
                    "description": "mahasiswa menekan tombol submit tugas lalu beberapa detik kemudian terlihat panik",
                    "caption": "klik tombol submit || baru sadar ada yang salah"
                }
            ]
        },
        "en": {
            "single": [
                {
                    "description": "student panics seeing the clock, 15 minutes left but assignment only halfway done",
                    "caption": "15 minutes to deadline, only halfway done"
                },
                {
                    "description": "student pulling an all-nighter to finish a task postponed for too long",
                    "caption": "one-week deadline done in one night"
                },
                {
                    "description": "student reads assignment instructions, each sentence gets more confusing",
                    "caption": "when assignment instructions go in circles"
                },
                {
                    "description": "group project chat has thousands of messages, but only one person does all the work",
                    "caption": "group project, but I did it all"
                },
                {
                    "description": "student submits without rereading, then realizes a mistake right after submit",
                    "caption": "POV: saw the mistake right after submit"
                }
            ],
            "multi": [
                {
                    "description": "student panics at assignment deadline and only starts very late",
                    "caption": "deadline at 2 || started at 1:45"
                },
                {
                    "description": "group chat has thousands of messages, but only one person did the work",
                    "caption": "group chat is crowded || I did all the work"
                },
                {
                    "description": "student planned to work gradually, still submitted at the last second",
                    "caption": "planned to pace it || still submitted at 11:59"
                },
                {
                    "description": "student opens an assignment file that's still half-done while submission time is near",
                    "caption": "deadline is close || idea not born yet"
                },
                {
                    "description": "student presses submit, then panics a few seconds later",
                    "caption": "clicked submit || then noticed a mistake"
                }
            ]
        }
    }
}