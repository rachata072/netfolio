# VPNs, IPsec & IKE

> **CCNP Security · SCOR 350-701 v2.0 · Domain 1.0 Security Concepts**
>
> **1.6** Describe site-to-site and remote access VPN deployment types such as virtual tunnel interfaces, standards-based IPsec, SSL VPN, DMVPN, FlexVPN, and GETVPN
>
> The building blocks (AH and ESP, transport and tunnel mode, NAT-T, pre-shared keys and certificates) are in [Phishing Defense & Cryptographic Security](/ccnp-security/phishing-defense-cryptography#ipsec). This topic assumes them and goes one level deeper: how IKE actually builds the tunnel, how to tell the VPN protocols apart, and how to read a live tunnel on a router.

---

# How to think about VPNs

A VPN keeps your data **confidential, unaltered and authentic** while it crosses a network you **don't control**. Every VPN, from a two-router lab to a 5,000-user remote-access headend, answers the same three questions. Learn to ask them and every VPN topic, config and failure falls into place.

## Three questions every VPN answers

| Question | What answers it | Where it lives in an IOS IKEv1 config |
|---|---|---|
| **1. Who is at the other end?** | Peer **authentication**: a pre-shared key, a certificate, or (for users) EAP and MFA | `crypto isakmp policy` (`authentication`) and `crypto isakmp key` |
| **2. How is the data protected?** | The **algorithms and keys**: ESP, AES, SHA, Diffie-Hellman, PFS, lifetimes | `crypto isakmp policy` (Phase 1) and the **transform set** (Phase 2) |
| **3. Which traffic goes in?** | The **traffic selectors**: a crypto ACL, a route into a tunnel interface, or a split-tunnel list | `access-list` + `match address`, or `ip route ... Tunnel0` |

These questions also organize troubleshooting. A tunnel that won't come up has a problem with **question 2** (the peers can't agree), **question 1** (they agree but don't trust each other), or **question 3** (they trust each other but disagree about what to protect). The [IKEv1 states](#reading-ikev1-states-in-the-real-world) tell you which one.

## The attacker's view

Attackers rarely break AES. They go after the parts around it:

- **The secret, not the cipher.** A weak or shared pre-shared key, especially with [aggressive mode](#main-mode-and-aggressive-mode), can be cracked offline.
- **Old negotiation options.** DH group 2 and SHA-1 still "work" and still get negotiated if you leave them configured.
- **The selectors.** Traffic that doesn't match the selectors leaves **in cleartext**, silently. An over-broad selector encrypts traffic you meant to inspect.
- **The headend itself.** An internet-facing VPN gateway is one of the most attacked devices you own. Patch it first, and put MFA on every remote-access login.
- **The endpoint.** A remote-access client is a door into the LAN. Split tunneling and an unmanaged laptop together make that door wider.

## How SCOR tests this topic

| Style | Example | Answer |
|---|---|---|
| **Pick the VPN type** | "A sales team needs access from hotel Wi-Fi to internal apps" | **Remote-access** VPN with Cisco Secure Client |
| **Match the protocol to what it provides** | "Which protocol carries multicast routing traffic between sites but doesn't encrypt it?" | **GRE**, so it's paired with IPsec |
| **Name the phase or exchange** | "Which IKEv1 exchange negotiates the IPsec SAs?" | **Quick mode** (Phase 2) |
| **Compare IKEv1 and IKEv2** | "Which IKE version supports EAP and asymmetric authentication?" | **IKEv2** |
| **Pick the deployment** | "Encrypt traffic across a private MPLS WAN without point-to-point tunnels" | **GETVPN** |
| **Read the output** | "`show crypto isakmp sa` shows `MM_NO_STATE`" | Phase 1 **policy mismatch** or no reply from the peer |

---

# What a VPN is for

A VPN builds a **protected tunnel across an untrusted network**, so traffic between two trusted places looks like it never left. The key word is **untrusted**. Traffic inside your own LAN doesn't normally need a VPN; traffic across the internet does.

## A private circuit is not an encrypted circuit

Before VPNs, the way to connect sites "privately" was a leased line or an **MPLS** service from a provider. MPLS keeps your traffic **separate** from other customers with labels and VRFs, and it comes with service-level guarantees. It does **not encrypt** anything. Your packets still cross the provider's routers in cleartext.

That's why organizations often **run a VPN over MPLS anyway**: MPLS gives separation and predictable performance, the VPN adds confidentiality and integrity in case the provider, or anyone with access to its network, isn't fully trusted. [GETVPN](#the-1-6-deployment-types-at-a-glance) was designed for exactly this case.

Encryption also has uses inside networks you do control: **MACsec** encrypts Ethernet links hop by hop, and GETVPN can encrypt a private WAN without changing its routing.

---

# Site-to-site and remote access

![Site-to-site versus remote access: in a site-to-site VPN, gateways at HQ and a branch build one IPsec tunnel and users on both LANs are unaware of it; in remote access, one user's device runs Cisco Secure Client to an IPsec IKEv2 or TLS and DTLS headend for full network access, while a clientless browser session reaches only selected web applications through an HTTPS portal; below, a full tunnel sends all of the user's traffic to the headend while a split tunnel sends only corporate subnets and lets internet traffic go direct](img/09/fig-01-vpn-types.webp)

| | **Site-to-site** (LAN-to-LAN, L2L) | **Remote access** (RA) |
|---|---|---|
| **Connects** | Whole **networks** to each other | **One user's device** to a network |
| **Tunnel endpoints** | Two gateways: routers, firewalls or concentrators | The user's device and a **headend** |
| **Who knows about it** | Nobody but the gateways. **Transparent to users**: they just reach an IP or a URL | The user, who starts it or has it start automatically |
| **Software on the user's device** | None | **Cisco Secure Client** (formerly AnyConnect), or just a browser for clientless |
| **Authenticates** | The **gateways**, with a PSK or certificates | The **device** (often a certificate) **and the user** (password, MFA, through AAA) |
| **Usual protocol** | **IPsec** with IKEv1 or IKEv2 | **TLS and DTLS** ("SSL VPN") or **IKEv2/IPsec** |
| **Typical Cisco headend** | ISR or Catalyst 8000 router, Secure Firewall (FTD or ASA) | Secure Firewall (FTD or ASA), or an IOS XE router with FlexVPN |

## Three kinds of remote access

"SSL VPN" and "IPsec VPN" are **different technologies**, not two halves of one. An SSL VPN uses TLS and has nothing to do with IPsec. Remote access comes in three flavors:

| RA type | Client needed? | Protocol and port | What the user gets |
|---|---|---|---|
| **IPsec RA** | Yes, Secure Client | **IKEv2** (UDP 500 / 4500) + **ESP** | Full network access, like being on the LAN |
| **Client SSL VPN** | Yes, Secure Client | **TLS** on TCP 443, then **DTLS** on UDP 443 for performance | Full network access |
| **Clientless SSL VPN** | **No**, a browser | **HTTPS** to a portal on the headend | **Limited**: links to specific web apps and file shares |

Two details worth knowing:

- **Why DTLS?** Secure Client starts on TLS over TCP, then adds a **DTLS** tunnel over UDP. Tunneling TCP inside TCP suffers when packets are lost, because both layers retransmit. DTLS gives the same protection without that problem, and the client falls back to TLS if UDP 443 is blocked.
- **Clientless is an ASA feature.** Secure Firewall Threat Defense (FTD) supports Secure Client with SSL or IKEv2, but **not clientless**. Configuring RA on FTD is topic 2.9.

The word "SSL" survives only in product names. Every "SSL VPN" today runs **TLS 1.2 or 1.3**; SSL itself is [deprecated](/ccnp-security/phishing-defense-cryptography#ssl-and-tls).

## Full tunnel and split tunnel

Once a remote user is connected, **which of their traffic goes through the tunnel?**

| | **Full tunnel** | **Split tunnel** |
|---|---|---|
| What goes in the tunnel | **Everything**, internet traffic included | Only traffic for **corporate subnets** (or everything except a list) |
| Internet traffic | Hairpins through the headend, where your security stack inspects it | Goes **directly** from the user's network |
| Security | Stronger: one inspection point, one policy | Weaker: internet traffic bypasses corporate controls unless something else (DNS-layer security, a cloud proxy) covers it |
| Cost | More headend bandwidth, more latency | Less load, faster SaaS and video |

Many designs use a middle path: split tunnel with **exceptions** for trusted, high-volume services such as video conferencing, and cloud security (Umbrella or Secure Access) covering whatever goes direct.

Split tunneling is question 3 from [the three questions](#three-questions-every-vpn-answers) again: it's a **traffic selector** for remote access.

---

# VPN protocols: who provides what

A complete VPN needs **authentication, encryption and integrity**. Some protocols provide all three. Others only build a tunnel, and have to be **combined** with one that protects it.

![Which VPN protocol provides what, as a grid: IPsec and TLS or DTLS provide authentication, encryption and integrity; GRE carries multicast and non-IP traffic but has no security; L2TP carries Layer 2 frames with no encryption; PPTP's protection is broken; MPLS separates traffic without encrypting it; the combinations GRE over IPsec and L2TP over IPsec get the tunneling features from the first protocol and all of the security from IPsec](img/09/fig-02-protocol-capabilities.webp)

| Protocol | Authentication | Encryption | Integrity | What it's for | On the wire |
|---|---|---|---|---|---|
| **IPsec (ESP)** | Yes | Yes | Yes | Protecting **IP packets**: the VPN workhorse | IP protocol 50, or UDP 4500 with NAT-T; IKE on UDP 500 |
| **TLS / DTLS** | Yes (certificates) | Yes | Yes | Remote-access "SSL VPN" | TCP 443 / UDP 443 |
| **GRE** | No | No | No | A tunnel that carries **multicast, broadcast and non-IP** traffic, so routing protocols can run over it | IP protocol 47 |
| **L2TP** | Weak (tunnel only) | No | No | Tunneling **Layer 2 (PPP) frames** | UDP 1701 |
| **PPTP** | MS-CHAPv2 (broken) | MPPE (weak) | No | Legacy Microsoft remote access. **Don't use it** | TCP 1723 + GRE |
| **L2F** | No | No | No | Legacy Cisco protocol, replaced by L2TP | UDP 1701 |
| **MPLS L3VPN** | No | No | No | **Separating** customers on a provider network | MPLS labels |

**The pattern:** when a protocol builds tunnels but doesn't protect them, it rides inside IPsec.

| Combination | The first protocol adds | IPsec adds |
|---|---|---|
| **GRE over IPsec** | Multicast and non-IP, so OSPF or EIGRP can run between sites | Encryption, integrity, peer authentication |
| **L2TP over IPsec** | Layer 2 frames and per-user PPP sessions | Encryption, integrity, peer authentication |

Plain crypto-map IPsec carries **unicast IP only**. That's the single most useful reason to know GRE: if a scenario needs a routing protocol across an encrypted link, the answer is **GRE over IPsec**, a [VTI](#crypto-maps-and-virtual-tunnel-interfaces), or a design built on them such as DMVPN.

---

# IPsec and IKE: who does what

IPsec splits the work into two planes. Mixing them up is the root of most confusion about phases and SAs.

| | **Control plane: IKE** | **Data plane: ESP** |
|---|---|---|
| Job | Authenticate the peers, agree on algorithms, create keys | Encrypt and authenticate the user's packets |
| Runs on | **UDP 500**, then **UDP 4500** if NAT is detected | **IP protocol 50**, or inside UDP 4500 with NAT-T |
| Produces | Security associations | Protected packets, each tagged with an SPI |
| Covered in | This topic | [AH and ESP](/ccnp-security/phishing-defense-cryptography#ah-and-esp) |

A **security association (SA)** is an agreement between two peers about **how** to protect traffic: algorithms, keys and a lifetime. Each SA has an **SPI** (security parameter index), a number carried in every ESP packet so the receiver knows which keys to use.

Three names you'll see for the same family:

- **ISAKMP** (RFC 2408) is the **framework**: message formats and the idea of SAs. That's why IOS IKEv1 commands say `crypto isakmp`.
- **IKE** is the **protocol** that runs inside that framework and does the actual key exchange. IKEv1 is RFC 2409; **IKEv2** (RFC 7296) dropped the ISAKMP layering and is one self-contained protocol.
- **Oakley** is the Diffie-Hellman-based key exchange IKEv1 borrowed. You'll only meet it in history questions.

---

# IKEv1, step by step

IKEv1 builds a tunnel in **two phases**. Phase 1 builds a secure channel **between the two gateways**. Phase 2 uses that channel to negotiate how **user data** is protected.

**Phase 1 secures the conversation. Phase 2 secures the data.**

![The IKEv1 exchange as a message ladder between R2 and R3: main mode sends six messages in three pairs, the first pair agreeing on a Phase 1 policy, the second exchanging Diffie-Hellman values and nonces, and the third exchanging identities and authentication hashes already encrypted; the IOS state moves from MM_NO_STATE to MM_SA_SETUP to MM_KEY_EXCH to QM_IDLE; quick mode then sends three encrypted messages that agree on the transform set, proxy identities and optional PFS, creating two one-way IPsec SAs; a side lane shows aggressive mode squeezing Phase 1 into three messages with the identity and authentication hash sent before encryption](img/09/fig-03-ikev1-exchange.webp)

## Phase 1 and Phase 2 compared

| | **Phase 1** | **Phase 2** |
|---|---|---|
| **Exchange** | **Main mode** (6 messages) or **aggressive mode** (3) | **Quick mode** (3 messages) |
| **Builds** | **One ISAKMP SA**: the management tunnel. It's **bidirectional** | **IPsec SAs** for user data. Each is **one-way**, so they come in **pairs** |
| **Protects** | The **negotiation** itself (control plane) | The **user's packets** (data plane) |
| **Authentication** | **Negotiated here**: PSK, RSA signatures (certificates) or RSA encrypted nonces | **Inherited** from Phase 1 |
| **Encryption and integrity** | Negotiated in the **ISAKMP policy** | Negotiated in the **transform set** |
| **Diffie-Hellman** | **Always**: the DH group in the policy | **Optional**: only with **PFS** |
| **What to protect** | Not negotiated | **Proxy identities**, from the crypto ACL |
| **IPsec protocol and mode** | Not applicable | **ESP** (or AH), **tunnel** or transport mode |
| **IOS default lifetime** | **86,400 seconds** (24 hours) | **3,600 seconds** or 4,608,000 KB, whichever comes first |
| **IOS config** | `crypto isakmp policy`, `crypto isakmp key` | `crypto ipsec transform-set`, the ACL, `crypto map` |
| **Verify with** | `show crypto isakmp sa` | `show crypto ipsec sa` |

The two lifetimes are **independent**. Setting `lifetime 86400` in the ISAKMP policy does nothing to Phase 2, which keeps its one-hour default unless you set `crypto ipsec security-association lifetime seconds` globally or `set security-association lifetime seconds` in the crypto map. You can see the 3,600-second default in the [lab's `show crypto map` output](/ccnp-security/labs/ipsec-ikev1-site-to-site-vpn#step-4-crypto-map-and-apply-it).

## What each main mode message pair does

Main mode isn't six random packets. It's **three pairs**, and each pair answers one question. Knowing the pairs is what lets you read a stuck tunnel.

| Messages | What's exchanged | Encrypted? | IOS state after it (initiator) | If it fails here |
|---|---|---|---|---|
| **1 and 2** | The initiator's **policy proposals**; the responder picks one | No | `MM_SA_SETUP` | No matching policy: stuck at **`MM_NO_STATE`** |
| **3 and 4** | **Diffie-Hellman public values and nonces**. Both sides now compute the same keys | No | `MM_KEY_EXCH` | Rare; the peers already agreed on a group |
| **5 and 6** | Each peer's **identity** and **authentication proof** (a hash keyed by the PSK, or a signature) | **Yes**, with the new keys | `QM_IDLE` | Wrong PSK: the peer can't verify or decrypt it, stuck at **`MM_KEY_EXCH`** |

That table explains the two most common IKEv1 failures:

- **Policy mismatch** fails in the **first** pair, before any keys exist, so the state never leaves **`MM_NO_STATE`**.
- **PSK mismatch** fails in the **third** pair. The DH exchange worked, so the state reached **`MM_KEY_EXCH`**, but the keys derived from two different PSKs don't match. The peer sees messages it can't make sense of and logs `%CRYPTO-4-IKMP_BAD_MESSAGE: ... failed its sanity check or is malformed`.

`QM_IDLE` means Phase 1 is **done and healthy**: the ISAKMP SA is up and idle, ready for quick mode. It doesn't mean "stuck in quick mode."

## Main mode and aggressive mode

| | **Main mode** | **Aggressive mode** |
|---|---|---|
| Messages | **6** | **3** |
| Identity | Sent in messages 5 and 6, **encrypted** | Sent in the **first two messages**, **in cleartext** |
| Authentication hash | Encrypted | The responder's hash is sent **before encryption exists** |
| With a PSK | Safe against passive capture | An attacker who captures message 2 can **brute-force the PSK offline** |
| Peer identity with PSK | Must be the **IP address**, because the responder has to pick the key before it can decrypt the identity | Can be a **name** (a group name), because the identity arrives in cleartext |
| Where you'll find it | Every site-to-site default | Legacy IKEv1 remote access with group PSKs, and misconfigured devices |
| Recommendation | Use it | **Disable it**: `crypto isakmp aggressive-mode disable` |

That "peer identity" row is why aggressive mode existed at all. Remote-access clients have unpredictable IP addresses, so with a PSK the headend couldn't pick the right key from the address. Aggressive mode let them send a group name instead, at the cost of exposing a crackable hash. IKEv2 solved this properly with EAP and certificates.

## Quick mode, PFS and Diffie-Hellman groups

Quick mode is **three messages**, all encrypted under the ISAKMP SA. It negotiates:

- **The transform set**: ESP or AH, the encryption, the integrity algorithm, and tunnel or transport mode.
- **The proxy identities**: which source and destination networks this SA protects. They come from the crypto ACL.
- **PFS**, optionally, and the **Phase 2 lifetime**.

The result is **two IPsec SAs**, one in each direction, each with its own SPI. That's why `show crypto session` reports **`Active SAs: 2`** for a single working tunnel.

**Perfect Forward Secrecy (PFS)** adds a **fresh Diffie-Hellman exchange** inside quick mode. Without PFS, Phase 2 keys are derived from the Phase 1 keying material, so anyone who later recovers that material can derive every Phase 2 key that came from it. With PFS, each Phase 2 negotiation has **independent keys**: recovering one doesn't unlock the others. The cost is one more DH computation at every rekey. The idea is the same [forward secrecy](/ccnp-security/phishing-defense-cryptography#hybrid-cryptography-and-forward-secrecy) that TLS 1.3 makes mandatory.

The **Diffie-Hellman group** sets the strength of every key exchange:

| Group | Type and size | Status |
|---|---|---|
| 1, 2, 5 | MODP 768, 1024, 1536-bit | **Weak. Don't use.** Group 2 still appears in older lab configs, including this topic's lab |
| 14 | MODP 2048-bit | Acceptable minimum |
| 15, 16 | MODP 3072, 4096-bit | Strong, slower |
| **19, 20, 21** | **ECP 256, 384, 521-bit** (elliptic curve) | **Recommended**: strong and fast |
| 24 | MODP 2048-bit with a 224-bit subgroup | **Deprecated** |

Both peers must agree on a group in Phase 1 and, if PFS is on, in Phase 2. A **higher number isn't automatically stronger** (group 24 is weaker than 14), so know the recommended ones by name.

## Lifetimes: the one Phase 1 setting that doesn't have to match

Encryption, hash, authentication method and DH group **must match** for a Phase 1 policy to be accepted. The **lifetime doesn't**: IOS settles on the **shorter** of the two. In this topic's lab, one router had a typo (`84600` instead of `86400`) and the tunnel still came up; the countdown in `show crypto session detail` proves which value won. The [lab walks through the evidence](/ccnp-security/labs/ipsec-ikev1-site-to-site-vpn#read-the-session-summary). Other vendors' gateways can be stricter, so configure the same lifetime on both ends anyway.

## Interesting traffic: why a configured tunnel can be down

An IKEv1 crypto map is **on demand**. Configuring both routers builds nothing. The tunnel only negotiates when a packet arrives that:

1. is **routed out the interface** that has the crypto map, **and**
2. **matches the crypto ACL** ("interesting traffic").

So `show crypto isakmp sa` being **empty right after configuration is normal**. Send traffic between the protected networks and the tunnel comes up. The **first packet is usually lost**, because it's the one that triggers Phase 1 and Phase 2. Once up, the tunnel stays up for the SA lifetime and rekeys while traffic keeps flowing.

**The crypto ACLs on the two peers must be mirror images.** R2 protects `172.16.2.0/24 → 172.16.3.0/24`; R3 must protect `172.16.3.0/24 → 172.16.2.0/24`. If they don't describe the same flow, Phase 1 succeeds and Phase 2 fails, because the responder can't accept the proxy identities it was offered.

The crypto ACL is a **selector**, not a firewall: `permit` means "encrypt this," and anything it doesn't match goes out **in cleartext**. That's why a ping from the router itself fails across a working tunnel: it's sourced from the WAN address, which isn't in the ACL. The [lab demonstrates it](/ccnp-security/labs/ipsec-ikev1-site-to-site-vpn#break-6-ping-from-the-router-itself).

## The IKEv1 configuration, piece by piece

This is R2 from the lab. R3 is identical except for the **peer address** and the **ACL direction**.

```
! ---- Phase 1: how the gateways protect their negotiation ----
crypto isakmp policy 10
 encr aes 128
 hash sha
 authentication pre-share
 group 2
 lifetime 86400
crypto isakmp key S3cr3tk3y! address 33.3.3.3
!
! ---- Phase 2: how user data is protected ----
crypto ipsec transform-set S2S_TRANSFORM_SET esp-aes esp-sha-hmac
 mode tunnel
!
! ---- Which traffic goes in ----
access-list 100 permit ip 172.16.2.0 0.0.0.255 172.16.3.0 0.0.0.255
!
! ---- Tie it together and switch it on ----
crypto map S2S_CRYPTO_MAP 10 ipsec-isakmp
 set peer 33.3.3.3
 set transform-set S2S_TRANSFORM_SET
 match address 100
!
interface GigabitEthernet0/0
 crypto map S2S_CRYPTO_MAP
```

> **Lab values only.** `S3cr3tk3y!`, group 2 and SHA-1 come from a training lab and are deliberately weak. The [hardened version](/ccnp-security/labs/ipsec-ikev1-site-to-site-vpn#harden-it) is in the lab. Never reuse lab keys.

| Command | Phase | Answers which question | Role |
|---|---|---|---|
| `crypto isakmp policy 10` | 1 | How (and who, via `authentication`) | One Phase 1 proposal. Lower number = tried first |
| `crypto isakmp key ... address` | 1 | Who | The PSK, bound to the peer's IP address |
| `crypto ipsec transform-set` | 2 | How | ESP with AES and HMAC-SHA, tunnel mode |
| `access-list 100` | 2 | Which traffic | The interesting traffic, which becomes the proxy identities |
| `crypto map ... ipsec-isakmp` | 2 | Ties all three | Binds **peer + transform set + ACL** into one entry |
| `crypto map` on the interface | | | **Activates** it on the outside interface |

**Order to build it:** ISAKMP policy and key, then transform set, then ACL, then crypto map, then apply the map to the interface. Applying the map last means nothing is half-active while you type.

![How R2 decides what to do with a packet from PC-2: it arrives on G1/0, the routing table must send it out G0/0 where the crypto map lives, and it must match ACL 100; a packet that fails either test leaves in cleartext and dies at the internet router, which has no route to 172.16.0.0; a matching packet with no IPsec SA triggers IKE Phase 1 and Phase 2 and is usually dropped; once the SAs exist, it's encrypted with ESP in tunnel mode behind a new header from 22.2.2.2 to 33.3.3.3](img/09/fig-04-crypto-map-path.webp)

## Reading IKEv1 states in the real world

| What you see | Phase | Most likely cause |
|---|---|---|
| No SA at all, nothing in `debug crypto isakmp` | | No interesting traffic, traffic not routed out the crypto-map interface, or the map isn't applied |
| Stuck at **`MM_NO_STATE`** | 1 | **Policy mismatch** (encryption, hash, auth or DH group), or the peer isn't answering on UDP 500 |
| Stuck at **`MM_KEY_EXCH`**, `IKMP_BAD_MESSAGE` on the peer | 1 | **PSK mismatch** |
| **`QM_IDLE`**, no IPsec SA, `PROPOSAL_NOT_CHOSEN` | 2 | **Transform set** or PFS mismatch |
| **`QM_IDLE`**, no IPsec SA, `proxy identities not supported` | 2 | **Crypto ACLs not mirrored** |
| SAs up, **encaps climbing, decaps stuck** | Data | The tunnel is fine; the **return path beyond it** is broken |

Every row is reproduced, with real output, in the [IKEv1 site-to-site lab](/ccnp-security/labs/ipsec-ikev1-site-to-site-vpn).

---

# IKEv2

**IKEv2** (RFC 7296) does the same job as IKEv1 with fewer messages and more built in. It still has two stages, but the names change, and the first stage builds the first data SA at the same time.

![IKEv1 and IKEv2 side by side as message ladders: IKEv1 uses six main mode messages to build the ISAKMP SA and three quick mode messages to build the IPsec SAs, nine in total; IKEv2 uses two IKE_SA_INIT messages to agree on algorithms and run Diffie-Hellman, then two encrypted IKE_AUTH messages that authenticate both peers and create the first Child SA, four in total, with CREATE_CHILD_SA used later for more SAs or rekeys](img/09/fig-05-ikev1-vs-ikev2.webp)

## The names change

| | IKEv1 | IKEv2 |
|---|---|---|
| First stage | Phase 1: **main mode** or **aggressive mode** | **`IKE_SA_INIT`** (2 messages) + **`IKE_AUTH`** (2 messages) |
| SA it creates | **ISAKMP SA** | **IKE SA** |
| Second stage | Phase 2: **quick mode** (3 messages) | Built into `IKE_AUTH`; **`CREATE_CHILD_SA`** for extra SAs and rekeys |
| Data SAs | **IPsec SAs** | **Child SAs** (they're still IPsec SAs) |
| Messages to the first data SA | **9** with main mode, **6** with aggressive | **4** |

IKEv2 adds one new term: the **PRF** (pseudorandom function), the algorithm that turns the DH secret and nonces into keys. It's negotiated with encryption, integrity and the DH group. On IOS, it defaults to match the integrity algorithm; with an AEAD cipher such as AES-GCM there's no separate integrity algorithm, so you set the PRF explicitly.

## What IKEv2 fixes

| | **IKEv1** | **IKEv2** |
|---|---|---|
| **Standard** | RFC 2409, plus add-on RFCs | **RFC 7296**, one document |
| **Messages** | 6 to 9 | **4** |
| **NAT traversal** | An **add-on** (RFC 3947). Cisco IOS enables it by default | **Part of the base protocol** |
| **Dead peer detection** | An **add-on** (RFC 3706), optional | **Liveness checks built in** |
| **DoS resistance** | The responder builds state for every first packet | **Cookies**: under load, the responder makes the initiator prove its address before it creates state |
| **Reliability** | Some messages, such as the last quick mode message and notifications, are never acknowledged | **Every request gets a response**; the initiator retransmits until it does |
| **User authentication** | Add-ons: **XAUTH** and mode config | **EAP** built in, so users authenticate against RADIUS, AD or MFA |
| **Authentication method** | **Same on both ends** | **Asymmetric**: each side chooses, for example certificate on the headend and EAP for the user |
| **Mobility** | The tunnel breaks when an address changes | **MOBIKE** (RFC 4555) moves the SA to a new address |
| **Selector mismatch** | Phase 2 simply fails | The responder can **narrow** the selectors to what it allows |
| **Cisco use** | Legacy crypto maps, older remote access | **FlexVPN**, Secure Firewall VPNs, Secure Client IPsec |

**Bottom line:** IKEv2 is faster, more reliable, harder to attack and better at remote access. IKEv1 is still everywhere in existing site-to-site tunnels, which is why both are on the exam. New deployments should use IKEv2.

## The IKEv2 configuration on IOS

IKEv2 config is **modular**: each block does one job and points to the next. Here's R2 from the lab rebuilt with IKEv2. The Phase 2 objects (transform set, ACL, crypto map) barely change; the map just points to an IKEv2 profile.

```
! ---- IKE SA: algorithms ----
crypto ikev2 proposal S2S_PROPOSAL
 encryption aes-cbc-256
 integrity sha256
 group 19 14
!
crypto ikev2 policy S2S_POLICY
 proposal S2S_PROPOSAL
!
! ---- IKE SA: who, and how they prove it ----
crypto ikev2 keyring S2S_KEYRING
 peer R3
  address 33.3.3.3
  pre-shared-key S3cr3tk3y!
!
crypto ikev2 profile S2S_IKEV2_PROFILE
 match identity remote address 33.3.3.3 255.255.255.255
 authentication remote pre-share
 authentication local pre-share
 keyring local S2S_KEYRING
!
! ---- Child SA: same Phase 2 objects as IKEv1 ----
crypto ipsec transform-set S2S_TRANSFORM_SET esp-aes 256 esp-sha256-hmac
 mode tunnel
access-list 100 permit ip 172.16.2.0 0.0.0.255 172.16.3.0 0.0.0.255
!
crypto map S2S_CRYPTO_MAP 10 ipsec-isakmp
 set peer 33.3.3.3
 set transform-set S2S_TRANSFORM_SET
 set ikev2-profile S2S_IKEV2_PROFILE
 match address 100
!
interface GigabitEthernet0/0
 crypto map S2S_CRYPTO_MAP
```

> **Lab values only.** Never reuse lab keys on real equipment.

| IKEv2 block | Job | IKEv1 equivalent |
|---|---|---|
| `crypto ikev2 proposal` | Encryption, integrity, PRF and DH groups. You can list several; the peers pick a common one | The `encr`, `hash` and `group` lines of `crypto isakmp policy` |
| `crypto ikev2 policy` | Chooses which proposals to offer (and can match on local address or VRF) | The policy number and ordering |
| `crypto ikev2 keyring` | Stores PSKs per peer | `crypto isakmp key ... address` |
| `crypto ikev2 profile` | **Who** the peer is (`match identity`), **how each side proves it** (`authentication local` and `remote`, separately), and which keyring or trustpoint to use | `authentication` in the ISAKMP policy |
| `set ikev2-profile` in the crypto map | Tells the map to negotiate with IKEv2 | Nothing; crypto maps default to IKEv1 |

The **separate `authentication local` and `authentication remote` lines** are asymmetric authentication in action. Change `remote` to `rsa-sig` or `eap` and the two sides prove themselves differently, which IKEv1 can't do. PSKs can also be written directly in the profile instead of a keyring, as the [PSK and certificate comparison](/ccnp-security/phishing-defense-cryptography#authenticating-the-peers-pre-shared-keys-and-certificates) shows; certificates use a PKI trustpoint, and EAP uses AAA.

Recent IOS XE releases also ship **IKEv2 smart defaults**: a built-in proposal, policy, transform set and IPsec profile. With them, a working FlexVPN config needs little more than a keyring and a profile. Writing every block out, as above, is clearer while you learn and is what you'll see on the exam.

---

# Crypto maps and virtual tunnel interfaces

Topic 1.6 names **virtual tunnel interfaces (VTIs)** alongside standards-based IPsec, and the difference is one of the most practical in VPN design. A crypto map is **policy-based**: an ACL decides what's encrypted. A VTI is **route-based**: the **routing table** decides, by sending traffic into a tunnel interface.

![Policy-based versus route-based IPsec: with a crypto map, the crypto ACL attached to the physical WAN interface picks which flows are encrypted, every subnet pair needs its own ACL entry, and multicast routing protocols can't cross; with a static VTI, an ordinary tunnel interface protected by an IPsec profile encrypts everything routed into it, so static routes or OSPF and EIGRP decide what crosses, and per-interface features such as QoS, ACLs and NetFlow apply to the tunnel](img/09/fig-06-crypto-map-vs-vti.webp)

| | **Crypto map** (policy-based) | **VTI** (route-based) |
|---|---|---|
| What decides what's encrypted | A **crypto ACL** | The **routing table**: anything routed into `Tunnel0` |
| Applied to | The physical outside interface | A logical **tunnel interface** with its own IP |
| Adding a subnet | Edit the ACL on **both** peers | Add a route, or let a routing protocol learn it |
| Routing protocols, multicast | **No** | **Yes** |
| Per-tunnel features | Hard to apply | QoS, ACLs, NetFlow, NAT on the tunnel interface |
| Proxy identities | The ACL's subnets | `0.0.0.0/0 ↔ 0.0.0.0/0` (everything routed in) |
| Status | Legacy, still very common | **Preferred** for new designs; the building block of DMVPN and FlexVPN |

A **static VTI** (SVTI) is a point-to-point tunnel to one peer. A **dynamic VTI** (DVTI) is created from a template on a hub each time a peer connects, which is how one headend serves many branches or remote users.

The same tunnel as the lab, rebuilt as a static VTI on R2 (the IKEv1 Phase 1 policy and key stay as they were):

```
crypto ipsec profile S2S_IPSEC_PROFILE
 set transform-set S2S_TRANSFORM_SET
!
interface Tunnel0
 ip address 10.23.23.2 255.255.255.252
 tunnel source GigabitEthernet0/0
 tunnel destination 33.3.3.3
 tunnel mode ipsec ipv4
 tunnel protection ipsec profile S2S_IPSEC_PROFILE
!
ip route 172.16.3.0 255.255.255.0 Tunnel0
```

No ACL and no crypto map. The **route** is the selector: traffic for `172.16.3.0/24` goes into `Tunnel0`, and everything that enters `Tunnel0` is encrypted.

---

# The 1.6 deployment types at a glance

The blueprint lists six deployment types. They're all built from the same pieces, IPsec ESP with keys from IKE (or TLS for SSL VPN), combined differently:

| Deployment | Shape | Keys from | How traffic is selected | Pick it when |
|---|---|---|---|---|
| **Standards-based IPsec** (crypto map) | Point-to-point, site-to-site | IKEv1 or IKEv2 | **Crypto ACL** | Interoperating with another vendor's gateway; a few static tunnels |
| **VTI** (static or dynamic) | Point-to-point, or hub with templates | IKEv1 or IKEv2 | **Routing** into a tunnel interface | You need routing protocols, multicast or per-tunnel features |
| **DMVPN** | **Hub-and-spoke** with **dynamic spoke-to-spoke** tunnels | IKEv1 or IKEv2 | Routing over **mGRE**; **NHRP** finds the other spoke's address | Many branches that also talk to each other directly |
| **FlexVPN** | Any: site-to-site, hub-and-spoke, spoke-to-spoke **and remote access** | **IKEv2 only** | Routing over VTIs | One IKEv2 framework for every VPN on IOS XE |
| **GETVPN** | **Tunnel-less**, any-to-any | A **group key** from a **key server** (GDOI, UDP 848), not per-pair IKE | **The original IP header is kept**, so the existing private WAN routing still works | Encrypting a private **MPLS** WAN without building tunnels |
| **SSL VPN** | Remote access | **TLS** handshake | Split-tunnel lists on the headend | Users with Secure Client, or a browser for clientless |

Two distinctions the exam checks:

- **DMVPN vs. FlexVPN:** DMVPN is a **design** (mGRE + NHRP + IPsec) that runs on IKEv1 or IKEv2. FlexVPN is Cisco's **IKEv2-only framework** that covers site-to-site and remote access with one set of commands.
- **GETVPN vs. everything else:** every other type builds **point-to-point SAs** between pairs of peers. GETVPN gives **every member the same keys**, and because it **preserves the original IP header**, it only works over a **private** WAN; across the internet, private addresses in that header wouldn't be routable.

---

# Exam traps

- **VPN = protection across an untrusted network.** MPLS is private and separated, **not encrypted**.
- **Site-to-site is transparent to users; remote access needs a client** (or a browser for clientless).
- **SSL VPN is TLS, not IPsec.** Client SSL VPN gives full access over TLS and DTLS; clientless gives a browser portal with limited access, and only ASA supports it, not FTD.
- **Full tunnel inspects everything; split tunnel sends internet traffic direct.**
- **GRE, L2TP, L2F, MPLS: no encryption.** Pair GRE or L2TP with IPsec. **PPTP is broken.**
- **Phase 1 → one bidirectional ISAKMP SA. Phase 2 → a pair of one-way IPsec SAs** (`Active SAs: 2`).
- **Main mode 6 messages, aggressive 3, quick mode 3.** Aggressive mode sends identity in cleartext and exposes the PSK hash to offline cracking.
- **PFS = a fresh DH exchange in Phase 2.** It's optional in IKEv1.
- **IOS lifetimes:** Phase 1 **86,400 s**, Phase 2 **3,600 s**. They're set separately.
- **Configured isn't up:** an IKEv1 crypto map waits for **interesting traffic**, and the first packet is usually lost.
- **`MM_NO_STATE` = policy mismatch. `MM_KEY_EXCH` = PSK mismatch. `QM_IDLE` = Phase 1 healthy.**
- **The crypto ACLs must mirror.** Traffic outside them leaves in cleartext.
- **IKEv2 = 4 messages, IKE SA + Child SA**, built-in NAT-T and liveness checks, EAP, asymmetric auth, MOBIKE.
- **Crypto map = policy-based (ACL); VTI = route-based (routing table).** Routing protocols need a VTI or GRE.
- **GETVPN = tunnel-less group keys over a private WAN. FlexVPN = IKEv2 only. DMVPN = mGRE + NHRP + IPsec.**

---

# Quick reference

| Concept | One-liner |
|---|---|
| Site-to-site | Network to network through gateways; users don't see it |
| Remote access | One device to a network with Secure Client, or a browser portal |
| Client SSL VPN | TLS on TCP 443, then DTLS on UDP 443; full access |
| Clientless SSL VPN | Browser HTTPS portal; limited apps; ASA only |
| Full / split tunnel | All traffic to the headend / only corporate traffic |
| GRE | IP 47; multicast and non-IP; no security |
| ISAKMP SA | IKEv1 Phase 1; one, bidirectional; protects negotiation |
| IPsec SA | Phase 2; one-way, so a pair; protects data; identified by an SPI |
| Main / aggressive mode | 6 messages, identity hidden / 3 messages, identity exposed |
| Quick mode | 3 encrypted messages; transform set, proxy IDs, PFS |
| Transform set | ESP or AH, encryption, integrity, mode |
| Proxy identities | The protected subnets, from the crypto ACL; must mirror |
| PFS | Fresh DH per Phase 2 negotiation; independent keys |
| DH groups | Avoid 1, 2, 5 and 24; 14 minimum; prefer 19, 20, 21 |
| IKEv2 | RFC 7296; 4 messages; IKE SA + Child SA; EAP, MOBIKE, cookies |
| Crypto map vs. VTI | ACL picks traffic vs. routing picks traffic |
| DMVPN | mGRE + NHRP + IPsec; dynamic spoke-to-spoke |
| FlexVPN | IKEv2-only framework for site-to-site and remote access |
| GETVPN | Group keys from a key server (GDOI); header preserved; private WAN |

---

# Lab for this topic

[IKEv1 site-to-site VPN lab (real IOS)](/ccnp-security/labs/ipsec-ikev1-site-to-site-vpn): build the crypto-map tunnel from this topic between two routers, verify each phase with the right `show` command, watch main mode and quick mode in `debug`, then break it six ways (PSK, Phase 1 policy, transform set, ACL mirror, return path, router-sourced ping) and harden it with AES-256, SHA-256, DH group 14 and PFS.

---

# Check yourself

<details><summary>1. Two offices must exchange traffic securely over the internet without users doing anything. Which VPN type, which devices build it, and which protocol is most common?</summary>

A **site-to-site** VPN. The **edge routers or firewalls** at each office are the tunnel endpoints, and the users never see it. **IPsec** is the usual protocol.

</details>

<details><summary>2. A company already has an MPLS WAN between sites. Why might it still encrypt that traffic, and which deployment type was designed for this?</summary>

MPLS **separates** customers but **doesn't encrypt**; traffic crosses the provider's network in cleartext. **GETVPN** encrypts a private WAN with group keys and keeps the original IP header, so the existing routing keeps working without building tunnels.

</details>

<details><summary>3. Correct this statement: "A clientless SSL VPN uses IPsec and TLS together to give full network access."</summary>

A clientless SSL VPN uses **TLS only** (an HTTPS portal in the browser), not IPsec, and gives **limited** access to selected web apps. Full network access needs Secure Client, over **TLS and DTLS** or over **IKEv2/IPsec**.

</details>

<details><summary>4. A remote-access design sends only corporate subnets through the tunnel. What's this called, and what's the security trade-off?</summary>

**Split tunneling.** It saves headend bandwidth and speeds up SaaS, but the user's internet traffic **bypasses corporate inspection** unless something else, such as DNS-layer security or a cloud proxy, covers it. A full tunnel inspects everything.

</details>

<details><summary>5. OSPF must run between two sites over an encrypted link. Why doesn't a plain crypto map work, and what does?</summary>

A crypto map encrypts **unicast IP** selected by an ACL; it can't carry OSPF's **multicast** hellos. Use **GRE over IPsec** or a **VTI**, which is an interface that routing protocols can run over.

</details>

<details><summary>6. Which IKEv1 phase creates the SA that protects user data, what is that SA called, and why are there two of them?</summary>

**Phase 2 (quick mode)** creates the **IPsec SAs**. IPsec SAs are **one-way**, so a working tunnel has one inbound and one outbound SA, which is why `show crypto session` shows `Active SAs: 2`.

</details>

<details><summary>7. `show crypto isakmp sa` is stuck at MM_NO_STATE. In which message pair did main mode fail, and what's the usual cause?</summary>

The **first pair** (messages 1 and 2), where the peers try to agree on a policy. The usual cause is a **Phase 1 policy mismatch**: encryption, hash, authentication method or DH group. It can also mean the peer isn't answering on UDP 500 at all.

</details>

<details><summary>8. The state reaches MM_KEY_EXCH and stays there, and the peer logs IKMP_BAD_MESSAGE. What's wrong, and why does it fail at this point?</summary>

A **pre-shared key mismatch**. The Diffie-Hellman exchange (messages 3 and 4) succeeded, but each side mixes its own PSK into the keys, so messages 5 and 6, encrypted and authenticated with those keys, can't be verified by the peer.

</details>

<details><summary>9. Why is aggressive mode with a pre-shared key discouraged?</summary>

Aggressive mode sends the **identity in cleartext** and the responder's **authentication hash before any encryption exists**. An attacker who captures it can **brute-force the PSK offline**. Use main mode, prefer certificates, and disable aggressive mode with `crypto isakmp aggressive-mode disable`.

</details>

<details><summary>10. Both routers are fully configured, but `show crypto isakmp sa` is empty. Is the VPN broken?</summary>

Not necessarily. An IKEv1 crypto map negotiates only when **interesting traffic** (matching the crypto ACL and routed out the crypto-map interface) arrives. Send traffic between the protected LANs; the first packet is usually lost while the tunnel builds.

</details>

<details><summary>11. Phase 1 is up (QM_IDLE), but there's no IPsec SA and the responder logs "proxy identities not supported." What's wrong?</summary>

The **crypto ACLs aren't mirror images**, so the responder can't accept the protected networks the initiator proposed. Make each router's ACL the exact reverse of the other's.

</details>

<details><summary>12. The ISAKMP policy says `lifetime 86400`. What lifetime do the IPsec SAs get on IOS, and how do you change it?</summary>

The IOS default of **3,600 seconds** (or 4,608,000 KB). The ISAKMP lifetime only applies to Phase 1. Set `crypto ipsec security-association lifetime seconds` globally, or `set security-association lifetime seconds` in the crypto map entry.

</details>

<details><summary>13. Name four things IKEv2 has built in that IKEv1 needed add-ons for, or didn't have.</summary>

Any four of: **NAT traversal**, **liveness (dead peer) checks**, **EAP** user authentication, **asymmetric authentication**, **MOBIKE**, **anti-DoS cookies**, and **reliable acknowledged exchanges**. It also needs only **4 messages** to build the first Child SA.

</details>

<details><summary>14. An IKEv2 profile has `authentication local rsa-sig` and `authentication remote eap`. What does that allow, and could IKEv1 do it?</summary>

**Asymmetric authentication**: the headend proves itself with a **certificate** while the remote user authenticates with **EAP** against RADIUS or AD. IKEv1 can't; both ends must use the same method.

</details>

<details><summary>15. What's the difference between a crypto map and a VTI in how they choose which traffic to encrypt?</summary>

A crypto map is **policy-based**: a **crypto ACL** selects the flows. A VTI is **route-based**: anything the **routing table** sends into the tunnel interface is encrypted, so adding a network means adding a route, and routing protocols can run over it.

</details>

<details><summary>16. Match each to its description: DMVPN, FlexVPN, GETVPN. (a) IKEv2-only framework for site-to-site and remote access; (b) tunnel-less group encryption for a private WAN; (c) mGRE and NHRP with dynamic spoke-to-spoke tunnels.</summary>

**DMVPN = (c). FlexVPN = (a). GETVPN = (b).**

</details>
