import hashlib


def generate_id_from_chinese(text: str) -> str:
    
    text = text[:1024]
    text_bytes = text.encode('utf-8')
   
    md5_hash = hashlib.md5(text_bytes)
   
    return md5_hash.hexdigest()