"""
Apply Windows compatibility patches to the installed sam3 package.

Run this after every `pip install git+https://github.com/facebookresearch/sam3.git`
or any sam3 reinstall. patch_sam3.bat calls this automatically.

Current patches
---------------
sam3/model/edt.py
    triton has no Windows wheels. The patched file guards the import with
    try/except and falls back to cv2.distanceTransform, which is semantically
    identical (the sam3 docstring says the function is equivalent to a batched
    cv2.distanceTransform(input, cv2.DIST_L2, 0)).
"""

import os
import shutil
import site
import sys

PATCHES = [
    # (source file in patches/, target relative path inside sam3 package)
    ("sam3_edt_windows.py", os.path.join("sam3", "model", "edt.py")),
]

PATCHES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patches")


def find_sam3_site_package() -> str | None:
    for sp in site.getsitepackages():
        if os.path.isdir(os.path.join(sp, "sam3")):
            return sp
    return None


def apply_patches(site_pkg: str) -> int:
    errors = 0
    for src_name, rel_target in PATCHES:
        src = os.path.join(PATCHES_DIR, src_name)
        target = os.path.join(site_pkg, rel_target)

        if not os.path.exists(src):
            print(f"  SKIP  {rel_target}  (patch source not found: {src})")
            errors += 1
            continue

        if not os.path.exists(target):
            print(f"  SKIP  {rel_target}  (target not found — sam3 installed differently?)")
            errors += 1
            continue

        shutil.copy2(src, target)
        print(f"  OK    {rel_target}")

    return errors


def main() -> int:
    print("ArtSegment — applying SAM3 Windows patches")
    print()

    site_pkg = find_sam3_site_package()
    if site_pkg is None:
        print("ERROR: sam3 package not found in any site-packages directory.")
        print("Install sam3 first:")
        print("  pip install git+https://github.com/facebookresearch/sam3.git")
        return 1

    print(f"Found sam3 in: {site_pkg}")
    errors = apply_patches(site_pkg)

    print()
    if errors:
        print(f"Finished with {errors} error(s).")
        return 1

    print("All patches applied successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
