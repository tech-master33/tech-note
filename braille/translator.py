try:
    import louis
    HAS_LOUIS = True
except ImportError:
    HAS_LOUIS = False

_grade = 2

def set_grade(grade):
    global _grade
    _grade = grade

def get_grade():
    return _grade

TABLE = {
    1: "en-us-g1.ctb",
    2: "en-us-g2.ctb",
}

def translate(text):
    if not HAS_LOUIS or not text:
        return text
    try:
        table = TABLE.get(_grade, "en-us-g2.ctb")
        result, _ = louis.translate([table], text, typeform=None, mode=0)
        return result
    except Exception:
        return text

def back_translate(keys):
    if not HAS_LOUIS or not keys:
        return keys
    try:
        table = TABLE.get(_grade, "en-us-g2.ctb")
        result, _ = louis.backTranslate([table], keys)
        return result
    except Exception:
        return keys
