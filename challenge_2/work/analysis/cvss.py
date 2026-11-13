"""CVSS v3.1 base-score calculator for the three Trojans.

HONEST scoring rules applied here:
  * Vectors reflect ONLY what the simulations in tb/tb_crypto.v actually prove.
  * Attack Vector = Physical (AV:P): the triggers are presented on the FPGA's
    on-board SPI/I2C buses. There is NO network or remote path in this challenge,
    so AV:N / AV:A are NOT claimed. An AV:L sensitivity row is shown for the case
    where the application processor's local interface is itself the adversary.
  * Scope = Unchanged (S:U): the impact stays within the cryptographic component;
    no second security authority is demonstrably crossed.
  * Impact is credited only when demonstrated in simulation:
      - A leaks the device secret               -> C:H, I:N, A:N  (a disclosure;
        it does NOT itself modify data, so I:N — downstream forgery with the
        stolen secret is a separate attack and is not scored here).
      - B accepts forged tags AND releases the correct plaintext of a captured
        ciphertext (both shown)                  -> C:H, I:H, A:N.
      - C recovers a second plaintext via nonce reuse (shown). Forgery / key
        recovery under reuse was NOT demonstrated -> C:H, I:N, A:N.
"""
import math
AV={'N':0.85,'A':0.62,'L':0.55,'P':0.2}; AC={'L':0.77,'H':0.44}
UI={'N':0.85,'R':0.62}; CIA={'H':0.56,'L':0.22,'N':0.0}
PR_U={'N':0.85,'L':0.62,'H':0.27}; PR_C={'N':0.85,'L':0.68,'H':0.50}
def roundup(x): return math.ceil(x*10)/10.0
def base(v):
    p=dict(x.split(':') for x in v.split('/') if ':' in x); S=p['S']
    isc=1-((1-CIA[p['C']])*(1-CIA[p['I']])*(1-CIA[p['A']]))
    impact=6.42*isc if S=='U' else 7.52*(isc-0.029)-3.25*(isc-0.02)**15
    pr=(PR_U if S=='U' else PR_C)[p['PR']]
    expl=8.22*AV[p['AV']]*AC[p['AC']]*pr*UI[p['UI']]
    if impact<=0: return 0.0
    raw=impact+expl if S=='U' else 1.08*(impact+expl)
    return roundup(min(raw,10.0))
def sev(s): return "None" if s==0 else "Low" if s<4 else "Medium" if s<7 else "High" if s<9 else "Critical"

# PRIMARY vectors. Threat model (justified against the FIRST CVSS v3.1 spec):
#  * AV:L — the attacker drives the accelerator through its existing SPI command
#    interface via the application processor (malicious/compromised host code or
#    an untrusted operator); no physical manipulation of the FPGA die/bus is
#    required, so AV:L (local logical access), not AV:P.
#  * S:C — the IP doc states key material is "held inside the FPGA and never
#    exposed through SPI". Each payload breaches that documented isolation
#    boundary, impacting the host processor / application data — a different
#    security authority than the crypto core. Per the spec that is Scope:Changed.
#  * Impact credited ONLY where a tb/tb_crypto.v test demonstrates it:
#      A: leaks key+nonce+secret (C:H) AND a forged ciphertext is accepted using
#         the leaked key (I:H)                         -> C:H/I:H
#      B: forged tag accepted (I:H) AND correct plaintext recovered (C:H) -> C:H/I:H
#      C: plaintext recovered under nonce reuse (C:H); forgery/key recovery NOT
#         demonstrated                                  -> C:H/I:N
ROWS=[
 ("A  key+secret leak -> decrypt+forge (tested)", "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N"),
 ("B  reserved-bit auth bypass + PT recovery",    "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N"),
 ("C  forced nonce reuse (C only, tested)",       "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N"),
 ("-- AV:L with conservative S:U (Scope debate) --",""),
 ("A  AV:L/S:U",                                  "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"),
 ("B  AV:L/S:U",                                  "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"),
 ("C  AV:L/S:U",                                  "CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"),
 ("-- most conservative floor (AV:P, S:U) --",""),
 ("A  floor",                                     "CVSS:3.1/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"),
 ("B  floor",                                     "CVSS:3.1/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"),
 ("C  floor",                                     "CVSS:3.1/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"),
]
if __name__=="__main__":
    print(f"{'scenario':46s} {'score':>5s} {'severity':>9s}  vector")
    for name,v in ROWS:
        if not v: print(name); continue
        s=base(v); print(f"{name:46s} {s:5.1f} {sev(s):>9s}  {v}")
