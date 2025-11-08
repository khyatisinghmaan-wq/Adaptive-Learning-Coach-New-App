import os, re

def load_kb(kb_dir: str):
    docs = []
    for fn in os.listdir(kb_dir):
        if fn.endswith('.md'):
            with open(os.path.join(kb_dir, fn), 'r', encoding='utf-8') as f:
                docs.append(f.read())
    return docs

def simple_retrieve(query: str, docs):
    # Extremely simple retrieval: return the first paragraph that contains any keyword
    q_terms = [w.lower() for w in re.findall(r"\w+", query)]
    best_para = None
    for doc in docs:
        for para in doc.split('\n\n'):
            p_low = para.lower()
            if any(t in p_low for t in q_terms):
                best_para = para.strip()
                if len(best_para) > 0:
                    return best_para
    # fallback: first paragraph of first doc
    if docs:
        for para in docs[0].split('\n\n'):
            if para.strip():
                return para.strip()
    return "No relevant content found in KB."
