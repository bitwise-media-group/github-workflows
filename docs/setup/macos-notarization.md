---
description:
  One-time org setup of the shared Developer ID certificate and notary API key, and the consumer-side GoReleaser config.
---

# macOS notarization

[`release.yaml`](../workflows/release.md) signs and notarizes the darwin binaries of any consumer whose
`.goreleaser.yaml` has a [`notarize.macos`](https://goreleaser.com/customization/sign/notarize/) block: GoReleaser's
embedded [quill](https://github.com/anchore/quill) signs each Mach-O with a Developer ID Application certificate
(hardened runtime flag set, Apple timestamp attached) and submits it to Apple's notary service, all on the
`ubuntu-latest` runner — no macOS runner and no GoReleaser Pro. A notarized binary runs from a browser download without
a Gatekeeper prompt (the ticket is fetched online on first run; a bare Mach-O cannot be stapled), so the Homebrew cask
needs no `xattr -dr com.apple.quarantine` hook. The setup below is done **once for the organisation**: one shared
Developer ID Application certificate and one App Store Connect team API key, stored as five org secrets visible only to
the repositories that notarize. Every Developer ID Application certificate Apple issues to the team carries the
identical subject (`Developer ID Application: <Team> (<TEAMID>)` — the CSR's CN and email are not carried into it), so
per-binary certificates would only buy independent revocation at the cost of a `.p12` secret per repo.

## Prerequisites

Apple Developer Program membership current and the latest agreements accepted, signed in as the **Account Holder** — the
only role that can create Developer ID certificates. `gh auth refresh -h github.com -s admin:org` once so
`gh secret set --org` works. `quill` (`brew install quill` or `mise use -g aqua:anchore/quill`) only for the optional
`.p12` check.

## Step 1 — the shared signing certificate

Make a key and CSR, have Apple issue the certificate against it, and bundle leaf + key into a `.p12`. The CN and email
only label the CSR in the portal; Apple composes the issued subject itself.

```sh
name=bitwise-oss
dir=$(mktemp -d)
# key + CSR (RSA-2048)
openssl req -new -newkey rsa:2048 -nodes \
  -keyout "$dir/$name.key" -out "$dir/$name.certSigningRequest" \
  -subj "/emailAddress=oss@bitwisemedia.co.uk/CN=BitWise Media Group OSS Release Signing/C=GB"
```

At <https://developer.apple.com/account/resources/certificates/add>: **Software → Developer ID → Developer ID
Application**, profile type **G2 Sub-CA**, upload `$dir/$name.certSigningRequest`, then **Download**
(`developerID_application.cer`).

```sh
# p12 = leaf + key. quill attaches Apple's Developer ID G2 chain itself, so no
# `quill p12 attach-chain`; OpenSSL 3's default PBES2/AES-256 encryption decodes
# fine, so do NOT pass -legacy. `-in` needs PEM, hence the DER conversion first.
openssl x509 -inform der -in developerID_application.cer -out "$dir/$name.crt"
# sanity check: the subject must read "Developer ID Application: ..." — a
# Developer ID *Installer* certificate carries a critical extension
# (1.2.840.113635.100.6.1.14) quill rejects with "x509: unhandled critical extension"
openssl x509 -in "$dir/$name.crt" -noout -subject
password=$(openssl rand -base64 24)
openssl pkcs12 -export -inkey "$dir/$name.key" -in "$dir/$name.crt" -name "$name" \
  -out "$dir/$name.p12" -passout "pass:$password"
quill p12 describe "$dir/$name.p12"    # optional: shows the leaf + the resolved chain
# record these, and back the .p12 + password up in the password manager: Apple
# cannot re-issue a private key, so a lost key means revoke + reissue.
openssl x509 -in "$dir/$name.crt" -noout -serial -fingerprint -sha256 -enddate
```

## Step 2 — the team API key

App Store Connect → **Users and Access → Integrations → App Store Connect API → Team Keys → Generate**: name
`GitHub Actions Notarization`, access **Developer**. Download `AuthKey_<KEYID>.p8` (offered once) and copy the **Issuer
ID** (top of the page) and the **Key ID**.

## Step 3 — org secrets for the notarizing repos

The base64 values are single-line so GitHub masks them in logs. Clean up the local key material once the secrets are set
and the backup is in the password manager.

```sh
org=bitwise-media-group; repos=dotty,patchy,evolve
gh secret set MACOS_SIGN_P12         --org $org --visibility selected --repos $repos \
  --body "$(base64 -i "$dir/$name.p12" | tr -d '\n')"
gh secret set MACOS_SIGN_PASSWORD    --org $org --visibility selected --repos $repos --body "$password"
gh secret set MACOS_NOTARY_ISSUER_ID --org $org --visibility selected --repos $repos --body "<issuer id>"
gh secret set MACOS_NOTARY_KEY_ID    --org $org --visibility selected --repos $repos --body "<key id>"
gh secret set MACOS_NOTARY_KEY       --org $org --visibility selected --repos $repos \
  --body "$(base64 -i ~/Downloads/AuthKey_<KEYID>.p8 | tr -d '\n')"

rm -rf "$dir" ~/Downloads/AuthKey_<KEYID>.p8 ~/Downloads/developerID_application.cer
```

## Consumer side

Put darwin in its own build id and limit `binary_signs.ids` to the non-darwin ids: GoReleaser runs `binary_signs`
(cosign) _before_ notarization, which rewrites the Mach-O in place, so a cosign bundle over the darwin binary would
never verify against what ships — and the OSS `binary_signs` has no per-artifact `if`, so the build id is the only
handle. The darwin binaries are covered by the Apple signature and notarization plus the SLSA attestation over
`checksums.txt`. Then add the block and pass the five secrets from the caller (commented lines in
[`examples/release.yaml`](https://github.com/bitwise-media-group/github-workflows/blob/main/examples/release.yaml)):

```yaml
notarize:
  macos:
    # every real release notarizes (and fails if the secrets are missing); a
    # snapshot only does when MACOS_SIGN_P12 is exported, so `goreleaser
    # release --snapshot` stays offline and a local end-to-end test is one env
    # export away
    - enabled: '{{ or (not .IsSnapshot) (isEnvSet "MACOS_SIGN_P12") }}'
      ids: [<darwin build id>]
      sign:
        certificate: "{{ .Env.MACOS_SIGN_P12 }}"
        password: "{{ .Env.MACOS_SIGN_PASSWORD }}"
      notarize:
        issuer_id: "{{ .Env.MACOS_NOTARY_ISSUER_ID }}"
        key_id: "{{ .Env.MACOS_NOTARY_KEY_ID }}"
        key: "{{ .Env.MACOS_NOTARY_KEY }}"
        wait: true
        timeout: 15m
```

Verify a shipped binary on a Mac with `codesign -dv --verbose=4 <binary>` (Authority =
`Developer ID Application: … (TEAMID)`, flags include `runtime`) and `spctl -a -vv -t install <binary>`
(`source=Notarized Developer ID`).

## Onboarding another repo

Add it to each secret's repository list — org **Settings → Secrets and variables → Actions**, or
`gh api -X PUT orgs/$org/actions/secrets/<NAME>/repositories/$(gh api repos/$org/<repo> --jq .id)` for each of the five
— then make the consumer-side changes. No new Apple material is needed.

## Rotation and revocation

The certificate is valid for five years. Revoking it in the developer portal invalidates future signing for every repo
at once (binaries already notarized keep running), so rotate by issuing a new certificate with step 1 and re-running the
`MACOS_SIGN_P12` / `MACOS_SIGN_PASSWORD` `gh secret set`. The API key is revoked in App Store Connect → Team Keys;
generate a new one and re-run the three `MACOS_NOTARY_*` `gh secret set`s.

## The secrets

| Secret                   | Caller passes                           | Holds                                                 |
| ------------------------ | --------------------------------------- | ----------------------------------------------------- |
| `macos-sign-p12`         | `${{ secrets.MACOS_SIGN_P12 }}`         | base64 of the `.p12` (Developer ID certificate + key) |
| `macos-sign-password`    | `${{ secrets.MACOS_SIGN_PASSWORD }}`    | the `.p12` export password                            |
| `macos-notary-issuer-id` | `${{ secrets.MACOS_NOTARY_ISSUER_ID }}` | App Store Connect issuer ID                           |
| `macos-notary-key-id`    | `${{ secrets.MACOS_NOTARY_KEY_ID }}`    | App Store Connect API key ID                          |
| `macos-notary-key`       | `${{ secrets.MACOS_NOTARY_KEY }}`       | base64 of the API key's `.p8`                         |

`release.yaml` exports them to `mise run release` as `MACOS_SIGN_P12`, `MACOS_SIGN_PASSWORD`, `MACOS_NOTARY_ISSUER_ID`,
`MACOS_NOTARY_KEY_ID` and `MACOS_NOTARY_KEY`. When they aren't passed they are empty, which GoReleaser's `isEnvSet`
treats as unset, and a config without a `notarize` block never reads them.
