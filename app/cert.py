"""HTTPS-certificaten voor de lokale PWA (nodig om de app op Android te installeren).

Android/Chrome staat een installeerbare PWA + service worker alleen toe op een
'secure context': HTTPS of localhost. Over http://<lan-ip>:5001 werkt dat dus niet.

Deze module genereert een kleine lokale root-CA + een servercertificaat waarin
alle LAN-IP's van dit apparaat staan. Je installeert de root-CA (rootCA.pem)
éénmalig op de telefoon; daarna vertrouwt Android https://<dit-ip>:5001 en kun je
de app als echte app op het beginscherm zetten.

Verandert het IP van het apparaat (bv. nieuwe DHCP-lease), dan wordt alleen het
servercertificaat opnieuw gemaakt — de CA blijft hetzelfde, dus je hoeft niets
opnieuw op de telefoon te installeren.
"""
import os
import socket
import ipaddress
import datetime

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _local_ipv4s():
    """Verzamelt alle bruikbare IPv4-adressen van dit apparaat."""
    ips = set()

    # Adressen die bij de hostnaam horen
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ips.add(info[4][0])
    except Exception:
        pass

    # Het 'uitgaande' LAN-IP (werkt ook als de hostnaam niets oplevert)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass

    v4 = set()
    for ip in ips:
        try:
            if isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address):
                v4.add(ip)
        except ValueError:
            pass
    v4.add("127.0.0.1")
    return sorted(v4)


def _build_ca():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AgLoadMonitor Lokale CA")])
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))  # 10 jaar
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                key_encipherment=False, content_commitment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _build_server(ca_key, ca_cert, ips):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    san = [x509.DNSName("localhost")]
    try:
        san.append(x509.DNSName(socket.gethostname()))
    except Exception:
        pass
    for ip in ips:
        san.append(x509.IPAddress(ipaddress.ip_address(ip)))

    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AgLoadMonitor")]))
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        # Mobiele browsers accepteren leaf-certificaten van max ~825 dagen
        .not_valid_after(now + datetime.timedelta(days=820))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return key, cert


def _write_key(path, key):
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))


def _write_cert(path, cert):
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def _load_key(path):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_cert(path):
    with open(path, "rb") as f:
        return x509.load_pem_x509_certificate(f.read())


def _cert_covers_ips(cert_path, ips):
    """True als het bestaande servercertificaat alle huidige IP's al dekt."""
    try:
        cert = _load_cert(cert_path)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        cert_ips = {str(ip) for ip in san.get_values_for_type(x509.IPAddress)}
        return all(ip in cert_ips for ip in ips)
    except Exception:
        return False


def ensure_certificates(cert_dir):
    """Zorgt dat er een geldige (CA + server) certificaatset is in cert_dir.

    Returnt (server_cert_pad, server_key_pad, root_ca_pad).
    """
    os.makedirs(cert_dir, exist_ok=True)
    ca_cert_p = os.path.join(cert_dir, "rootCA.pem")
    ca_key_p = os.path.join(cert_dir, "rootCA.key")
    srv_cert_p = os.path.join(cert_dir, "server.crt")
    srv_key_p = os.path.join(cert_dir, "server.key")

    ips = _local_ipv4s()

    have_all = all(os.path.exists(p) for p in (ca_cert_p, ca_key_p, srv_cert_p, srv_key_p))
    if have_all and _cert_covers_ips(srv_cert_p, ips):
        return srv_cert_p, srv_key_p, ca_cert_p

    if have_all:
        print("ℹ️ Netwerk-IP gewijzigd — servercertificaat opnieuw genereren (CA blijft hetzelfde)...")

    # CA hergebruiken indien aanwezig, zodat je 'm niet opnieuw op de telefoon hoeft te zetten
    if os.path.exists(ca_cert_p) and os.path.exists(ca_key_p):
        ca_key = _load_key(ca_key_p)
        ca_cert = _load_cert(ca_cert_p)
    else:
        ca_key, ca_cert = _build_ca()
        _write_key(ca_key_p, ca_key)
        _write_cert(ca_cert_p, ca_cert)

    srv_key, srv_cert = _build_server(ca_key, ca_cert, ips)
    _write_key(srv_key_p, srv_key)
    _write_cert(srv_cert_p, srv_cert)

    print(f"✅ HTTPS-certificaat gegenereerd voor IP's: {', '.join(ips)}")
    print(f"   ➜ Installeer de CA op je telefoon via http(s)://<dit-ip>:5001/rootCA.pem")
    return srv_cert_p, srv_key_p, ca_cert_p
