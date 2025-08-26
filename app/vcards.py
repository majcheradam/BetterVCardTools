import re
import unicodedata
from typing import Optional
from uuid import uuid4

import vobject

CRLF = "\r\n"


def decode_vcard_bytes(data: bytes) -> str:
    """Best-effort decoding of uploaded vCard bytes to UTF-8 string.

    Strategy:
    - Use charset_normalizer to detect encoding reliably.
    - Normalize to NFC Unicode form.
    - Optionally run ftfy.fix_text to repair common mojibake if available.
    Fallbacks are designed to avoid raising while preserving the most info.
    """
    try:
        from charset_normalizer import from_bytes  # type: ignore
    except Exception:
        from_bytes = None  # type: ignore

    text: str
    if from_bytes:
        try:
            best = from_bytes(data).best()
            if best is not None:
                text = str(best)
            else:
                text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("utf-8", errors="replace")
    else:
        # Fallback to utf-8 with replacement
        text = data.decode("utf-8", errors="replace")

    # Normalize to NFC for consistent output
    text = unicodedata.normalize("NFC", text)

    # Optionally fix mojibake like 'W≈Ça≈õciciel' → 'Właściciel'
    try:
        from ftfy import fix_text  # type: ignore

        fixed = fix_text(text)
        # Only replace if it seems beneficial (heuristic):
        if fixed != text:
            text = fixed
    except Exception:
        # ftfy not available or failed; keep text as-is
        pass

    return text


def _escape(s: str) -> str:
    if not s:
        return ""
    return (str(s)
            .replace("\\", "\\\\")
            .replace(";", r"\\;")
            .replace(",", r"\\,")
            .replace("\n", r"\\n")
            .replace("\r", ""))

def _caret_encode_param_value(s: str) -> str:
    """RFC 6868 caret encoding for parameter values: ^n -> \n, ^' -> ", ^^ -> ^.
    Also escape comma and semicolon in param values using caret rules where appropriate.
    """
    if s is None:
        return ""
    # Basic replacements per RFC 6868
    out = str(s).replace("^", "^^").replace("\n", "^n").replace('"', "^'")
    # Comma/semicolon can remain; most implementations accept quoted-string
    return out

def _format_params(params: list[tuple[str, str]]) -> str:
    if not params:
        return ""
    parts = []
    for k, v in params:
        if v is None or v == "":
            continue
        # Quote only when necessary; simple tokens can remain unquoted
        v_str = str(v)
        if re.fullmatch(r"[A-Za-z0-9._+-]+(,[A-Za-z0-9._+-]+)*", v_str):
            parts.append(f";{k}={v_str}")
        else:
            parts.append(f";{k}=" + '"' + _caret_encode_param_value(v_str) + '"')
    return "".join(parts)

def _fold_line(line: str, limit: int = 75) -> list[str]:
    """Fold a single logical line into 75-octet segments (bytes), using CRLF + single space continuation."""
    b = line.encode('utf-8')
    if len(b) <= limit:
        return [line]
    out: list[str] = []
    i = 0
    while i < len(b):
        chunk = b[i:i+limit]
        # avoid splitting in the middle of a UTF-8 code point
        while chunk and (chunk[-1] & 0b11000000) == 0b10000000:
            chunk = chunk[:-1]
        out.append(chunk.decode('utf-8', errors='ignore'))
        i += len(chunk)
        if i < len(b):
            # continuation lines start with a single space
            b = b[:i] + b[i:]
    # Prepend continuation space to all but the first logical segment
    for idx in range(1, len(out)):
        out[idx] = ' ' + out[idx]
    return out

_PREFIXES = {"mr", "mrs", "ms", "dr", "prof"}
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md"}

def _split_name(fn: str) -> dict[str, str]:
    """Best-effort split of a display name into structured N fields.
    Returns dict with keys: family, given, additional, prefix, suffix.
    """
    tokens = [t for t in re.split(r"\s+", (fn or "").strip()) if t]
    if not tokens:
        return {"family": "", "given": "", "additional": "", "prefix": "", "suffix": ""}
    # Normalize helper strips trailing dots for prefix/suffix matching
    def norm(t: str) -> str:
        return re.sub(r"\.+$", "", t).lower()
    prefix = tokens[0] if norm(tokens[0]) in _PREFIXES else ""
    suffix = tokens[-1] if norm(tokens[-1]) in _SUFFIXES else ""
    core = (
        tokens[1:-1]
        if (prefix and suffix)
        else (tokens[1:] if prefix else (tokens[:-1] if suffix else tokens))
    )
    if not core:
        return {
            "family": "",
            "given": tokens[0] if tokens else "",
            "additional": "",
            "prefix": prefix,
            "suffix": suffix,
        }
    if len(core) == 1:
        given, family = core[0], ""
        additional = ""
    else:
        given, family = core[0], " ".join(core[1:])
        additional = ""
    return {
        "family": family,
        "given": given,
        "additional": additional,
        "prefix": prefix,
        "suffix": suffix,
    }

def _split_types(val) -> list[str]:
    if not val:
        return []
    if isinstance(val, str):
        parts = [p.strip() for p in val.split(",") if p.strip()]
    elif isinstance(val, list):
        parts = []
        for x in val:
            parts.extend([p.strip() for p in str(x).split(",") if p.strip()])
    else:
        parts = [str(val).strip()]
    return [p.lower() for p in parts]

def _normalize_types(kind: str, types: list[str]) -> list[str]:
    # Dedup, lowercase done in _split_types; filter unwanted values
    tset = set(types or [])
    if kind == "email":
        # RFC 6350 removed INTERNET; it's implied, so drop it
        tset.discard("internet")
    if kind == "tel" and len(tset) > 1 and "voice" in tset:
        # Drop 'voice' if there are other types present
        tset.remove("voice")
    return sorted(tset)

_KNOWN_TEL_TYPES = {
    "home", "work", "cell", "voice", "fax", "pager", "text", "textphone", "main", "iphone"
}
_KNOWN_EMAIL_TYPES = {"home", "work", "internet", "pref", "x-mobileme"}
_KNOWN_ADR_TYPES = {"home", "work", "pref", "intl", "postal", "parcel", "dom"}

def _extract_types_from_params(kind: str, params: dict, singletonparams) -> list[str]:
    types: list[str] = []
    p = params or {}
    # TYPE values (comma-joined or list)
    if 'TYPE' in p:
        types.extend(_split_types(p.get('TYPE')))
    # vCard 2.1 style: bare flags like HOME/WORK appear as parameter keys
    for key, _val in p.items():
        k = str(key).lower()
        if k == 'type':
            continue
        if kind == 'tel' and k in _KNOWN_TEL_TYPES:
            types.append(k)
        if kind == 'email' and k in _KNOWN_EMAIL_TYPES:
            types.append(k)
        if kind == 'adr' and k in _KNOWN_ADR_TYPES:
            types.append(k)
    # singletonparams fallback (some vobject versions)
    if singletonparams:
        types.extend(_split_types(singletonparams))
    return _normalize_types(kind, types)

essential_fields = ("fn", "email_list", "tel_list", "org")

def parse_vcards(text: str) -> list[dict]:
    """Parse vCard text into a normalized contact dict list.

    Output shape per contact:
      {
        name: Optional[str]  # FN if present
        n: {
          family: str, given: str, additional: str, prefix: str, suffix: str
        } | None
        emails: List[{ value: str, types: List[str] }]
        phones: List[{ value: str, types: List[str] }]
        org: List[str] | None  # structured components
      }
    """
    contacts: list[dict] = []
    for v in vobject.readComponents(text):
        # FN and structured N
        fn_obj = getattr(v, 'fn', None)
        fn_val: Optional[str] = fn_obj.value if fn_obj is not None else None
        n_struct = None
        n_obj = getattr(v, 'n', None)
        if n_obj is not None:
            nval = n_obj.value  # vobject.vcard.Name
            n_struct = {
                "family": nval.family or "",
                "given": nval.given or "",
                "additional": nval.additional or "",
                "prefix": nval.prefix or "",
                "suffix": nval.suffix or "",
            }
        else:
            # Derive a minimal N from FN as best-effort using split helper
            n_struct = _split_name(str(fn_val)) if fn_val else None

        # Emails with types
        emails = []
        for e in getattr(v, 'email_list', []):
            params = getattr(e, 'params', {}) or {}
            singleton = getattr(e, 'singletonparams', []) or []
            types = _extract_types_from_params('email', params, singleton)
            emails.append({"value": e.value, "types": types})

        # Phones with types
        phones = []
        for p in getattr(v, 'tel_list', []):
            params = getattr(p, 'params', {}) or {}
            singleton = getattr(p, 'singletonparams', []) or []
            types = _extract_types_from_params('tel', params, singleton)
            phones.append({"value": p.value, "types": types})

        # ORG structured components
        org_list = None
        org_obj = getattr(v, 'org', None)
        if org_obj is not None:
            try:
                # Typically a list of components
                vals = org_obj.value or []
                org_list = [str(x) for x in vals]
            except Exception:
                # fallback: treat as a single string
                try:
                    org_list = [str(org_obj.value)]
                except Exception:
                    org_list = None

        # ADR list (structured). Collect components and types (+ group id for LABEL mapping)
        adrs = []
        for a in getattr(v, 'adr_list', []) or []:
            try:
                aval = a.value
                comps = {
                    "box": getattr(aval, 'box', '') or '',
                    "extended": getattr(aval, 'extended', '') or '',
                    "street": getattr(aval, 'street', '') or '',
                    "city": getattr(aval, 'city', '') or '',
                    "region": getattr(aval, 'region', '') or '',
                    "code": getattr(aval, 'code', '') or '',
                    "country": getattr(aval, 'country', '') or '',
                }
                params = getattr(a, 'params', {}) or {}
                singleton = getattr(a, 'singletonparams', []) or []
                types = _extract_types_from_params('adr', params, singleton)
                group = getattr(a, 'group', None)
                adrs.append({"components": comps, "types": types, "group": group})
            except Exception:
                continue

        # LABEL properties (vCard 3.0). Try group-based matching, then index order
        label_objs = getattr(v, 'label_list', []) or []
        label_entries = []
        for lb in label_objs:
            try:
                label_entries.append({
                    "value": str(lb.value),
                    "group": getattr(lb, 'group', None),
                })
            except Exception:
                continue
        if label_entries and adrs:
            # First try to match by group
            groups_to_label = {e["group"]: e["value"] for e in label_entries if e.get("group")}
            for adr in adrs:
                g = adr.get("group")
                if g and g in groups_to_label and not adr.get("label"):
                    adr["label"] = groups_to_label[g]
            # Then match remaining by index
            remaining_labels = [e["value"] for e in label_entries if not e.get("group")]
            idx = 0
            for adr in adrs:
                if not adr.get("label") and idx < len(remaining_labels):
                    adr["label"] = remaining_labels[idx]
                    idx += 1

        # URL list
        urls = []
        for u in getattr(v, 'url_list', []) or []:
            try:
                urls.append(str(u.value))
            except Exception:
                continue

        # IMPP list (instant messaging)
        impps = []
        for im in getattr(v, 'impp_list', []) or []:
            try:
                impps.append(str(im.value))
            except Exception:
                continue

        # GEO
        geo_val = None
        geo_obj = getattr(v, 'geo', None)
        if geo_obj is not None:
            try:
                g = str(geo_obj.value)
                # If looks like "lat;long" convert to geo:lat,long
                if ";" in g and not g.startswith("geo:"):
                    parts = [p.strip() for p in g.split(";")]
                    if len(parts) >= 2:
                        geo_val = f"geo:{parts[0]},{parts[1]}"
                else:
                    geo_val = g
            except Exception:
                geo_val = None

        # TZ
        tz_val = None
        tz_obj = getattr(v, 'tz', None)
        if tz_obj is not None:
            try:
                tz_val = str(tz_obj.value)
            except Exception:
                tz_val = None

        # Helper to collect media props (URI or inline with params)
        def _collect_media_list(prop_list):
            items = []
            for pr in prop_list or []:
                try:
                    val = pr.value
                    params = getattr(pr, 'params', {}) or {}
                    typ = None
                    # TYPE may contain MIME hints like JPEG, PNG, MP3
                    tparam = params.get('TYPE')
                    if tparam:
                        tp = _split_types(tparam)
                        typ = tp[0] if tp else None
                    enc = (params.get('ENCODING') or params.get('encoding') or [None])
                    encoding = enc[0] if isinstance(enc, list) else enc
                    # Normalize value
                    sval = str(val) if val is not None else ''
                    if sval.startswith(('http://', 'https://', 'data:')):
                        items.append({"kind": "uri", "value": sval, "type": typ})
                    else:
                        # Inline data or unknown
                        items.append({"kind": "inline", "value": sval, "type": typ, "encoding": (encoding or '')})
                except Exception:
                    continue
            return items

        photos = _collect_media_list(getattr(v, 'photo_list', []) or [])

        # LOGO/SOUND/KEY (URIs only)
        logos = _collect_media_list(getattr(v, 'logo_list', []) or [])
        sounds = _collect_media_list(getattr(v, 'sound_list', []) or [])
        keys = _collect_media_list(getattr(v, 'key_list', []) or [])

        # BDAY (date or datetime or text). Normalize to ISO if possible.
        bday_val = None
        bday_obj = getattr(v, 'bday', None)
        if bday_obj is not None:
            try:
                val = bday_obj.value
                # vobject can yield date/datetime; convert to date string when possible
                if hasattr(val, 'isoformat'):
                    # If datetime, take date part
                    try:
                        bday_val = val.date().isoformat()
                    except Exception:
                        bday_val = val.isoformat()
                else:
                    bday_val = str(val)
            except Exception:
                bday_val = None

        # NOTE can appear multiple times; collect as list of strings
        notes_list: list[str] | None = None
        note_props = getattr(v, 'note_list', None)
        if note_props is not None:
            try:
                notes_list = [str(n.value) for n in (note_props or [])]
            except Exception:
                notes_list = None

        # UID if present (preserve for dedupe/sync friendliness)
        uid_val = None
        uid_obj = getattr(v, 'uid', None)
        if uid_obj is not None:
            try:
                uid_val = str(uid_obj.value) if uid_obj.value is not None else None
            except Exception:
                uid_val = None

        c = {
            "name": fn_val,
            "n": n_struct,
            "emails": emails,
            "phones": phones,
            "org": org_list,
            "bday": bday_val,
            "notes": notes_list,
            "uid": uid_val,
            "adrs": adrs,
            "urls": urls,
            "photos": photos,
            "logos": logos,
            "sounds": sounds,
            "keys": keys,
            "impps": impps,
            "geo": geo_val,
            "tz": tz_val,
        }
        contacts.append(c)
    return contacts


def _guess_mime_from_type(t: Optional[str], fallback: str = 'application/octet-stream') -> str:
    if not t:
        return fallback
    t = t.lower()
    if t in ('jpeg', 'jpg'): return 'image/jpeg'
    if t == 'png': return 'image/png'
    if t == 'gif': return 'image/gif'
    if t == 'bmp': return 'image/bmp'
    if t == 'svg': return 'image/svg+xml'
    if t in ('mp3',): return 'audio/mpeg'
    if t in ('wav',): return 'audio/wav'
    if t in ('ogg',): return 'audio/ogg'
    if t in ('pgp', 'pgp-key'): return 'application/pgp-keys'
    if t in ('x509', 'x-509'): return 'application/x-x509-ca-cert'
    return fallback

def _to_tel_uri_normalized(tel_raw: str, e164: bool = False, default_region: Optional[str] = None) -> str:
    tel = re.sub(r"[\s()\-.]", "", str(tel_raw))
    if tel.lower().startswith('tel:'):
        tel = tel[4:]
    if e164:
        try:
            import phonenumberslite as phonenumbers
        except Exception:
            phonenumbers = None
        if phonenumbers:
            try:
                num = phonenumbers.parse(tel, default_region or None)
                if phonenumbers.is_valid_number(num):
                    from phonenumberslite import PhoneNumberFormat
                    e = phonenumbers.format_number(num, PhoneNumberFormat.E164)
                    return f"tel:{e}"
            except Exception:
                pass
    # fallback
    if not tel.startswith('+') and tel.startswith('00'):
        tel = '+' + tel[2:]
    return f"tel:{tel}"

def contact_to_vcard40(c: dict, *, options: Optional[dict] = None) -> str:
    opts = options or {}
    props: list[str] = []
    props.append("BEGIN:VCARD")
    props.append("VERSION:4.0")
    # FN
    name = c.get("name") or "Unnamed"
    # N (structured): family;given;additional;prefix;suffix
    n_struct = c.get("n") or {
        "family": "",
        "given": name,
        "additional": "",
        "prefix": "",
        "suffix": "",
    }
    n_fields = [
        _escape(n_struct.get("family", "")),
        _escape(n_struct.get("given", "")),
        _escape(n_struct.get("additional", "")),
        _escape(n_struct.get("prefix", "")),
        _escape(n_struct.get("suffix", "")),
    ]
    props.append("N:" + ";".join(n_fields))
    props.append(f"FN:{_escape(name)}")

    # EMAIL
    for e in c.get("emails", []):
        types = _normalize_types("email", e.get("types", []))
        # PREF mapping: if 'pref' is present, set PREF=1 and drop from TYPE
        pref = None
        if 'pref' in types:
            pref = '1'
            types = [t for t in types if t != 'pref']
        param_list = []
        if types:
            param_list.append(("TYPE", ",".join(types)))
        if pref:
            param_list.append(("PREF", pref))
        params = _format_params(param_list)
        props.append(f"EMAIL{params}:{_escape(e.get('value',''))}")

    # TEL (VALUE=uri tel:...)
    for p in c.get("phones", []):
        tel_raw = str(p.get("value", ""))
        tel = _to_tel_uri_normalized(tel_raw, bool(opts.get('e164')), opts.get('default_region'))
        types = _normalize_types("tel", p.get("types", []))
        pref = None
        if 'pref' in types:
            pref = '1'
            types = [t for t in types if t != 'pref']
        param_list = []
        if types:
            param_list.append(("TYPE", ",".join(types)))
        if pref:
            param_list.append(("PREF", pref))
        param_list.append(("VALUE", "uri"))
        params = _format_params(param_list)
        props.append(f"TEL{params}:{_escape(tel)}")

    # ORG structured
    if c.get("org"):
        comps = [
            _escape(str(comp)) for comp in (c.get("org") or [])
        ]
        props.append("ORG:" + ";".join(comps))

    # ADR (structured: box;extended;street;city;region;code;country)
    for a in c.get("adrs", []) or []:
        comps = a.get("components", {})
        parts = [
            _escape(comps.get("box", "")),
            _escape(comps.get("extended", "")),
            _escape(comps.get("street", "")),
            _escape(comps.get("city", "")),
            _escape(comps.get("region", "")),
            _escape(comps.get("code", "")),
            _escape(comps.get("country", "")),
        ]
        types = _normalize_types("adr", a.get("types", []))
        pref = None
        if 'pref' in types:
            pref = '1'
            types = [t for t in types if t != 'pref']
        param_list = []
        if types:
            param_list.append(("TYPE", ",".join(types)))
        if pref:
            param_list.append(("PREF", pref))
        # Optional LABEL support if present in dict
        label = a.get("label")
        if label:
            param_list.append(("LABEL", label))
        params = _format_params(param_list)
        props.append("ADR" + params + ":" + ";".join(parts))

    # BDAY (RFC 6350 date-and-or-time). Assume a simple date string like YYYY-MM-DD.
    if c.get("bday"):
        props.append(f"BDAY:{_escape(str(c.get('bday')))}")

    # NOTE(s) – write each as separate NOTE property
    notes = c.get("notes") or []
    for note in notes:
        props.append(f"NOTE:{_escape(str(note))}")

    # IMPP(s)
    for im in c.get("impps", []) or []:
        props.append(f"IMPP:{_escape(str(im))}")

    # GEO (as URI geo:lat,long)
    if c.get("geo"):
        val = str(c.get("geo"))
        if not val.startswith("geo:") and ";" in val:
            # best-effort conversion
            lat, lon = val.split(";", 1)
            val = f"geo:{lat.strip()},{lon.strip()}"
        props.append(f"GEO:{_escape(val)}")

    # TZ (text or offset)
    if c.get("tz"):
        props.append(f"TZ:{_escape(str(c.get('tz')))}")

    # URL(s)
    for u in c.get("urls", []) or []:
        props.append(f"URL:{_escape(str(u))}")

    # PHOTO(s) as URI
    def _emit_media(name: str, items: list[dict]):
        for it in items or []:
            kind = it.get('kind')
            if kind == 'uri':
                props.append(f"{name};VALUE=uri:{_escape(str(it.get('value','')))}")
            elif kind == 'inline' and opts.get('inline_media_data_uri'):
                data = re.sub(r"\s+", "", str(it.get('value','')))
                mime = _guess_mime_from_type(it.get('type'))
                props.append(f"{name};VALUE=uri:data:{mime};base64,{data}")
            # else: skip inline when option disabled

    _emit_media('PHOTO', c.get('photos', []))

    # LOGO/SOUND/KEY as URI
    _emit_media('LOGO', c.get('logos', []))
    _emit_media('SOUND', c.get('sounds', []))
    _emit_media('KEY', c.get('keys', []))

    # PRODID and UID
    props.append("PRODID:-//BetterVCardTools//v1.0//EN")
    # UID: preserve existing if provided; otherwise generate a UUID URN
    existing_uid = (c.get("uid") or "").strip()
    if existing_uid:
        props.append(f"UID:{_escape(existing_uid)}")
    else:
        props.append(f"UID:urn:uuid:{uuid4()}")
    # REV (UTC timestamp)
    try:
        from datetime import datetime, timezone
        props.append("REV:" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    except Exception:
        pass
    props.append("END:VCARD")
    # Apply folding and CRLF join
    folded: list[str] = []
    for line in props:
        folded.extend(_fold_line(line))
    return CRLF.join(folded) + CRLF


def contacts_to_vcards40(contacts: list[dict], *, options: Optional[dict] = None) -> str:
    return "".join(contact_to_vcard40(c, options=options) for c in contacts)
