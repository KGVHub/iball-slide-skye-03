import os
root = "/home/kgvarunkanth/claude/kernel"
fixed = []
for dp, dn, fn in os.walk(root):
    if "/.git" in dp:
        continue
    for name in fn:
        p = os.path.join(dp, name)
        try:
            if os.path.islink(p):
                continue
            st = os.lstat(p)
            if st.st_size == 0 or st.st_size > 256:
                continue
            with open(p, "rb") as f:
                data = f.read()
        except OSError:
            continue
        # must be a single-line path-looking string
        if b"\n" in data.rstrip(b"\n"):
            continue
        s = data.decode("utf-8", "replace").strip()
        if not s or " " in s or "\t" in s:
            continue
        if not (s.startswith("./") or s.startswith("../") or s.startswith("/")):
            continue
        target = s if s.startswith("/") else os.path.normpath(os.path.join(dp, s))
        if not os.path.exists(target):
            continue
        # looks like a symlink stored as a file -> restore
        os.remove(p)
        os.symlink(s, p)
        fixed.append((os.path.relpath(p, root), s))
for r, s in fixed:
    print(f"{r} -> {s}")
print(f"\nTotal restored: {len(fixed)}")
