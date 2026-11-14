"""
Web Search & Multi-Engine Information Service for BioWriter Studio.
Provides unified live search across DuckDuckGo Web API, Wikipedia Knowledge Base,
Europe PMC Scholarly Literature, and direct deep-links to Google, Google Scholar, PubMed.
"""

import json
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Any, Optional


def get_search_engine_links(query: str) -> Dict[str, str]:
    """Generates direct, pre-filled launch links across major search engines."""
    clean_q = query.strip()
    q_enc = urllib.parse.quote_plus(clean_q)
    return {
        "google": f"https://www.google.com/search?q={q_enc}",
        "scholar": f"https://scholar.google.com/scholar?q={q_enc}",
        "pubmed": f"https://pubmed.ncbi.nlm.nih.gov/?term={q_enc}",
        "duckduckgo": f"https://duckduckgo.com/?q={q_enc}",
        "europe_pmc": f"https://europepmc.org/search?query={q_enc}",
        "wikipedia": f"https://en.wikipedia.org/wiki/Special:Search?search={q_enc}"
    }


def search_web(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Queries open Web search APIs (DuckDuckGo Instant Answer and Wikipedia)
    to retrieve clean, verified web summaries and source URLs.
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    results = []

    # 1. DuckDuckGo Instant Answer API
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_q)}&format=json"
        req = urllib.request.Request(
            ddg_url,
            headers={"User-Agent": "BioWriterStudio-WebSearch/2.0 (Academic Research Assistant)"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            
            # Primary abstract if present
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading") or clean_q.title(),
                    "snippet": data.get("AbstractText"),
                    "url": data.get("AbstractURL") or f"https://duckduckgo.com/?q={urllib.parse.quote_plus(clean_q)}",
                    "source": data.get("AbstractSource") or "DuckDuckGo Knowledge"
                })

            # Related topics
            for topic in data.get("RelatedTopics", []):
                if len(results) >= max_results:
                    break
                if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                    snippet = topic.get("Text", "")
                    # Extract title from before the first dash if available
                    parts = snippet.split(" - ", 1)
                    title = parts[0] if len(parts) > 1 else snippet[:60]
                    body = parts[1] if len(parts) > 1 else snippet
                    results.append({
                        "title": title.strip(),
                        "snippet": body.strip(),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo Web"
                    })
    except Exception as e:
        # Fallback continues gracefully
        pass

    # 2. Wikipedia Full-Text Search API (action=query&list=search)
    if len(results) < max_results:
        try:
            wiki_search_url = (
                f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch="
                f"{urllib.parse.quote(clean_q)}&format=json&utf8=1&srlimit={max_results}"
            )
            req = urllib.request.Request(
                wiki_search_url,
                headers={"User-Agent": "BioWriterStudio-WebSearch/2.0"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                search_hits = data.get("query", {}).get("search", [])
                for hit in search_hits:
                    if len(results) >= max_results:
                        break
                    title = hit.get("title", "")
                    raw_snippet = hit.get("snippet", "")
                    clean_snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()
                    page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                    if title and not any(r.get("url") == page_url for r in results):
                        results.append({
                            "title": title,
                            "snippet": clean_snippet,
                            "url": page_url,
                            "source": "Wikipedia Knowledge Base"
                        })
        except Exception:
            pass

    # 3. Wikipedia OpenSearch API Fallback
    if len(results) < max_results:
        try:
            wiki_url = (
                f"https://en.wikipedia.org/w/api.php?action=opensearch&search="
                f"{urllib.parse.quote(clean_q)}&limit={max_results}&namespace=0&format=json"
            )
            req = urllib.request.Request(
                wiki_url,
                headers={"User-Agent": "BioWriterStudio-WebSearch/2.0"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                wiki_data = json.loads(resp.read().decode("utf-8", errors="replace"))
                if len(wiki_data) >= 4 and isinstance(wiki_data[1], list):
                    titles = wiki_data[1]
                    snippets = wiki_data[2] if len(wiki_data) > 2 else []
                    urls = wiki_data[3] if len(wiki_data) > 3 else []
                    
                    for i in range(len(titles)):
                        if len(results) >= max_results:
                            break
                        title = titles[i]
                        snippet = snippets[i] if i < len(snippets) else ""
                        url = urls[i] if i < len(urls) else ""
                        if url and snippet and not any(r.get("url") == url for r in results):
                            results.append({
                                "title": title,
                                "snippet": snippet,
                                "url": url,
                                "source": "Wikipedia Encyclopedia"
                            })
        except Exception:
            pass

    return results[:max_results]


def search_scholar(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Queries Europe PMC REST API to retrieve peer-reviewed research papers,
    clinical trials, and citations.
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    results = []
    try:
        url = (
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
            f"query={urllib.parse.quote(clean_q)}&format=json&pageSize={max_results}&resultType=core"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BioWriterStudio-ScholarSearch/2.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            hit_list = data.get("resultList", {}).get("result", [])
            for item in hit_list:
                title = (item.get("title") or "").rstrip(".")
                abstract = item.get("abstractText") or ""
                abstract_clean = re.sub(r"<[^>]+>", "", abstract).strip()
                if not abstract_clean:
                    abstract_clean = f"Published paper in {item.get('journalTitle', 'Peer-Reviewed Journal')} ({item.get('pubYear', 'Recent')})."
                
                doi = item.get("doi", "")
                url_link = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/MED/{item.get('pmid', '')}"
                if not doi and not item.get("pmid"):
                    url_link = f"https://europepmc.org/search?query={urllib.parse.quote_plus(title)}"

                results.append({
                    "title": title,
                    "snippet": abstract_clean[:220] + ("..." if len(abstract_clean) > 220 else ""),
                    "authors": item.get("authorString") or "Research Consortium",
                    "year": str(item.get("pubYear") or "2024"),
                    "journal": item.get("journalTitle") or "Scientific Reports",
                    "doi": doi,
                    "url": url_link,
                    "source": "Europe PMC Literature"
                })
    except Exception:
        pass

    return results[:max_results]


def execute_multi_search(query: str) -> Dict[str, Any]:
    """
    Executes a comprehensive multi-source search spanning Web, Scholar,
    and direct search engine launchers.
    """
    clean_q = query.strip()
    # Strip search prefixes if present
    clean_subject = re.sub(r'^(search|find|lookup|look up|google|websearch|web search|scholar):\s*', '', clean_q, flags=re.IGNORECASE)
    clean_subject = re.sub(r'^(search (the )?(web|internet|google|online|duckduckgo|engines?)|look up (online|on the web|on google)|find (me )?papers|find online)\s*(for|about)?\s*', '', clean_subject, flags=re.IGNORECASE).strip()
    if not clean_subject:
        clean_subject = clean_q

    web_results = search_web(clean_subject, max_results=3)
    scholar_results = search_scholar(clean_subject, max_results=3)
    engine_links = get_search_engine_links(clean_subject)

    # Synthesize multi-source summary
    summary_parts = []
    if web_results:
        summary_parts.append(f"Found {len(web_results)} live web sources on **{clean_subject}**.")
    if scholar_results:
        summary_parts.append(f"Located {len(scholar_results)} peer-reviewed scholarly studies on Europe PMC.")

    return {
        "query": clean_subject,
        "summary": " ".join(summary_parts) if summary_parts else f"Search query compiled for '{clean_subject}'.",
        "web_results": web_results,
        "scholar_results": scholar_results,
        "engine_links": engine_links
    }
