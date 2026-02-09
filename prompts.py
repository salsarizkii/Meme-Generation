# ============================================================
# LANGUAGE CONFIGURATION
# ============================================================
# Pilih bahasa: "id" untuk Indonesia, "en" untuk English
DEFAULT_LANGUAGE = "id"

# ============================================================
# DESCRIBE IMAGE PROMPT
# ============================================================
DESCRIBE_IMAGE_PROMPT = {
    "id": """Analisis gambar meme template ini secara detail:
        
1. Identifikasi karakter/objek utama:
   - Siapa atau apa yang ada di gambar?
   - Ekspresi wajah dan bahasa tubuh?
   - Posisi dalam frame?

2. Deskripsi visual:
   - Setting/latar belakang
   - Warna dominan
   - Komposisi visual
   - Area yang kosong untuk teks

3. Konteks meme:
   - Mood/emosi yang ditampilkan
   - Potensi konteks humor
   - Dinamika antara elemen visual

Berikan deskripsi objektif minimal 120 kata yang bisa membantu membuat caption meme yang relevan.""",
    "en": """Analyze this meme template image in detail:
        
1. Identify main characters/objects:
   - Who or what is in the image?
   - Facial expressions and body language?
   - Position in the frame?

2. Visual description:
   - Setting/background
   - Dominant colors
   - Visual composition
   - Empty areas for text

3. Meme context:
   - Mood/emotion displayed
   - Potential humor context
   - Dynamics between visual elements

Provide an objective description of at least 120 words that can help create a relevant meme caption."""
}

# ============================================================
# GENERATE FINAL CAPTION PROMPT (FEW-SHOT)
# ============================================================
GENERATE_FINAL_CAPTION_PROMPT = {
    "id": {
        "single_box": """Anda adalah generator caption meme untuk mahasiswa.
Deskripsi template: {description}...

TOPIK: {topic}
FOKUS HUMOR: {focus}

CONTOH CAPTION (FEW-SHOT, SATU BARIS): 
{fewshot_block}

TUGAS: Buat SATU caption meme (satu kalimat saja, tanpa pemisah ||).
KETENTUAN: Sangat singkat (maks 10 kata), lucu/satir, relatable mahasiswa, relevan dengan deskripsi.
OUTPUT: HANYA SATU BARIS caption, tanpa penjelasan.

Caption baru Anda:""",
        "multi_box": """Anda adalah generator caption meme untuk mahasiswa.
Deskripsi template: {description}...

TOPIK: {topic}
FOKUS HUMOR: {focus}

CONTOH CAPTION (FEW-SHOT, 2 BOX): 
{fewshot_block}

TUGAS: Buat SATU caption dengan {box_count} box.
Gabungkan SEMUA teks dalam SATU BARIS dengan format:
teks1 || teks2 || ... || teks{box_count}

KETENTUAN:
- Sangat singkat (1-4 kata per box)
- Lucu/satir/relatable untuk mahasiswa
- Relevan dengan deskripsi template
OUTPUT: HANYA SATU BARIS dengan format di atas, tanpa penjelasan.

Caption baru Anda:"""
    },
    "en": {
        "single_box": """You are a meme caption generator for university students.
Template description: {description}...

TOPIC: {topic}
HUMOR FOCUS: {focus}

EXAMPLE CAPTIONS (FEW-SHOT, SINGLE LINE): 
{fewshot_block}

TASK: Create ONE meme caption (single sentence, no || separator).
REQUIREMENTS: Very short (max 10 words), funny/satirical, relatable students, relevant to the description.
OUTPUT: ONLY ONE LINE caption, without explanation.

Your new caption:""",
        "multi_box": """You are a meme caption generator for university students.
Template description: {description}...

TOPIC: {topic}
HUMOR FOCUS: {focus}

EXAMPLE CAPTIONS (FEW-SHOT, MULTI-BOX): 
{fewshot_block}

TASK: Create ONE caption with {box_count} boxes.
Combine ALL text in ONE LINE with format:
text1 || text2 || ... || text{box_count}

REQUIREMENTS:
- Very short (1-4 words per box)
- Funny/satirical/relatable for students
- Relevant to the template description
OUTPUT: ONLY ONE LINE with format above, without explanation.

Your new caption:"""
    }
}

# ============================================================
# GENERATE ZEROSHOT CAPTION PROMPT
# ============================================================
GENERATE_ZEROSHOT_CAPTION_PROMPT = {
    "id": {
        "single_box": """Anda adalah generator caption meme untuk mahasiswa.
Buat SATU caption meme saja (satu kalimat, tanpa pemisah ||).

Batasan: Sangat singkat (maks 10 kata), lucu/satir/relatable, relevan kehidupan mahasiswa.
Topik: {topic}
Fokus humor: {focus}

Deskripsi gambar: "{description}"

OUTPUT: HANYA SATU BARIS caption, tanpa penjelasan.""",
        "multi_box": """Anda adalah generator caption meme untuk mahasiswa.
Buat {box_count} teks meme singkat.
Gabungkan SEMUA teks dalam SATU BARIS dengan format:
teks1 || teks2 || ... || teks{box_count}

Batasan:
- Sangat singkat (1–4 kata per box)
- Lucu / satir / relatable
- Relevan dengan kehidupan mahasiswa
- OUTPUT HANYA SATU BARIS dengan pemisah '||'

Topik: {topic}
Fokus humor: {focus}

Deskripsi gambar: "{description}" """
    },
    "en": {
        "single_box": """You are a meme caption generator for university students.
Create ONE meme caption (single sentence, no || separator).

Constraints: Very short (max 10 words), funny/satirical/relatable, relevant to student life.
Topic: {topic}
Humor focus: {focus}

Image description: "{description}"

OUTPUT: ONLY ONE LINE caption, without explanation.""",
        "multi_box": """You are a meme caption generator for university students.
Create {box_count} short meme texts.
Combine ALL text in ONE LINE with format:
text1 || text2 || ... || text{box_count}

Constraints:
- Very short (1-4 words per box)
- Funny/satirical/relatable
- Relevant to student life
- OUTPUT ONLY ONE LINE with '||' separator

Topic: {topic}
Humor focus: {focus}

Image description: "{description}" """
    }
}

# ============================================================
# FEW-SHOT CAPTIONS PER SUBTOPIC
# ============================================================
FEWSHOT_CAPTIONS = {
    "thesis": {
        "id": [
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
        "en": [
            {
                "description": "exhausted student staring at laptop at night, burnout because of thesis",
                "caption": "thesis progress || mental lagging behind"
            },
            {
                "description": "confused student reading revisions from lecturer chat, stressed because of thesis guidance",
                "caption": "tiny revision || thinking about it all week"
            },
            {
                "description": "blank student staring at thesis document, stuck while writing thesis",
                "caption": "title exists || content doesn't yet"
            },
            {
                "description": "panicked student looking at calendar in room, worried because of defense deadline",
                "caption": "defense close || revisions far away"
            },
            {
                "description": "tired student drinking coffee at desk, exhausted because of late night thesis",
                "caption": "coffee finished || thesis not yet"
            }
        ]
    },
    "lecturer": {
        "id": [
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
        "en": [
            {
                "description": "serious lecturer explaining material in class, neutral because of theory lecture",
                "caption": "who understands || only the lecturer"
            },
            {
                "description": "confused student staring at whiteboard in class, not understanding because material is hard",
                "caption": "come to class || leave confused"
            },
            {
                "description": "sleepy student struggling to keep eyes open in morning class, tired because of early class",
                "caption": "brain offline || body online"
            },
            {
                "description": "calm lecturer speaking casually in class, neutral because material is hard",
                "caption": "this is easy || he says"
            },
            {
                "description": "blank student looking at slides in presentation, confused because of online class",
                "caption": "slides going || mind silent"
            }
        ]
    },
    "assignment": {
        "id": [
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
        ],
        "en": [
            {
                "description": "panicked student looking at deadline on laptop, stressed because of assignment",
                "caption": "many assignments || little time"
            },
            {
                "description": "tired student working on assignment at night, exhausted because of piled up assignments",
                "caption": "intend to do it gradually || fell asleep"
            },
            {
                "description": "confused student reading instructions in assignment document, doubtful because instructions are unclear",
                "caption": "the problem exists || the meaning doesn't"
            },
            {
                "description": "panicked student typing fast approaching deadline, worried because assignment is tight",
                "caption": "deadline at two || start at one"
            },
            {
                "description": "relieved student closing laptop at night, relieved because assignment is done",
                "caption": "submit first || think later"
            }
        ]
    }
}

