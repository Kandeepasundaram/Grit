"""Generate RSA key pair for Grit license JWT signing.

Run once during backend setup:
    python scripts/generate_license_keys.py

Outputs:
  - backend/license_private.pem  (keep secret — used by server to sign JWTs)
  - src/grit/cloud/license_public.pem  (bundled with client — used to verify JWTs)
"""

from __future__ import annotations

from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Install cryptography first:  pip install cryptography")
    raise SystemExit(1)

HERE = Path(__file__).parent.parent

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

private_pem = key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
public_pem = key.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
)

private_path = HERE / "backend" / "license_private.pem"
public_path = HERE / "src" / "grit" / "cloud" / "license_public.pem"

private_path.parent.mkdir(parents=True, exist_ok=True)
private_path.write_bytes(private_pem)
print(f"Private key written to: {private_path}")

public_path.parent.mkdir(parents=True, exist_ok=True)
public_path.write_bytes(public_pem)
print(f"Public key written to:  {public_path}")
print()
print("Add backend/license_private.pem to .gitignore — never commit the private key!")
