LABELS = [
    ("ถูกสุด", "green"),
    ("เร็วสุด", "blue"),
    ("ประหยัด", "teal"),
    ("สมดุล", "purple"),
    ("สบาย", "orange"),
    ("พรีเมี่ยม", "gold"),
]

def pick_label(idx: int) -> tuple[str, str]:
    return LABELS[idx % len(LABELS)]
