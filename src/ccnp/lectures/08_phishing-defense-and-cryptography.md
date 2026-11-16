# Phishing Defense & Cryptographic Security

> **CCNP Security · SCOR 350-701 v2.0 · Domain 1.0 Security Concepts**
>
> **1.4** Describe the controls used to protect against phishing and social engineering attacks
>
> **1.5** Describe cryptography security components such as hashing, encryption, PKI, SSL, TLS, QUIC, MASQUE, IPsec, NAT-T IPv4 for IPsec, preshared key, certificate-based authorization, and post-quantum cryptography

---

# How to think about this topic

The two halves of this topic belong together. When cryptography holds, attackers stop attacking the math and start attacking **people**: they phish for the password instead of breaking the encryption. And the defenses against phishing are built from cryptography: DKIM is a digital signature, every mail and web gateway relies on TLS, and phishing-resistant MFA is public-key crypto bound to a website's name.

## Four questions for any security protocol

This topic names a lot of protocols, and the exam loves to swap them. Ask these four questions about each one and they stop blurring together:

| Question | Why it separates protocols |
|---|---|
| **What does it protect?** Confidentiality, integrity, authenticity, or a mix | AH authenticates but doesn't encrypt; ESP does both. SPF authorizes a server; DKIM proves the message wasn't changed |
| **At which layer does it work?** | IPsec protects IP packets; TLS protects one application connection; MASQUE tunnels traffic inside HTTP/3 |
| **What does it ride on, and on which port?** | TLS uses TCP 443 for HTTPS; QUIC uses **UDP** 443; IKE uses UDP 500; NAT-T uses UDP 4500; ESP is IP protocol 50 with **no ports at all** |
| **Who proves identity to whom, and how?** | A certificate signed by a CA, a pre-shared key, or a key published in DNS |

The [protocol comparison](#telling-the-protocols-apart) near the end of this topic answers all four for every protocol in one table.

## How SCOR tests this topic

| Style | Example | Answer |
|---|---|---|
| **Match the control to the problem** | "Which DNS record tells receivers what to do when SPF fails?" | **DMARC** |
| **Name the technique** | "Phishing over SMS" | **Smishing** |
| **Pick the key or the direction** | "Lois sends Bob a confidential message. Which key encrypts it?" | **Bob's public key** |
| **Pick the protocol, mode or port** | "An IPsec tunnel breaks when one peer moves behind PAT. What fixes it?" | **NAT-T, UDP 4500** |

---

# Social engineering: what you're defending against

**Social engineering** manipulates **people** into giving up access, information or money. It works because it skips the technical controls: a user who types their password into a fake page has handed it over, however strong the encryption was.

| Technique | What it is | The tell |
|---|---|---|
| **Phishing** | Fraudulent **email** sent widely to trick users | Generic greeting, urgent request, link to a lookalike site |
| **Spear phishing** | Phishing **aimed at one person or team**, using researched details | Names, projects and suppliers the attacker shouldn't know |
| **Whaling** | Spear phishing aimed at **executives** | Board, legal or finance themes |
| **Business email compromise (BEC)** | An email from a real or spoofed **executive or supplier** asking for a payment or a change of bank details | A payment request that bypasses the normal process |
| **Vishing** | Phishing by **voice** call, now including **AI-cloned voices** | "IT support" or "the bank" calling unexpectedly |
| **Smishing** | Phishing by **SMS** or messaging app | A delivery or bank text with a short link |
| **Quishing** | A **QR code** that leads to a phishing page, often on a printed notice or in a PDF | The link is hidden until scanned, often on a phone with weaker protection |
| **Callback phishing** | An email with no link, just a **phone number** to call about a fake invoice | The attacker then talks the victim into installing remote-access software |
| **Pretexting** | An invented scenario that justifies the request | "I'm the new auditor and need…" |
| **Baiting** | A lure such as a **USB drive** left in the car park | Curiosity does the work |
| **Quid pro quo** | Help offered in exchange for access | "I'll fix your laptop if you give me your login" |
| **Watering hole** | Compromising a **website the targets already visit** | No email at all; the trusted site serves the attack |
| **Tailgating / piggybacking** | **Physical**: following someone through a secured door | Not phishing at all, but social engineering in person |
| **MFA fatigue (push bombing)** | Flooding a user with MFA prompts until they approve one | Repeated prompts the user didn't start |

The pattern behind all of them: **urgency, authority, curiosity or fear**, used to stop the victim thinking before they act. Deepfake voice and video, covered in [AI as the attacker's tool](/ccnp-security/attack-threats-vulnerabilities-cia-triad#ai-as-the-attacker-s-tool), make the authority part much more convincing.

---

# Protecting against phishing: five layers

No single control stops phishing, so the defense is **layered**: block what you can, authenticate senders, limit what a stolen login can do, train people, and catch what still gets through.

![Five layers of phishing defense from the inbox outward: email filtering by Cisco Secure Email blocks most messages, SPF, DKIM and DMARC stop spoofing of your own domain, MFA and least privilege limit a stolen password, training and process controls help people spot and report the rest, and DNS security, a secure web gateway, Splunk and Cisco XDR catch what still gets through; each layer lists what it stops and what it misses](img/08/fig-01-phishing-layers.webp)

## Layer 1: email filtering

The **first line of defense** filters mail before it reaches anyone. It blocks or quarantines **spam, phishing and malware**, analyzes **links and attachments** (URL reputation, link rewriting, sandboxing), and filters **outbound** mail too, so a compromised internal account can't spray phishing at customers and partners.

Cisco offers two deployment styles, and the difference is a likely exam point:

| | **Cisco Secure Email Gateway** (formerly the Email Security Appliance, ESA) | **Cisco Secure Email Threat Defense** |
|---|---|---|
| Where it sits | **In the mail path**: your domain's **MX records** point at it, so every inbound message passes through it first | **Beside** the mailbox: connects to the cloud mail platform (Microsoft 365) through its **API** |
| Deployment | On-premises, virtual or Cloud Gateway | Cloud only |
| When it acts | **Before delivery** | Scans as mail arrives and can **remove messages already delivered** (retrospective remediation) |
| Sees internal mail? | Only what's routed through it | Yes, including **internal** mail between users |
| Blueprint | Background for 1.4 | Configured in topic **5.7** |

How the MX approach forces mail through the filter:

```
 Sender's server ── DNS: "MX for example.com?" ──▶ answer: the filtering service
 Sender's server ── SMTP ──▶ Email filter ──▶ your mail system (cloud or on-premises) ──▶ user
```

## Layer 2: SPF, DKIM and DMARC

These three **DNS TXT records** stop attackers sending mail that **claims to come from your domain**. Each does a different job, and the exam tests whether you can tell them apart:

![How a receiving mail server checks a message from example.com: SPF looks up which servers may send for the envelope sender's domain and compares the sending IP; DKIM fetches the public key from the selector record and verifies the message signature; DMARC checks that at least one of them passed and that its domain aligns with the visible From address, then applies the policy of none, quarantine or reject and sends reports back to the domain owner](img/08/fig-02-email-authentication.webp)

| | **SPF** | **DKIM** | **DMARC** |
|---|---|---|---|
| Question it answers | Is this **server** allowed to send for the domain? | Was the message **signed by the domain**, and is it **unchanged**? | Did SPF or DKIM pass **for the domain the user sees**, and what should I do if not? |
| What it checks | The **sending IP** against a list | A **digital signature** in the message header | **Alignment** with the visible **From:** domain, plus **policy** |
| Crypto? | No | **Yes**: private key signs, public key in DNS verifies | No (it uses SPF and DKIM results) |
| DNS record lives at | `example.com` | `selector._domainkey.example.com` | `_dmarc.example.com` |
| Survives forwarding? | **No**: the forwarder's IP isn't listed | **Usually**, if the message isn't modified | Passes if DKIM still passes and aligns |
| Standard | RFC 7208 | RFC 6376 | RFC 7489 |

### SPF: who may send

```
example.com.  TXT  "v=spf1 ip4:198.51.100.25 include:_spf.mailprovider.example -all"
```

| Part | Meaning |
|---|---|
| `v=spf1` | This is an SPF record |
| `ip4:198.51.100.25` | This IP may send mail for the domain |
| `include:_spf.mailprovider.example` | Also allow the servers listed by a **third party** that sends for you (Microsoft 365, a marketing platform). Forget one and its mail fails SPF |
| `-all` | Everything else **fails** |

The ending sets how strict the record is: **`-all`** hard fail, **`~all`** soft fail (accept but mark as suspicious), **`?all`** neutral, and **`+all`** passes everyone, which you should never use. SPF checks the **envelope sender** (the return path), not the **From:** address the user sees, and it allows at most **10 DNS lookups**, so long chains of `include:` can break it.

### DKIM: a signature on the message

The sending server **signs** each message with its **private key** and adds a `DKIM-Signature` header that names the signing domain (`d=`) and a **selector** (`s=`). The receiver fetches the **public key** from `selector._domainkey.domain` and verifies the signature:

```
s1._domainkey.example.com.  TXT  "v=DKIM1; k=rsa; p=MIIBIjANBgkqh..."
```

A valid signature proves the message was **signed by that domain** and **hasn't been altered** since. It's the [digital signature](#asymmetric-cryptography) idea from later in this topic, applied to email: **private key signs, public key verifies**.

### DMARC: alignment, policy and reports

```
_dmarc.example.com.  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; adkim=s; aspf=s"
```

| Part | Meaning |
|---|---|
| `p=` | **Policy** for mail that fails: `none` (monitor only), `quarantine` (to junk) or `reject` (refuse it) |
| `rua=` / `ruf=` | Where to send **aggregate** and **failure** reports: the "reporting" in the name |
| `adkim=` / `aspf=` | **Alignment** mode for DKIM and SPF: `r` relaxed (subdomains match) or `s` strict (exact match) |

**Alignment is the idea that makes DMARC work.** SPF and DKIM each check **some** domain, but not necessarily the one in the **From:** line the user reads. An attacker can pass SPF for their own domain while showing `ceo@example.com` to the victim. DMARC passes only if **SPF or DKIM passes and the domain it passed for matches the From: domain**.

Roll it out in stages: start at **`p=none`** and read the reports to find every legitimate sender, then move to **`quarantine`**, then **`reject`**. Since 2024, Google and Yahoo require SPF, DKIM and DMARC from anyone sending bulk mail to their users, so this is no longer optional for most organizations.

> **What SPF, DKIM and DMARC don't stop.** They protect **your exact domain**. An attacker who registers `examp1e.com` or `example-payments.com` can publish perfect SPF, DKIM and DMARC records for **their** domain and pass every check. Lookalike domains are caught by the email filter, DNS security and trained users, which is why the layers stack.

## Layer 3: identity and access

Assume some phishing will succeed, and limit what a stolen password can do:

- **MFA**: a stolen password alone no longer logs in. **Cisco Duo** adds number matching and Verified Duo Push against MFA fatigue, and device trust and risk-based policies. Ordinary push and one-time codes can still be relayed by an [adversary-in-the-middle proxy](/ccnp-security/attack-threats-vulnerabilities-cia-triad#token-theft-and-adversary-in-the-middle-phishing); **phishing-resistant MFA (FIDO2 / passkeys)** is bound to the real site's name and can't be relayed.
- **Least privilege**: give each user only the access their job needs. If one user is phished, the attacker gets **that user's** access, and has to find a **privilege escalation** to go further.

## Layer 4: people and process

People are the most targeted layer, so they need to be part of the defense, not just its weak point:

- **Short, frequent training** (15 to 20 minutes, games and quizzes) beats a yearly slide deck. Teach people to **hover over links**, check the **real sender address**, and distrust **urgency**.
- **Phishing simulations** that teach in the moment, measured by how many people **report** the message, not just how many click.
- **An easy "report phishing" button**: one reported message lets the security team pull the same email from every other mailbox.
- **Process controls for money and access**: verify payment and bank-detail changes by **calling back on a known number**, never the number in the email. This stops BEC and deepfake calls even when the message is convincing.
- Teach **MFA fatigue** specifically: an unexpected prompt should be **denied and reported**, never approved to make it stop.

## Layer 5: catch what gets through

| Control | What it does | Cisco product |
|---|---|---|
| **DNS-layer security** | When a user clicks a phishing link, the malicious domain **doesn't resolve**, so the connection never happens. The same mechanism blocks malware C2 callbacks | **Cisco Umbrella**, and **Cisco Secure Access** (Cisco's SSE platform, which includes Umbrella's DNS-layer security) |
| **Secure web gateway (SWG)** | Inspects web traffic and blocks known and newly seen phishing sites, risky categories and file downloads | Cisco Secure Access |
| **Remote browser isolation** | Opens risky sites in a remote browser, so only a safe rendering reaches the user | Cisco Secure Access |
| **SIEM** | Collects logs from mail, DNS, web, firewalls and identity, and correlates them to spot compromised accounts | **Splunk** (part of Cisco since 2024) |
| **XDR** | Correlates detections across **email, endpoint, network and identity** and speeds up response | **Cisco XDR** |

> **DNS security is the cheapest high-value phishing control.** Even after the user clicks, if the phishing domain won't resolve, nothing loads.

**Exam traps**

- **SPF = which servers may send. DKIM = a signature proving the domain signed it and it wasn't changed. DMARC = alignment + policy + reports.** All three are **DNS TXT records**.
- **DMARC passes only if SPF or DKIM passes and aligns with the From: domain.** Policies: `none`, `quarantine`, `reject`.
- **`-all` = hard fail, `~all` = soft fail.**
- **None of them stop lookalike domains.**
- **Secure Email Gateway** sits in the mail path via **MX records**; **Email Threat Defense** connects to Microsoft 365 by **API** and can remove delivered mail.
- **Vishing = voice, smishing = SMS, quishing = QR code, tailgating = physical.** **MFA fatigue = push bombing.**

---

# Cryptography building blocks

Every protocol later in this topic is assembled from a few primitives. Learn what each one **can** and **can't** do, and the protocols become easy to read.

![The cryptographic building blocks compared: a hash is one-way with no key and gives integrity; an HMAC adds a shared key for integrity and authenticity; symmetric encryption uses one shared key for fast confidentiality; asymmetric encryption uses the recipient's public key so only their private key can decrypt; a digital signature is made with the sender's private key and checked with their public key, adding non-repudiation](img/08/fig-03-crypto-primitives.webp)

## Hashing

A **hash function** turns any input into a fixed-length **digest** (also called a hash value or fingerprint):

```
"The quick brown fox jumps over the lazy dog"  ──▶  SHA-256  ──▶  d7a8fbb3 07d78094 69ca9abc b0082e4f ...
```

| Property | What it means |
|---|---|
| **One-way** | You can't recover the input from the digest. There's no key and nothing to decrypt |
| **Fixed length** | One word or a whole disk image gives a digest of the same size (256 bits for SHA-256) |
| **Deterministic** | The same input always gives the same digest |
| **Avalanche effect** | Changing **one bit** of input changes about **half** the digest |
| **Collision-resistant** | It should be infeasible to find two inputs with the same digest |

Two points that are often stated wrongly:

- **Hashing isn't encryption.** It has **no key** and produces **no ciphertext**, so there's nothing to decrypt.
- **"256" in SHA-256 is the digest length**, not a key size.

| Algorithm | Digest | Status |
|---|---|---|
| **MD5** | 128 bits | **Broken**: collisions are trivial |
| **SHA-1** | 160 bits | **Broken**: a practical collision was published in 2017 |
| **SHA-2** (SHA-256, SHA-384, SHA-512) | 256 to 512 bits | **Current standard** |
| **SHA-3** | 224 to 512 bits | Current; a different internal design, a backup to SHA-2 |

**Checking a download:** the vendor publishes the file's SHA-256 digest; you hash your copy and compare. A match proves the file **wasn't altered or corrupted**. It doesn't prove **who** made it: an attacker who replaces the file on a compromised site can replace the published hash too. That's what HMACs and signatures add.

**Passwords are stored as hashes**, but with a twist: a unique random **salt** per password and a deliberately **slow** algorithm (bcrypt, scrypt, Argon2, PBKDF2), so stolen hashes are expensive to crack.

## HMAC: a hash with a key

An **HMAC** (hash-based message authentication code) mixes a **shared secret key** into the hash. Only someone with the key can produce the right value, so an HMAC proves **integrity and authenticity**: the data is unchanged **and** came from someone who holds the key. IPsec, TLS 1.2, SNMPv3 and NTP authentication all use HMACs (HMAC-SHA-256 and similar). Because both sides share the same key, an HMAC can't prove **which** of them created a message, so it doesn't give non-repudiation.

## Symmetric encryption

**Encryption** turns plaintext into ciphertext with an **algorithm** (the cipher) and a **key**, and unlike hashing it's **reversible**. In **symmetric** encryption, **the same key** encrypts and decrypts:

```
 plaintext ──[ AES + shared key ]──▶ ciphertext ──[ AES + the same key ]──▶ plaintext
```

| Strength | Weakness |
|---|---|
| **Fast and efficient**, so it's used for all bulk data | **Key distribution**: how do you get the same secret to the other side safely, and to hundreds of peers? |

**Algorithms:** **AES** (128, 192 or 256-bit keys) is the standard, **ChaCha20** is a fast modern alternative, and DES and 3DES are broken or deprecated (see [missing or weak encryption](/ccnp-security/security-vulnerabilities-exploits#missing-or-weak-encryption)).

**Encryption alone doesn't guarantee integrity.** Ciphertext can be altered in transit, and older modes don't notice. Modern protocols use **authenticated encryption (AEAD)**, such as **AES-GCM** and **ChaCha20-Poly1305**, which encrypts **and** adds an integrity tag, so tampered ciphertext fails to decrypt. TLS 1.3 allows only AEAD ciphers.

## Asymmetric cryptography

**Asymmetric** (public-key) cryptography uses a **key pair**: a **private key** that never leaves its owner, and a **public key** that can be given to anyone. What one key does, only the other can undo.

That solves key distribution, at a cost: asymmetric operations are **much slower** than symmetric ones, so they're used for small jobs (agreeing on a key, signing), never for bulk data.

**The direction depends on the goal**, and this is the most tested fact in the topic:

| Goal | Done with | Checked or undone with | Example |
|---|---|---|---|
| **Confidentiality** | The **recipient's public** key encrypts | The **recipient's private** key decrypts | Lois encrypts a message to Bob with **Bob's public key**; only Bob can read it |
| **Digital signature** (authenticity, integrity, non-repudiation) | The **sender's private** key signs | The **sender's public** key verifies | A mail server signs with **its private key** (DKIM); anyone verifies with the public key in DNS |

A **digital signature** doesn't sign the whole message directly: the sender **hashes** the message and signs the **hash** with their private key. The receiver hashes the message too, verifies the signature with the sender's public key, and compares. Because only the sender holds the private key, a signature also gives **non-repudiation**: they can't credibly deny sending it.

Not every asymmetric algorithm does every job. This catches people out:

| Algorithm | Encrypt? | Sign? | Agree on a key? | Notes |
|---|---|---|---|---|
| **RSA** | Yes | Yes | Yes, by encrypting a key (key transport) | Key transport was removed from TLS 1.3 |
| **Diffie-Hellman (DH, ECDH)** | **No** | **No** | **Yes**: both sides compute the same secret without ever sending it | The basis of **forward secrecy** |
| **ECDSA, EdDSA** | No | **Yes** | No | Signatures only |
| **ML-KEM** (post-quantum) | No | No | **Yes** (key encapsulation) | See [post-quantum cryptography](/ccnp-security/attack-threats-vulnerabilities-cia-triad#post-quantum-cryptography) |
| **ML-DSA** (post-quantum) | No | **Yes** | No | |

**Diffie-Hellman doesn't encrypt anything.** It lets two sides **agree on a shared secret** over an open network: each side combines its own private value with the other side's public value, and both arrive at the same number, which an eavesdropper can't compute. That secret becomes the symmetric key. The **DH group** (for example group 14, 2048-bit; group 19 and 20, elliptic-curve) sets how strong the exchange is, and it must match on both IPsec peers.

## Hybrid cryptography and forward secrecy

Real protocols combine the primitives, using each where it's strongest. This is a **hybrid cryptosystem**:

1. **Certificates and signatures** prove **who** the other side is.
2. **Diffie-Hellman** (or another key exchange) **agrees on a symmetric key**.
3. **Symmetric AEAD encryption** (AES-GCM) protects all the data, with integrity built in.

**Forward secrecy** (perfect forward secrecy, PFS) means a fresh, **ephemeral** DH key pair for every session, thrown away afterwards. If the server's long-term private key is stolen later, **past sessions still can't be decrypted**, because their keys were never derived from it. TLS 1.3 requires it; in IPsec it's the **PFS** setting on the phase 2 (child SA) negotiation.

**Exam traps**

- **Hash = one-way, no key, integrity. Encryption = reversible, needs a key, confidentiality.** "256" in SHA-256 is the digest length.
- **MD5 and SHA-1 are broken; use SHA-2 or SHA-3.**
- **Symmetric = one shared key, fast, key-distribution problem. Asymmetric = key pair, slow, solves distribution.**
- **Confidentiality: recipient's public key. Signature: sender's private key.** Private keys are never shared.
- **Diffie-Hellman agrees on a key; it doesn't encrypt or sign.**
- **Hash = integrity. HMAC = + authenticity. Signature = + non-repudiation.**

---

# PKI and certificates

## The problem PKI solves

Asymmetric cryptography has one gap: **how do you know a public key really belongs to who it claims to?** If an attacker can swap Bob's public key for their own, Lois encrypts to the attacker, who reads the message and re-encrypts it to Bob: a [man-in-the-middle attack](/ccnp-security/attack-threats-vulnerabilities-cia-triad#on-path-man-in-the-middle-attacks). **Public key infrastructure (PKI)** closes the gap with a **trusted third party** that vouches for the binding between an identity and a key.

## The pieces of PKI

| Component | Role |
|---|---|
| **Certificate Authority (CA)** | **Issues and signs** certificates. A **root CA** signs **intermediate CAs**, which sign the certificates servers and users actually use |
| **Registration Authority (RA)** | **Verifies the requester's identity** before the CA issues. Often part of the CA itself |
| **Digital certificate** | Binds an **identity** to a **public key**, signed by the CA. The standard format is **X.509** |
| **CSR** (certificate signing request) | What the requester sends: their **public key** plus identity details, signed with their private key. **The private key never leaves the requester** |
| **CRL** (certificate revocation list) | A signed list of **revoked** certificates, published periodically by the CA |
| **OCSP** (Online Certificate Status Protocol) | Asks the CA about **one** certificate's status in real time |
| **OCSP stapling** | The **server** fetches its own signed OCSP response and presents it in the TLS handshake, so the client doesn't have to ask the CA |

What's in an X.509 certificate: the **subject** (who it's for) and **subject alternative names** (the DNS names it covers), the **public key**, the **issuer**, a **validity period**, a **serial number**, **key usage** (what the key may be used for), and the **CA's signature** over all of it.

## Issuing a certificate

![PKI in action: a server generates a key pair and sends a certificate signing request containing only its public key and identity, the registration authority verifies the identity and the CA signs the certificate; on the right, a browser validates the chain from the server certificate to an intermediate CA to a root CA already in its trust store, checks the dates and names, and checks revocation through a CRL, OCSP or a stapled OCSP response](img/08/fig-04-pki.webp)

1. The server **generates a key pair**. The private key stays on the server.
2. It builds a **CSR**: its **public key** and identity (names, organization).
3. The **RA verifies** the identity: for a public web certificate, at least proof of control of the domain.
4. The **CA signs** the certificate and returns it. The server installs it alongside its private key.

## How a client decides to trust a certificate

Operating systems and browsers ship with a **trust store** of root CA certificates. When a server presents its certificate, the client checks:

1. **The chain:** the server certificate was signed by an intermediate CA, which was signed by a **root in the trust store**. Root trusts intermediate, intermediate vouches for the server.
2. **The signatures** at every step are valid.
3. **The dates:** the certificate isn't expired or not yet valid.
4. **The name:** the hostname the user asked for is in the certificate's subject alternative names.
5. **Revocation:** the certificate isn't on the CA's **CRL**, or OCSP says it's good.

Fail any check and the browser shows a warning instead of the padlock.

**Revocation** is how a certificate is distrusted before it expires, for example after its **private key is stolen**: the CA adds it to the CRL and answers "revoked" over OCSP. Revocation has always been patchy in practice (CRLs are large, OCSP leaks which sites you visit), so the industry is moving to **short-lived certificates** instead. Under a 2025 CA/Browser Forum decision, the maximum life of public TLS certificates falls from 398 days to **200 days from March 2026**, **100 days from March 2027** and **47 days from March 2029**, which makes **automated renewal** (ACME) essential.

## Certificates on Cisco devices

Routers, switches and firewalls use certificates for their HTTPS and RESTCONF management, for IPsec peer authentication and for remote-access VPN. On IOS XE, a **trustpoint** holds a CA's certificate and the device's own certificate:

```
crypto pki trustpoint CORP-CA
 enrollment url http://ca.example.com:80
 subject-name CN=r1.example.com
 revocation-check crl
 rsakeypair R1-KEY 2048
crypto pki authenticate CORP-CA
crypto pki enroll CORP-CA
```

`crypto pki authenticate` installs and trusts the CA's certificate; `crypto pki enroll` sends the CSR. Enrollment can be automated with **SCEP** or **EST**. A **self-signed** certificate (the device signs its own) encrypts traffic but proves nothing about identity, which is why browsers warn about it.

**Exam traps**

- **PKI = trust in public keys.** **CA signs; RA verifies identity; CRL and OCSP handle revocation.** Certificates are **X.509**.
- **A CSR carries the public key and identity, never the private key.**
- **Trust chain:** root (in the trust store) → intermediate → server certificate.
- **OCSP stapling:** the server presents its own fresh status, so the client needn't contact the CA.

---

# SSL and TLS

**TLS (Transport Layer Security)** encrypts an application connection: it's the S in **HTTPS**, and it secures mail, directory, syslog, RADIUS and VPN traffic too. Its predecessor **SSL (Secure Sockets Layer)** is entirely **deprecated**, but people still say "SSL" (SSL certificates, SSL VPN, SSL decryption) when they mean TLS.

| Version | Year | Status |
|---|---|---|
| SSL 2.0, SSL 3.0 | 1995, 1996 | **Broken** (POODLE killed SSL 3.0 in 2014) |
| TLS 1.0, TLS 1.1 | 1999, 2006 | **Deprecated** by RFC 8996 (2021) |
| **TLS 1.2** | 2008 | **Acceptable** with strong, AEAD cipher suites and forward secrecy |
| **TLS 1.3** | 2018 | **Preferred** |

## The handshake: hybrid crypto in action

![The TLS 1.3 handshake in one round trip: the client hello carries supported cipher suites and a Diffie-Hellman key share, the server hello returns its key share, after which both sides derive the session keys and everything else is encrypted, including the server's certificate, its signature proving it owns the private key, and the finished messages; application data then flows under AES-GCM; a side panel lists which building block does which job and how TLS 1.2 differs](img/08/fig-05-tls-handshake.webp)

1. **ClientHello:** the TLS versions and cipher suites the client supports, and in TLS 1.3 a **Diffie-Hellman key share** straight away.
2. **ServerHello:** the server picks a cipher suite and sends **its** key share. Both sides now compute the same secret and derive the **session keys**.
3. **Certificate and CertificateVerify:** the server sends its **certificate** (PKI: the client validates the chain) and **signs** the handshake with its private key, proving it really owns the certificate.
4. **Finished:** both sides confirm the handshake wasn't tampered with.
5. **Application data** flows under fast **symmetric AEAD** encryption (AES-GCM or ChaCha20-Poly1305).

| | TLS 1.2 | TLS 1.3 |
|---|---|---|
| Round trips before data | **2** | **1** (0-RTT for resumed sessions, with replay risk) |
| Key exchange | RSA key transport **or** (EC)DHE | **(EC)DHE only** |
| Forward secrecy | Optional | **Mandatory** |
| Cipher suites | Dozens, including weak ones | **Five**, all AEAD |
| Certificate | Sent in **cleartext** | **Encrypted** |
| Removed | n/a | RSA key transport, static DH, CBC mode, RC4, SHA-1, MD5, compression, renegotiation |

## Where TLS is used

| Use | Port |
|---|---|
| HTTPS | TCP 443 |
| SMTP submission with STARTTLS / implicit TLS | TCP 587 / 465 |
| IMAPS, POP3S | TCP 993, 995 |
| LDAPS | TCP 636 |
| Syslog over TLS | TCP 6514 |
| DNS over TLS / DNS over HTTPS | TCP 853 / TCP 443 |
| RADIUS over TLS (RadSec) | TCP 2083 |
| Cisco Secure Client VPN | TCP 443 (TLS), then **DTLS** over **UDP 443** for the data |

**STARTTLS** upgrades a plaintext connection to TLS on the same port; **implicit TLS** starts encrypted on a dedicated port. **DTLS** is TLS adapted to UDP, used by Secure Client because tunneling traffic over TCP performs badly.

**TLS inspection** (decryption) is TLS deliberately broken in the middle by your own security device: Cisco Secure Firewall or Secure Access terminates the session, inspects it, and re-encrypts it with a certificate from an **internal CA** that company devices trust. It's the same mechanics as an on-path attack, with authorization.

---

# QUIC

Traditional web traffic uses **two separate layers**: **TCP** for reliable delivery, then **TLS** on top for encryption, each with its own handshake. **QUIC** (RFC 9000, 2021) merges them into **one protocol that runs over UDP**, with **TLS 1.3 built in**. It's the transport underneath **HTTP/3**.

| | TCP + TLS | QUIC |
|---|---|---|
| Transport | TCP | **UDP**, usually port **443** |
| Encryption | TLS on top, separate | **TLS 1.3 integrated**; even most transport header fields are encrypted |
| Handshakes | TCP handshake, then TLS handshake | **One** combined handshake: 1-RTT, or 0-RTT when resuming |
| Lost packet | Blocks **every** stream on the connection (head-of-line blocking) | Blocks only **its own** stream |
| Changing networks (Wi-Fi to mobile) | The connection breaks; a new one starts | The connection survives, identified by **connection IDs**, not IP and port |
| Used by | HTTP/1.1, HTTP/2 | **HTTP/3**, and MASQUE |

**Why security teams care:** QUIC is **encrypted UDP 443**, and firewalls built around TCP 443 often can't apply the same URL filtering or decryption to it. A common practice is to **block UDP 443** (or QUIC as an application) so browsers **fall back to TCP + TLS**, which the firewall or SWG can inspect. Cisco Secure Firewall can identify and block QUIC with an application rule.

---

# MASQUE

**MASQUE** (Multiplexed Application Substrate over QUIC Encryption) uses **HTTP/3 over QUIC** to build a **tunnel** through a proxy. QUIC on its own secures **one** connection; MASQUE adds HTTP methods that let a client ask a proxy to carry **arbitrary UDP** (CONNECT-UDP, RFC 9298) or **whole IP packets** (CONNECT-IP, RFC 9484), with ordinary TCP proxying alongside. The result behaves like a VPN, but to the network it looks like **HTTP/3 web traffic on UDP 443**.

```
 Client ══[ MASQUE: HTTP/3 over QUIC over UDP 443, TLS 1.3 ]══▶ Proxy ──▶ apps, sites, private networks
```

Where you'll meet it:

- **Apple iCloud Private Relay** and **Cloudflare WARP** use MASQUE proxies for privacy.
- **Cisco Secure Access** uses **QUIC and MASQUE** in the Cisco Secure Client **Zero Trust Access** module to carry users' traffic to private applications. This is why MASQUE is in the SCOR blueprint.

**Why it matters for security:**

| Use | Why MASQUE suits it |
|---|---|
| **Zero trust access** | Per-application tunnels set up after the user and device are verified, fast reconnects when networks change |
| **Privacy and anonymization** | Traffic is hidden inside ordinary-looking HTTP/3 |
| **Bypassing controls** (the risk) | Encrypted UDP 443 is hard to tell apart from normal web traffic, so unauthorized MASQUE proxies can tunnel past filtering unless QUIC is controlled or decrypted |

---

# IPsec

**IPsec** is a suite of protocols that protects **IP packets** between two endpoints, so **every application** inside the tunnel is protected without knowing about it. It provides **confidentiality, integrity and authentication**, plus anti-replay protection. It's the basis of site-to-site VPNs and many remote-access VPNs, and the [VPN deployment types](#how-the-protocols-fit-the-vpn-topics) later in the blueprint build on it.

## AH and ESP

![IPsec packets compared: AH in transport mode and tunnel mode authenticates the whole packet including the outer IP header but encrypts nothing; ESP in transport mode encrypts only the payload, while ESP in tunnel mode wraps and encrypts the entire original packet behind a new IP header; with NAT-T, the ESP packet is placed inside a UDP header on port 4500 so NAT devices can track it](img/08/fig-06-ipsec.webp)

| | **AH** (Authentication Header) | **ESP** (Encapsulating Security Payload) |
|---|---|---|
| IP protocol number | **51** | **50** |
| Encryption | **None** | **Yes** |
| Integrity and authentication | Yes, over the **whole packet including the outer IP header** | Yes, over the ESP header and payload, **not** the outer IP header |
| Works through NAT? | **Never**: NAT changes the IP header AH authenticated | **Yes, with NAT-T** |
| In practice | Rarely used | **Almost every IPsec VPN** |

## Transport and tunnel mode

| | **Transport mode** | **Tunnel mode** |
|---|---|---|
| What's protected | The **payload** only; the original IP header stays in front | The **entire original packet**, wrapped behind a **new** IP header |
| Who sees the real addresses | Anyone on the path | Only the tunnel endpoints' addresses are visible |
| Typical use | **Host-to-host**, and **GRE over IPsec** or **DMVPN**, where GRE already adds the outer header | **Site-to-site and remote-access VPNs** between gateways |

**The default combination for a VPN is ESP in tunnel mode:** the whole packet encrypted and authenticated.

## IKE: negotiating the tunnel

Before any data flows, the peers use **IKE (Internet Key Exchange)** on **UDP 500** to authenticate each other, agree on algorithms, and run Diffie-Hellman to create keys. The results are **security associations (SAs)**: one-way agreements identified by an **SPI** (security parameter index) in each packet.

| | **IKEv1** | **IKEv2** (preferred) |
|---|---|---|
| Phase 1 / first exchange | **Main mode** (6 messages) or **aggressive mode** (3, less private) builds the IKE (ISAKMP) SA | **IKE_SA_INIT** and **IKE_AUTH**: 4 messages build the IKE SA **and** the first child SA |
| Phase 2 / data SAs | **Quick mode** builds the IPsec SAs | **CREATE_CHILD_SA** for extra or rekeyed SAs |
| Built in | Little; NAT-T and dead-peer detection were add-ons | **NAT-T, dead-peer detection, EAP** for remote access, MOBIKE |
| Cisco | Legacy crypto maps | **FlexVPN**, Secure Firewall (FTD) VPNs |

Both peers must agree on the **encryption algorithm, integrity (hash) algorithm, DH group, authentication method and lifetimes**. A mismatch in any of them is the most common reason a tunnel won't come up.

## NAT and NAT-T

**NAT** translates private addresses (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) to public ones. The usual form, **PAT** (NAT overload), lets many inside hosts share one public address by tracking **port numbers**:

```
 Inside local 192.168.10.55:51062  ──▶  router translates to  inside global 203.0.113.10:5001  ──▶ server
 Reply to 203.0.113.10:5001        ──▶  router looks up its NAT table  ──▶  192.168.10.55:51062
```

**The problem:** ESP is **IP protocol 50**: it sits directly on IP and has **no port numbers**. In tunnel mode the inner TCP and UDP ports are encrypted too. A PAT device has nothing to track ESP sessions by, so the tunnel breaks when a peer sits behind PAT.

**The fix: NAT Traversal (NAT-T).** IKE detects NAT during the first exchange (each side sends hashes of its address and port, and a mismatch means something translated them). If NAT is found, both peers **move IKE to UDP 4500** and **wrap every ESP packet in a UDP header on port 4500**. NAT handles it like any other UDP flow, and **NAT keepalives** (20 seconds by default on Cisco ASA and Secure Firewall) stop the NAT mapping expiring while the tunnel is idle.

| Port or protocol | What uses it |
|---|---|
| **UDP 500** | IKE, when no NAT is in the path |
| **UDP 4500** | IKE **and** ESP, once NAT-T is in use |
| **IP protocol 50** | ESP, with no NAT in the path |
| **IP protocol 51** | AH (can't cross NAT) |

The blueprint says **NAT-T IPv4** for a reason: NAT, and so NAT-T, is mostly an IPv4 problem. IPv6 hosts normally have global addresses and don't need it.

## Authenticating the peers: pre-shared keys and certificates

| | **Pre-shared key (PSK)** | **Certificates** (RSA or ECDSA signatures) |
|---|---|---|
| What each peer holds | The **same secret string**, configured on both ends | Its **own private key and certificate**, plus the **CA's** certificate |
| Crypto | **Symmetric** (a shared secret) | **Asymmetric** with **PKI** |
| Scale | Each pair needs a secret; hundreds of sites means hundreds of secrets | Add a site by enrolling one certificate; no per-pair secrets |
| If it leaks | The secret works from anywhere until it's changed on both ends | **Revoke** one certificate; the rest are unaffected |
| Best for | A few site-to-site tunnels, labs | Large site-to-site meshes, DMVPN, FlexVPN, remote access |

On IOS XE, the difference is one line in the IKEv2 profile:

```
crypto ikev2 profile BRANCH-PSK
 match identity remote address 203.0.113.2 255.255.255.255
 authentication remote pre-share key Lab!Psk2026
 authentication local pre-share key Lab!Psk2026
!
crypto ikev2 profile BRANCH-CERT
 match certificate BRANCH-MAP
 authentication remote rsa-sig
 authentication local rsa-sig
 pki trustpoint CORP-CA
```

> **Lab value only.** `Lab!Psk2026` is a training value. Never reuse it.

**Certificate-based authorization** goes one step further: a certificate doesn't just prove **who** the peer is, its fields (organization, OU, a name pattern) can decide **what** it gets. A FlexVPN or Secure Firewall headend can map a certificate to a profile or group policy, so a branch router's certificate lands it in the branch policy and a contractor's certificate lands it in a restricted one. That's least privilege, enforced by the certificate itself.

Remote-access VPN users usually combine the two ideas: the **device** presents a certificate, and the **user** authenticates with a password and MFA (IKEv2 with **EAP**, or Secure Client over TLS).

## Post-quantum cryptography in these protocols

The [quantum threat](/ccnp-security/attack-threats-vulnerabilities-cia-triad#post-quantum-cryptography) is to the **key exchange and signatures**, not to AES. In the protocols above, migration looks like this:

| Protocol | What changes |
|---|---|
| **TLS 1.3 and QUIC** | **Hybrid** key exchange such as `X25519MLKEM768`, classical ECDH plus ML-KEM, already on by default in major browsers |
| **IKEv2 / IPsec** | **Additional key exchanges** (RFC 9370) that add ML-KEM to the DH exchange, and **post-quantum preshared keys** (PPK, RFC 8784) mixed into the keys; recent IOS XE releases support both |
| **PKI** | Certificates signed with **ML-DSA**, a slower transition because every CA, device and client has to support it |
| **Symmetric layer** | **AES-256** and **SHA-384** for margin |

---

# Telling the protocols apart

This is the table to come back to. Every protocol from the topic, answered with the same four questions:

![Four ways to protect traffic drawn as stacks: HTTPS puts TLS over TCP 443 so one application connection is encrypted; HTTP/3 puts TLS 1.3 inside QUIC over UDP 443; MASQUE carries other traffic inside HTTP/3 over QUIC to a proxy; IPsec ESP in tunnel mode encrypts the whole original IP packet as IP protocol 50, or inside UDP 4500 with NAT-T, so every application is protected](img/08/fig-07-protocol-stacks.webp)

| Protocol | Protects | Layer | Rides on | Identity proven by | You'll see it as |
|---|---|---|---|---|---|
| **TLS 1.2 / 1.3** | C, I, authenticity | One **application connection** | **TCP** (443 for HTTPS) | Server certificate (PKI); optionally client certificate | TCP 443 with a TLS handshake |
| **DTLS** | C, I, authenticity | One application flow | **UDP** (443 for Secure Client) | Certificate | UDP 443 alongside a TLS session |
| **QUIC** | C, I, authenticity | Transport + TLS 1.3 combined | **UDP 443** | Server certificate (PKI) | UDP 443, mostly encrypted headers |
| **MASQUE** | C, I, authenticity | A **tunnel** inside HTTP/3 | QUIC, **UDP 443** | Proxy certificate plus user or device identity | Looks like ordinary HTTP/3 |
| **IPsec ESP** | C, I, authenticity, anti-replay | **IP packets** (network layer) | **IP protocol 50**, or **UDP 4500** with NAT-T | PSK or certificates, via IKE | Protocol 50, or UDP 4500 |
| **IPsec AH** | I, authenticity only | IP packets | **IP protocol 51** | PSK or certificates, via IKE | Protocol 51; fails through NAT |
| **IKE** | Negotiates SAs and keys | Control channel for IPsec | **UDP 500**, then 4500 with NAT-T | PSK, certificates or EAP | UDP 500 / 4500 |
| **SPF** | Authorizes sending servers | Email (DNS) | DNS TXT lookup | Sending IP is in the domain's list | `v=spf1` record |
| **DKIM** | I, authenticity of a message | Email (DNS + header) | DNS TXT + message header | Domain's private key; public key in DNS | `DKIM-Signature` header |
| **DMARC** | Policy and reporting | Email (DNS) | DNS TXT lookup | SPF or DKIM pass + alignment | `_dmarc` record |

Three pairs the exam likes to confuse:

- **TLS vs. IPsec:** TLS protects **one application's connection** and needs the application to use it. IPsec protects **IP packets**, so every application inside the tunnel is covered without knowing it.
- **QUIC vs. MASQUE:** QUIC is a **transport** for one connection. MASQUE is a **tunnel** built on top of QUIC and HTTP/3 to carry other traffic.
- **AH vs. ESP:** AH **authenticates** but never encrypts and can't cross NAT. ESP **encrypts and authenticates** and crosses NAT with NAT-T.

## How the protocols fit the VPN topics

| VPN type (topic 1.6 onward) | Built on |
|---|---|
| Site-to-site IPsec, VTI, DMVPN, FlexVPN, GETVPN | **IPsec ESP**, keys negotiated by **IKE** (GETVPN uses a group key server instead of per-pair IKE) |
| Remote access with Cisco Secure Client | **TLS + DTLS** ("SSL VPN") or **IKEv2/IPsec** |
| Zero trust access with Cisco Secure Access | **QUIC + MASQUE** |

**Exam traps**

- **SSL is deprecated; TLS 1.2 and 1.3 are current.** TLS 1.3: one round trip, mandatory forward secrecy, encrypted certificate, AEAD only.
- **QUIC = UDP + TLS 1.3 in one protocol, under HTTP/3.** Blocking UDP 443 forces a fallback to inspectable TCP + TLS.
- **MASQUE = a tunnel over HTTP/3 and QUIC**, used by Cisco Secure Access zero trust access, iCloud Private Relay and Cloudflare WARP.
- **ESP = IP 50, encrypts. AH = IP 51, no encryption, no NAT.** VPNs use **ESP in tunnel mode**.
- **IKE = UDP 500. NAT-T = UDP 4500.** ESP has no ports, which is why PAT breaks it.
- **PSK = shared secret, doesn't scale. Certificates = PKI, scale, can be revoked individually, and can drive authorization.**

---

# Quick reference

| Control or primitive | One-line ID | Provides |
|---|---|---|
| Secure Email Gateway | In the mail path via MX records | Blocks spam, phishing, malware before delivery |
| Email Threat Defense | Microsoft 365 API integration | Detects and removes mail, including after delivery |
| SPF | Which servers may send | Sender authorization |
| DKIM | Domain's signature on the message | Integrity + authenticity |
| DMARC | Alignment, policy, reports | Anti-spoofing of the visible From: domain |
| DNS-layer security | Malicious domains don't resolve | Blocks the click before the connection |
| Hash (SHA-2/3) | One-way fingerprint | Integrity |
| HMAC | Hash + shared key | Integrity + authenticity |
| Symmetric (AES-GCM) | One shared key, AEAD | Confidentiality + integrity, fast |
| Asymmetric (RSA, ECC) | Key pair | Key distribution, signatures |
| Diffie-Hellman | Agree on a secret in the open | Key agreement, forward secrecy |
| Digital signature | Hash signed with a private key | Integrity + authenticity + non-repudiation |
| PKI | CA-signed X.509 certificates | Trust in public keys |
| TLS 1.3 | 1-RTT, AEAD only, PFS | Secure application connections |
| QUIC | UDP + TLS 1.3 | Faster secure transport, HTTP/3 |
| MASQUE | HTTP/3 + QUIC tunnel | Proxy / zero trust access |
| IPsec ESP, tunnel mode | Whole packet encrypted | Site-to-site and remote-access VPNs |
| NAT-T | ESP inside UDP 4500 | IPsec through NAT |
| PSK vs. certificates | Shared secret vs. PKI | Peer authentication; certificates also drive authorization |

---

# Check yourself

<details><summary>1. An email shows From: ceo@example.com, but it was sent from a server example.com never authorized. Which record catches the unauthorized server, and which part tells receivers to reject it?</summary>

**SPF** lists the servers allowed to send for the domain, and **`-all`** makes everything else a hard fail. For the receiver to act on the visible From: address, the domain also needs **DMARC** with **`p=reject`** (or `quarantine`), because SPF on its own checks the envelope sender.

</details>

<details><summary>2. An attacker sends mail from their own domain, which passes SPF, but displays ceo@example.com in the From: line. Which record stops this, and how?</summary>

**DMARC**, through **alignment**: SPF passed, but for the attacker's domain, which doesn't match the From: domain. DMARC requires SPF or DKIM to pass **for the same domain the user sees**.

</details>

<details><summary>3. What does DKIM prove that SPF doesn't, and which key does what?</summary>

DKIM proves the message was **signed by the domain** and **hasn't been changed**. The sending server signs with its **private key**; receivers verify with the **public key** published in DNS at `selector._domainkey.domain`.

</details>

<details><summary>4. A company's SPF, DKIM and DMARC are perfect, yet staff receive a convincing invoice from examp1e.com. Why didn't the records stop it, and what would?</summary>

The records only protect the company's **own** domain; `examp1e.com` is a different domain that can pass its own checks. The **email filter** (reputation, lookalike detection), **DNS security**, and **trained users** who check sender addresses are the defenses here.

</details>

<details><summary>5. Name each: a phone call from "IT support", a text with a delivery link, a QR code on a poster, someone following an employee through a badge door.</summary>

**Vishing**, **smishing**, **quishing**, and **tailgating** (physical social engineering, not phishing).

</details>

<details><summary>6. A user approves an MFA prompt after receiving fifteen in a row at midnight. What attack is this, and which two controls help?</summary>

**MFA fatigue (push bombing)**. **Number matching / Verified Duo Push** stops blind approval, and **training** teaches users to deny and report prompts they didn't start. Phishing-resistant MFA (FIDO2) removes push approvals altogether.

</details>

<details><summary>7. Which Cisco email product sits in the mail path, and which connects to Microsoft 365 by API and can remove mail after delivery?</summary>

**Cisco Secure Email Gateway** (formerly ESA) sits in the path via **MX records**. **Cisco Secure Email Threat Defense** uses the **Microsoft 365 API** and can remediate delivered mail.

</details>

<details><summary>8. You download an ISO and its SHA-256 digest matches the vendor's. What have you proven, and what haven't you?</summary>

You've proven **integrity**: the file wasn't changed or corrupted. You **haven't** proven who produced it; a digital signature, or a hash obtained from a trusted signed source, proves origin.

</details>

<details><summary>9. Why can't a SHA-256 digest be "decrypted" back to the original data?</summary>

Hashing is **one-way** and uses **no key**; it isn't encryption. The digest is a fixed-length fingerprint with no inverse.

</details>

<details><summary>10. Lois sends Bob a confidential message using asymmetric crypto. Which key does she encrypt with? If she wanted to sign it instead, which key would she use?</summary>

**Bob's public key** for confidentiality (only Bob's private key decrypts). **Her own private key** to sign (anyone can verify with her public key).

</details>

<details><summary>11. Someone says "Diffie-Hellman encrypts the data in a VPN." What's wrong with that?</summary>

Diffie-Hellman doesn't encrypt anything. It lets two peers **agree on a shared secret** over an open network. That secret becomes the **symmetric key**, and AES (or another symmetric cipher) encrypts the data.

</details>

<details><summary>12. A server's long-term private key is stolen. Why can't the attacker decrypt last month's recorded TLS 1.3 sessions?</summary>

**Forward secrecy**: every TLS 1.3 session uses a fresh **ephemeral** Diffie-Hellman exchange whose keys were discarded. The long-term key only **signs** the handshake; it was never used to create the session keys.

</details>

<details><summary>13. What does a CSR contain, what does the RA do, and what does the CA do?</summary>

The **CSR** holds the requester's **public key** and identity, never the private key. The **RA** verifies the requester's identity. The **CA** signs and issues the certificate.

</details>

<details><summary>14. A web server's private key leaks. How do clients learn not to trust its certificate, and what does OCSP stapling change?</summary>

The CA **revokes** the certificate: it appears on the **CRL** and OCSP reports it as revoked. With **OCSP stapling**, the **server** presents a fresh signed OCSP response in the handshake, so clients don't have to contact the CA themselves.

</details>

<details><summary>15. List three differences between TLS 1.2 and TLS 1.3.</summary>

Any three of: TLS 1.3 needs **one round trip** instead of two; **forward secrecy is mandatory** (no RSA key transport); only **five AEAD cipher suites**; the **server certificate is encrypted**; legacy options such as CBC, RC4, SHA-1 and renegotiation are gone.

</details>

<details><summary>16. How is QUIC different from TCP + TLS, and why do some organizations block UDP 443?</summary>

QUIC combines transport and **TLS 1.3** in one protocol over **UDP**, with one handshake, no head-of-line blocking between streams and connection migration. Organizations block **UDP 443** so browsers **fall back to TCP + TLS**, which their firewall or SWG can inspect.

</details>

<details><summary>17. What is MASQUE built from, and where does Cisco use it?</summary>

**HTTP/3 over QUIC**, used to build tunnels through a proxy (CONNECT-UDP, CONNECT-IP). Cisco uses QUIC and MASQUE in the **Zero Trust Access** module of Cisco Secure Client with **Cisco Secure Access**. iCloud Private Relay and Cloudflare WARP use it too.

</details>

<details><summary>18. A VPN between two sites must hide the original packets entirely and provide encryption, integrity and authentication. Which protocol and mode?</summary>

**ESP in tunnel mode**. AH can't encrypt, and transport mode leaves the original IP header visible.

</details>

<details><summary>19. An IPsec tunnel works until one peer is moved behind a PAT router, then it fails. Why, and what fixes it?</summary>

**ESP (IP protocol 50) has no port numbers**, so PAT can't track it. **NAT-T** detects the NAT during IKE and wraps ESP (and IKE) in **UDP 4500**, which PAT handles like any UDP flow.

</details>

<details><summary>20. Which IPsec protocol can never work through NAT, even with NAT-T, and why?</summary>

**AH**. It authenticates the **outer IP header**, which NAT has to change, so every translated packet fails the integrity check. NAT-T only applies to ESP.

</details>

<details><summary>21. A company is growing from 3 to 300 IPsec sites. Why move from pre-shared keys to certificates?</summary>

PSKs need a shared secret per peer relationship, are hard to rotate, and a leaked key works until it's changed everywhere. **Certificates** scale through the CA (enroll each site once), can be **revoked individually**, and their fields can drive **authorization**, such as mapping a branch to its policy.

</details>

<details><summary>22. Match each to what it protects: TLS, IPsec ESP, MASQUE.</summary>

**TLS**: one application's connection. **IPsec ESP**: IP packets, so every application inside the tunnel. **MASQUE**: a tunnel inside HTTP/3 and QUIC that carries other traffic through a proxy.

</details>
