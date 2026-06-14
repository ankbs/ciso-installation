import os
import re
import zipfile

def sanitize_text(text):
    if not text:
        return text
    
    # 1. Replace domains
    text = re.sub(r'myoffice\.mail\.onmicrosoft\.com', 'demo-tenant.mail.onmicrosoft.com', text, flags=re.IGNORECASE)
    text = re.sub(r'myoffice\.onmicrosoft\.com', 'demo-tenant.onmicrosoft.com', text, flags=re.IGNORECASE)
    text = re.sub(r'ankbs\.de', 'demo-corp.de', text, flags=re.IGNORECASE)
    
    # 2. Replace tenant name variations
    text = re.sub(r'\bankbs\b', 'demo-corp', text, flags=re.IGNORECASE)
    text = re.sub(r'\bANKBS\b', 'DEMO-CORP', text)
    
    # 3. Replace any sensitive advisory notes
    text = re.sub(r'Hinweis für die Kundenberatung', 'Testdaten-Hinweis (Demonstration)', text, flags=re.IGNORECASE)
    text = re.sub(r'Kundenberatung', 'Testdaten-Beratung', text, flags=re.IGNORECASE)
    
    # 4. SIDs or generic IDs replacements (if any)
    text = re.sub(r'S-1-5-21-\d+-\d+-\d+-\d+', 'S-1-5-21-0000000000-0000000000-0000000000-0000', text)
    
    return text

def sanitize_json_file(path):
    print(f"Sanitizing JSON: {path}")
    # Try different encodings
    for encoding in ('utf-16-le', 'utf-16', 'utf-8', 'latin-1'):
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            current_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    
    sanitized = sanitize_text(content)
    with open(path, 'w', encoding=current_encoding) as f:
        f.write(sanitized)

def sanitize_html_file(path):
    print(f"Sanitizing HTML: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    sanitized = sanitize_text(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(sanitized)

def sanitize_zip_based_file(path):
    print(f"Sanitizing ZIP-based file (DOCX/XLSX): {path}")
    temp_path = path + ".tmp"
    try:
        with zipfile.ZipFile(path, 'r') as zin:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    if item.filename.endswith(('.xml', '.rels', '.txt')):
                        try:
                            text = data.decode('utf-8')
                            new_text = sanitize_text(text)
                            data = new_text.encode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                text = data.decode('latin-1')
                                new_text = sanitize_text(text)
                                data = new_text.encode('latin-1')
                            except Exception:
                                pass
                    zout.writestr(item, data)
        os.replace(temp_path, path)
    except Exception as e:
        print(f"Error sanitizing zip-based file {path}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)

def sanitize_pdf_file(path):
    print(f"Sanitizing PDF: {path}")
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF not installed, skipping PDF sanitization.")
        return
        
    try:
        doc = fitz.open(path)
        modified = False
        for page in doc:
            search_terms = [
                "myoffice.mail.onmicrosoft.com", 
                "myoffice.onmicrosoft.com", 
                "ankbs.de", 
                "ankbs", 
                "ANKBS", 
                "Hinweis für die Kundenberatung", 
                "Kundenberatung"
            ]
            for term in search_terms:
                rl = page.search_for(term)
                if rl:
                    for rect in rl:
                        page.add_redact_annot(rect, fill=(1, 1, 1)) # White fill
                    page.apply_redactions()
                    modified = True
                    
        if modified:
            doc.save(path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        doc.close()
    except Exception as e:
        print(f"Error sanitizing PDF file {path}: {e}")

def main():
    evidences_dir = "db/evidences" if os.path.exists("db/evidences") else "evidences"
    print(f"[*] Starting sanitization process in: {evidences_dir}")
    
    for root, dirs, files in os.walk(evidences_dir):
        for file in files:
            path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            if ext == '.json':
                sanitize_json_file(path)
            elif ext in ('.html', '.htm'):
                sanitize_html_file(path)
            elif ext in ('.docx', '.xlsx'):
                sanitize_zip_based_file(path)
            elif ext == '.pdf':
                sanitize_pdf_file(path)

    print("[+] Sanitization process finished successfully!")

if __name__ == "__main__":
    main()
