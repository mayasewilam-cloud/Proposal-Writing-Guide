"""
Full-Text Retrieval Service for BioWriter Studio Paper Decoder.
Pipeline:
1. Direct Pasted Text / Uploaded PDF
2. DOI/PMID -> PMCID via Europe PMC / NCBI ID Converter
3. PMCID -> JATS Full-Text XML (Europe PMC REST API or NCBI E-utilities)
4. Fallback: Unpaywall Open-Access PDF -> PyMuPDF extraction
5. Fallback: Abstract-Only mode with prompt to upload PDF or paste text.
"""

import os
import re
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple, List

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

USER_AGENT = "BioWriterStudio/2.0 (mailto:analyst@biowriter.edu)"


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()


def parse_jats_xml(xml_bytes: bytes) -> Tuple[str, Dict[str, str]]:
    """Parses JATS XML into labeled paper sections and structured tables."""
    root = ET.fromstring(xml_bytes)
    sections: Dict[str, str] = {}

    # Title
    title_elem = root.find('.//article-title')
    title = ''.join(title_elem.itertext()).strip() if title_elem is not None else ""

    # Abstract
    abs_elem = root.find('.//abstract')
    if abs_elem is not None:
        abs_text = ' '.join(''.join(p.itertext()).strip() for p in abs_elem.findall('.//p'))
        if abs_text:
            sections['abstract'] = abs_text

    # Body Sections
    for sec in root.findall('.//body//sec'):
        t_elem = sec.find('title')
        t_text = ''.join(t_elem.itertext()).strip().lower() if t_elem is not None else ""
        sec_type = sec.attrib.get('sec-type', '').lower()

        canonical = None
        if any(k in t_text or k in sec_type for k in ['intro', 'background']):
            canonical = 'introduction'
        elif any(k in t_text or k in sec_type for k in ['method', 'material', 'procedure', 'experimental']):
            canonical = 'methods'
        elif any(k in t_text or k in sec_type for k in ['result', 'synthesis']):
            canonical = 'results'
        elif any(k in t_text or k in sec_type for k in ['discuss', 'limitation']):
            canonical = 'discussion'
        elif any(k in t_text or k in sec_type for k in ['conclus']):
            canonical = 'conclusions'

        if canonical:
            p_texts = [''.join(p.itertext()).strip() for p in sec.findall('.//p')]
            content = '\n\n'.join(p for p in p_texts if p).strip()
            if content:
                if canonical in sections:
                    sections[canonical] += '\n\n' + content
                else:
                    sections[canonical] = content

    # Structured Tables
    table_texts: List[str] = []
    for tw in root.findall('.//table-wrap'):
        label_elem = tw.find('label')
        label = ''.join(label_elem.itertext()).strip() if label_elem is not None else "Table"
        cap_elem = tw.find('.//caption')
        caption = ''.join(cap_elem.itertext()).strip() if cap_elem is not None else ""

        rows = []
        for tr in tw.findall('.//tr'):
            cells = [' '.join(''.join(c.itertext()).split()) for c in tr.findall('.//th') + tr.findall('.//td')]
            if cells:
                rows.append(' | '.join(cells))
        if rows:
            table_str = f"[{label}: {caption}]\n" + '\n'.join(rows)
            table_texts.append(table_str)

    if table_texts:
        sections['tables'] = '\n\n'.join(table_texts)

    # Figure Legends
    fig_texts: List[str] = []
    for fig in root.findall('.//fig'):
        label_elem = fig.find('label')
        label = ''.join(label_elem.itertext()).strip() if label_elem is not None else "Figure"
        cap_elem = fig.find('.//caption')
        caption = ''.join(cap_elem.itertext()).strip() if cap_elem is not None else ""
        if caption:
            fig_texts.append(f"[{label}: {caption}]")

    if fig_texts:
        sections['figure legends'] = '\n\n'.join(fig_texts)

    return title, sections


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extracts text from PDF bytes using PyMuPDF (fitz) or pypdf."""
    text_content = []
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text_content.append(page.get_text())
            doc.close()
            return "\n\n".join(text_content).strip()
        except Exception:
            pass

    if HAS_PYPDF:
        try:
            import io
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_content.append(t)
            return "\n\n".join(text_content).strip()
        except Exception:
            pass

    return ""


def parse_raw_text_into_sections(raw_text: str) -> Dict[str, str]:
    """Splits unparsed plain text or PDF text into labeled sections, supporting research papers and reviews."""
    if not raw_text or not raw_text.strip():
        return {}

    clean_raw = raw_text.strip()

    pattern = (
        r'(?i)(?:^|\n)\s*'
        r'(?:(?:section\s+)?[0-9IVXLCDM]+[\.:\s]+)?'
        r'(abstract|introduction|background|materials?\s+and\s+methods?|methods?|methodology|'
        r'experimental\s+(?:procedures?|section|protocols?)|results?\s+and\s+discussion|results?|'
        r'discussion|conclusions?|search\s+strategy|literature\s+search|study\s+selection|'
        r'inclusion\s+criteria|included\s+studies|evidence\s+synthesis|systematic\s+review|'
        r'clinical\s+trials?|mechanisms?(?:\s+of\s+action)?|pathophysiological?\s+mechanisms?|'
        r'limitations?|tables?|figure\s+legends?|references)\b[:\s]*\n?'
    )
    matches = list(re.finditer(pattern, clean_raw))

    if not matches:
        words = clean_raw.split()
        if len(words) >= 350:
            total = len(words)
            w_intro = ' '.join(words[:int(total * 0.20)])
            w_methods = ' '.join(words[int(total * 0.20):int(total * 0.45)])
            w_results = ' '.join(words[int(total * 0.45):int(total * 0.75)])
            w_discussion = ' '.join(words[int(total * 0.75):])
            return {
                'introduction': w_intro,
                'methods': w_methods,
                'results': w_results,
                'discussion': w_discussion
            }
        return {'abstract': clean_raw}

    sections: Dict[str, str] = {}
    for i, m in enumerate(matches):
        raw_name = m.group(1).lower().strip()
        if any(k in raw_name for k in ['method', 'material', 'procedure', 'search strategy', 'literature search', 'study selection', 'inclusion criteria']):
            sec_name = 'methods'
        elif any(k in raw_name for k in ['result', 'included studies', 'evidence synthesis', 'clinical trials', 'synthesis', 'mechanism', 'pathophysiolog']):
            sec_name = 'results'
        elif any(k in raw_name for k in ['intro', 'background']):
            sec_name = 'introduction'
        elif any(k in raw_name for k in ['discuss', 'limitation']):
            sec_name = 'discussion'
        elif any(k in raw_name for k in ['conclus']):
            sec_name = 'conclusions'
        elif any(k in raw_name for k in ['table']):
            sec_name = 'tables'
        elif any(k in raw_name for k in ['figure']):
            sec_name = 'figure legends'
        elif any(k in raw_name for k in ['ref']):
            sec_name = 'references'
        else:
            sec_name = 'abstract'

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_raw)
        chunk = clean_raw[start:end].strip()
        if chunk:
            if sec_name in sections:
                sections[sec_name] += '\n\n' + chunk
            else:
                sections[sec_name] = chunk

    return sections


def fetch_europepmc_metadata(clean_id: str) -> Optional[Dict[str, Any]]:
    """Queries Europe PMC for publication metadata, PMCID, and open access status."""
    is_doi = clean_id.startswith("10.") or "10." in clean_id
    query = f'DOI:"{clean_id}"' if is_doi else f'EXT_ID:"{clean_id}"'
    epmc_url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={urllib.parse.quote(query)}&format=json&resultType=core'
    try:
        req = urllib.request.Request(epmc_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        results = data.get('resultList', {}).get('result', [])
        if results:
            return results[0]
    except Exception:
        pass
    return None


def fetch_pmc_xml(pmcid: str) -> Optional[bytes]:
    """Fetches JATS XML for a given PMCID, trying Europe PMC then NCBI E-utilities."""
    # 1. Try Europe PMC REST API
    epmc_xml_url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
    try:
        req = urllib.request.Request(epmc_xml_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) > 1000 and b'<article' in data:
                return data
    except Exception:
        pass

    # 2. Try NCBI E-utilities fallback
    pmcid_num = pmcid.replace('PMC', '').strip()
    ncbi_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid_num}&retmode=xml'
    try:
        req = urllib.request.Request(ncbi_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) > 1000 and b'<article' in data:
                return data
    except Exception:
        pass

    return None


def fetch_unpaywall_pdf(doi: str) -> Optional[bytes]:
    """Queries Unpaywall for legal Open-Access PDF and downloads it."""
    clean_doi = doi.replace("https://doi.org/", "").strip()
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(clean_doi)}?email=analyst@biowriter.edu"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        pdf_url = data.get("best_oa_location", {}).get("url_for_pdf")
        if pdf_url:
            pdf_req = urllib.request.Request(pdf_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(pdf_req, timeout=15) as pdf_resp:
                return pdf_resp.read()
    except Exception:
        pass
    return None


def fetch_openalex_metadata(doi: str) -> Optional[Dict[str, Any]]:
    """Reconstructs abstract and metadata from OpenAlex inverted index."""
    clean_doi = doi.strip().replace("https://doi.org/", "").replace("doi.org/", "")
    url = f"https://api.openalex.org/works/https://doi.org/{clean_doi}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'mailto:analyst@biowriter.org'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        title = data.get("title", "")
        inv_idx = data.get("abstract_inverted_index") or {}
        word_pos = []
        for w, positions in inv_idx.items():
            for p in positions:
                word_pos.append((p, w))
        word_pos.sort()
        abstract = " ".join(w for p, w in word_pos)
        authors = ", ".join([a.get("author", {}).get("display_name", "") for a in data.get("authorships", [])][:5])
        year = data.get("publication_year")
        journal = (data.get("primary_location") or {}).get("source", {}).get("display_name", "")
        return {
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "year": year,
            "journal": journal
        }
    except Exception:
        return None


def fetch_pubmed_metadata(identifier: str) -> Optional[Dict[str, Any]]:
    """Fetches PubMed abstract and metadata via NCBI E-utilities."""
    clean = identifier.strip().replace("PMID:", "").replace("pmid:", "")
    if clean.startswith("10."):
        esearch = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={clean}&retmode=json"
        try:
            with urllib.request.urlopen(esearch, timeout=6) as r:
                ids = json.loads(r.read())['esearchresult'].get('idlist', [])
                if ids:
                    clean = ids[0]
                else:
                    return None
        except Exception:
            return None
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={clean}&retmode=xml"
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            xml = r.read().decode("utf-8", errors="ignore")
        title_m = re.search(r'<ArticleTitle>(.*?)</ArticleTitle>', xml, re.S)
        ab_m = re.findall(r'<AbstractText[^>]*>(.*?)</AbstractText>', xml, re.S)
        auth_m = re.findall(r'<LastName>(.*?)</LastName>\s*<ForeName>(.*?)</ForeName>', xml)
        year_m = re.search(r'<PubDate>.*?<Year>(\d{4})</Year>', xml, re.S)
        journal_m = re.search(r'<Title>(.*?)</Title>', xml)
        title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""
        abstract = "\n".join([re.sub(r'<[^>]+>', '', a).strip() for a in ab_m])
        authors = ", ".join([f"{f} {l}" for l, f in auth_m[:5]])
        year = int(year_m.group(1)) if year_m else None
        journal = journal_m.group(1).strip() if journal_m else ""
        return {"title": title, "abstract": abstract, "authors": authors, "year": year, "journal": journal, "pmid": clean}
    except Exception:
        return None


def retrieve_paper_data(
    identifier: str = "",
    pasted_text: str = "",
    pdf_bytes: Optional[bytes] = None,
    title: str = "",
    authors: str = "",
    year: Optional[int] = None,
    journal: str = ""
) -> Dict[str, Any]:
    """
    Main retrieval orchestrator:
    - Resolves full text via PMC XML or Unpaywall PDF
    - Returns structured sections and coverage object
    """
    clean_id = (identifier or "").strip().replace("https://doi.org/", "").replace("doi.org/", "")
    sections: Dict[str, str] = {}
    mode = "abstract_only"
    sections_read: List[str] = []
    missing_material: List[str] = []

    # 1. Uploaded PDF (Priority 1 for full text)
    if pdf_bytes and len(pdf_bytes) > 100:
        extracted = extract_text_from_pdf_bytes(pdf_bytes)
        if extracted and len(extracted.split()) > 100:
            sections = parse_raw_text_into_sections(extracted)
            if len([k for k in sections if k in ["methods", "results", "discussion", "introduction"]]) >= 2:
                mode = "full_text"

    # 2. Pasted Full-Text (Priority 2 for full text)
    if not sections and pasted_text and len(pasted_text.split()) >= 100:
        parsed_pasted = parse_raw_text_into_sections(pasted_text)
        if len([k for k in parsed_pasted if k in ["methods", "results", "discussion", "introduction"]]) >= 2:
            sections = parsed_pasted
            mode = "full_text"

    # 3. DOI / PMID / PMCID lookup (fetches PMC XML or Unpaywall PDF full text)
    if clean_id:
        pmc_meta = fetch_europepmc_metadata(clean_id)
        if pmc_meta:
            title = title or pmc_meta.get("title", "")
            authors = authors or pmc_meta.get("authorString", "")
            journal = journal or pmc_meta.get("journalTitle", "")
            pub_year = pmc_meta.get("pubYear")
            if pub_year and not year:
                try:
                    year = int(pub_year)
                except Exception:
                    pass

            pmcid = pmc_meta.get("pmcid")
            if pmcid:
                xml_data = fetch_pmc_xml(pmcid)
                if xml_data:
                    xml_title, parsed_secs = parse_jats_xml(xml_data)
                    if parsed_secs:
                        sections = parsed_secs
                        if not title and xml_title:
                            title = xml_title
                        if len([k for k in sections if k in ["methods", "results", "discussion", "introduction"]]) >= 2:
                            mode = "full_text"

            # If no PMCID XML, try Unpaywall OA PDF
            if not sections and clean_id.startswith("10."):
                oa_pdf_bytes = fetch_unpaywall_pdf(clean_id)
                if oa_pdf_bytes:
                    extracted = extract_text_from_pdf_bytes(oa_pdf_bytes)
                    if extracted and len(extracted.split()) > 200:
                        sections = parse_raw_text_into_sections(extracted)
                        if len([k for k in sections if k in ["methods", "results", "discussion", "introduction"]]) >= 2:
                            mode = "full_text"

            # If still no full text, use abstract from metadata
            if not sections and pmc_meta.get("abstractText"):
                clean_abs = re.sub(r'<[^>]+>', '', pmc_meta["abstractText"])
                sections = {"abstract": clean_abs.strip()}
                mode = "abstract_only"

        # Fallback 2c: OpenAlex (especially for OA abstracts when Europe PMC has no hit)
        if not sections and clean_id.startswith("10."):
            oa_meta = fetch_openalex_metadata(clean_id)
            if oa_meta and oa_meta.get("abstract"):
                title = title or oa_meta.get("title", "")
                authors = authors or oa_meta.get("authors", "")
                journal = journal or oa_meta.get("journal", "")
                year = year or oa_meta.get("year")
                sections = {"abstract": oa_meta["abstract"]}
                mode = "abstract_only"

        # Fallback 2d: NCBI PubMed (for PMID or DOIs indexed in PubMed)
        if not sections and clean_id:
            pm_meta = fetch_pubmed_metadata(clean_id)
            if pm_meta and pm_meta.get("abstract"):
                title = title or pm_meta.get("title", "")
                authors = authors or pm_meta.get("authors", "")
                journal = journal or pm_meta.get("journal", "")
                year = year or pm_meta.get("year")
                sections = {"abstract": pm_meta["abstract"]}
                mode = "abstract_only"

    # 3. Pasted Text Fallback
    if not sections and pasted_text and len(pasted_text.split()) >= 15:
        parsed_secs = parse_raw_text_into_sections(pasted_text)
        sections = parsed_secs
        has_body = len([k for k in sections if k in ["methods", "results", "discussion", "introduction"]]) >= 2
        mode = "full_text" if has_body else "abstract_only"

    # Build coverage object
    standard_secs = ["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusions", "Tables", "Figure legends"]
    for s in standard_secs:
        if s.lower() in sections and sections[s.lower()].strip():
            sections_read.append(s)
        else:
            missing_material.append(s)

    if mode == "full_text":
        missing_material = [m for m in missing_material if m in ["Tables", "Figure legends", "Conclusions"]]

    coverage = {
        "mode": mode,
        "sections_read": sections_read if sections_read else ["Abstract"],
        "missing": missing_material
    }

    return {
        "title": re.sub(r'<[^>]+>', '', title or "Research Paper").strip(),
        "authors": authors or "Identified Authors",
        "year": year,
        "journal": journal or "Peer-Reviewed Journal",
        "identifier": clean_id,
        "sections": sections,
        "coverage": coverage
    }
