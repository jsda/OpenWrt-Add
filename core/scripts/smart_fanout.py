#!/usr/bin/env python3
"""Route APK packages to the aarch64_cortex-a53 and x86_64 targets only."""
import argparse
import os
import re
import shutil
import sys
import tarfile
import zlib

AARCH64_TARGET = 'aarch64_cortex-a53'
TARGETS = (AARCH64_TARGET, 'x86_64')

ARCH_RE = re.compile(
    r'(aarch64_cortex-a\d+|aarch64_generic|aarch64|x86_64|i386_pentium4|'
    r'arm_cortex-a\d+[a-z0-9_]*|mipsel_[a-z0-9_]+|mips_24kc|'
    r'riscv64_generic|_all(?=\.apk$)|-all-)'
)
ARCH_V3_RE = re.compile(
    rb'\b(aarch64_cortex-a\d+|aarch64_generic|aarch64|x86_64|'
    rb'i386_pentium4|arm_cortex-a\d+[a-z0-9_]*|mipsel_[a-z0-9_]+|'
    rb'mips_24kc|riscv64_generic|noarch|all)\b'
)


def normalize_arch(arch):
    """Normalize architecture-independent and generic AArch64 labels."""
    if arch in ('all', 'noarch'):
        return 'all'
    if arch in ('aarch64', 'aarch64_generic'):
        return 'aarch64_generic'
    return arch


def get_apk_arch(path):
    """Determine target architecture from APK v3 header, .PKGINFO, or path."""
    # 1. Try APK v3 (ADB format).
    try:
        with open(path, 'rb') as f:
            data = f.read(4096)
        if data.startswith(b'ADBd'):
            decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
            decompressed = decompressor.decompress(data[4:4096])
            match = ARCH_V3_RE.search(decompressed[:1024])
            if match:
                return normalize_arch(match.group(1).decode('ascii'))
    except Exception:
        pass

    # 2. Try APK v2 (.PKGINFO in tar/tar.gz).
    try:
        with tarfile.open(path, 'r:*') as archive:
            for member in archive.getmembers():
                if member.name in ('.PKGINFO', 'PKGINFO'):
                    content = archive.extractfile(member)
                    if content:
                        for line in content.read().decode(
                            'utf-8', errors='ignore'
                        ).splitlines():
                            if line.startswith('arch ='):
                                return normalize_arch(
                                    line.split('=', 1)[1].strip()
                                )
    except Exception:
        pass

    # 3. Infer architecture from the parent directory or filename.
    match = ARCH_RE.search(path)
    if match:
        arch = match.group(1)
        if arch in ('_all', '-all-'):
            return 'all'
        return normalize_arch(arch)

    # LuCI and translation packages are architecture-independent.
    name = os.path.basename(path)
    if name.startswith(('luci-', 'translations-')):
        return 'all'

    return None


def copy_to_target(source, output_dir, target, filename):
    target_dir = os.path.join(output_dir, target)
    os.makedirs(target_dir, exist_ok=True)
    destination = os.path.join(target_dir, filename)
    shutil.copy2(source, destination)


def main():
    parser = argparse.ArgumentParser(
        description='Fan out APKs to aarch64_cortex-a53 and x86_64 only.'
    )
    parser.add_argument('src')
    parser.add_argument('out')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    apks = [
        os.path.join(root, filename)
        for root, _, files in os.walk(args.src)
        for filename in files
        if filename.endswith('.apk')
    ]
    if not apks:
        print('[WARN] no apk found in ' + args.src)
        return 0

    for target in TARGETS:
        os.makedirs(os.path.join(args.out, target), exist_ok=True)

    copied = 0
    skipped = 0
    for apk in apks:
        filename = os.path.basename(apk)
        arch = get_apk_arch(apk)

        if arch is None or arch == 'all':
            # Architecture-independent package: publish to both targets.
            for target in TARGETS:
                copy_to_target(apk, args.out, target, filename)
            print('  [all] ' + filename)
            copied += 1
        elif arch in ('aarch64_generic', 'aarch64', AARCH64_TARGET):
            # Generic AArch64 and a53 packages are published to a53 only.
            copy_to_target(apk, args.out, AARCH64_TARGET, filename)
            print('  [aarch64_cortex-a53] ' + filename)
            copied += 1
        elif arch == 'x86_64':
            copy_to_target(apk, args.out, 'x86_64', filename)
            print('  [x86_64] ' + filename)
            copied += 1
        else:
            # Never create extra architecture directories in the public feed.
            print('  [skip:%s] %s' % (arch, filename))
            skipped += 1

    print(
        '[INFO] Smart fan-out completed: %d copied, %d skipped, %d input APKs'
        % (copied, skipped, len(apks))
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
