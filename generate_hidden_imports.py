# Copyright (c) 2026 Jeff Nedley
# Licensed under the MIT License (see LICENSE for details)

with open('requirements.txt', 'r') as f:
    packages = [line.strip().split('==')[0].split('>=')[0].split('<=')[0] for line in f if line.strip() and not line.startswith('#')]

for pkg in packages:
    print(f"--hidden-import {pkg}")