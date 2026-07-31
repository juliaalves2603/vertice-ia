from pathlib import Path
import re

p = Path("backend/app.py")
s = p.read_text(encoding="utf-8")

Path("backend/app_backup_corrigir_business_discovery.py").write_text(s, encoding="utf-8")

old = '''fields = (
        f"business_discovery.username({username})"
        "{id,username,name,profile_picture_url,followers_count,media_count,"
        f"media.limit({limit})"
        "{id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count}}"
    )'''

new = '''fields = (
        f"business_discovery.username({username})"
        "{id,username,name,followers_count,media_count,"
        f"media.limit({limit})"
        "{id,caption,media_type,permalink,timestamp,like_count,comments_count}}"
    )'''

if old in s:
    s = s.replace(old, new)
else:
    print("Trecho exato não encontrado. Tentando correção por regex...")
    s = re.sub(
        r'fields = \([\s\S]*?business_discovery\.username\(\{username\}\)[\s\S]*?\n\s*\)',
        new,
        s,
        count=1
    )

p.write_text(s, encoding="utf-8")
print("Business Discovery simplificado.")
