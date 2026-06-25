import re
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import concurrent.futures
import json
import os
import argparse

def clean_sphinx_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content = soup.find(role="main")
    if not main_content:
        main_content = soup.find('div', class_='bd-article-container')
    if not main_content:
        return "" 
    for tag in main_content.find_all(['nav', 'script', 'style', 'footer']):
        tag.decompose()
    for a in main_content.find_all('a', class_='reference external'):
        if '[source]' in a.text:
            a.decompose()
    for pre in main_content.find_all('pre'):
        if '>>>' in pre.text:
            pre['class'] = 'language-python' 
    return str(main_content)

def convert_to_markdown(clean_html):
    markdown_text = md(clean_html, heading_style="ATX", code_language="python", strip=['a'])
    markdown_text = re.sub(r'^(#+\s+.*?)#\s*$', r'\1', markdown_text, flags=re.MULTILINE)
    
    junk_phrases = [r'Go BackOpen In Tab', r'On this page', r'Try it in your browser!']
    for phrase in junk_phrases:
        markdown_text = re.sub(phrase, '', markdown_text, flags=re.IGNORECASE)
        
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
    lines = [line.rstrip() for line in markdown_text.split('\n')]
    
    final_text = '\n'.join(lines).strip()
    final_text = final_text.replace("Go BackOpen In Tab", "").replace("On this page", "")
    return final_text

def process_single_doc(doc_info):
    url = doc_info['url']
    layer = doc_info['layer']
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        raw_html = response.text
        clean_html = clean_sphinx_html(raw_html)
        
        if not clean_html:
            return None
            
        final_markdown = convert_to_markdown(clean_html)
        return {"source_url": url, "layer": layer, "content": final_markdown}
    except Exception as e:
        print(f"[LỖI] {url} -> {e}")
        return None

def main_etl_pipeline(input_file, output_file, is_test_mode=False):
    if not os.path.exists(input_file):
        print(f"[!] Không tìm thấy file {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        docs_list = json.load(f)
        
    if is_test_mode:
        print("[!] ĐANG CHẠY CHẾ ĐỘ TEST (Chỉ lấy 20 bài đầu tiên)")
        docs_list = docs_list[:20]

    results = []
    print(f"[*] Bắt đầu crawl {len(docs_list)} tài liệu từ {input_file}. Vui lòng đợi...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(process_single_doc, doc): doc for doc in docs_list}
        done = 0
        total = len(docs_list)
        for future in concurrent.futures.as_completed(future_to_url):
            data = future.result()
            done += 1
            if done % 50 == 0 or done == total:
                print(f"--- Tiến độ: {done}/{total} ---")
            if data:
                results.append(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"\n[+] HOÀN TẤT! Đã lưu {len(results)} tài liệu vào: {output_file}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl HTML và chuyển đổi thành Markdown cho RAG")
    parser.add_argument("--input", help="File JSON chứa danh sách URL (VD: numpy_urls.json)")
    parser.add_argument("--file", help="File txt chứa danh sách các file JSON (VD: list_json.txt)")
    parser.add_argument("--test", action="store_true", help="Nếu có cờ này, chỉ chạy thử 20 URL đầu tiên của mỗi thư viện")
    
    args = parser.parse_args()
    
    # 1. Xử lý logic chạy từ file .txt chứa danh sách các file JSON
    if args.file:
        if not os.path.exists(args.file):
            print(f"[!] Không tìm thấy file: {args.file}")
            exit(1)
            
        print(f"[*] Đang đọc danh sách file JSON từ: {args.file}")
        with open(args.file, "r", encoding="utf-8") as f:
            # Đọc từng dòng, xóa khoảng trắng và bỏ qua dòng trống
            json_files = [line.strip() for line in f if line.strip()]
            
        for input_file in json_files:
            print(f"\n{'='*60}\n[*] ĐANG XỬ LÝ THƯ VIỆN TỪ FILE: {input_file}\n{'='*60}")
            if not os.path.exists(input_file):
                print(f"[!] Bỏ qua {input_file} vì không tồn tại trên ổ đĩa.")
                continue
                
            base_name = input_file.replace("_urls.json", "").replace(".json", "")
            output_file = f"{base_name}_knowledge_base_full.json"
            main_etl_pipeline(input_file, output_file, args.test)
            
        print("\n[*] HOÀN TẤT CRAWL TOÀN BỘ CÁC THƯ VIỆN TRONG DANH SÁCH!")

    # 2. Xử lý logic chạy 1 file JSON đơn lẻ (Cách cũ)
    elif args.input:
        input_file = args.input
        base_name = input_file.replace("_urls.json", "").replace(".json", "")
        output_file = f"{base_name}_knowledge_base_full.json"
        
        print(f"\n{'='*60}\n[*] ĐANG XỬ LÝ THƯ VIỆN TỪ FILE: {input_file}\n{'='*60}")
        main_etl_pipeline(input_file, output_file, args.test)
        
    else:
        print("[!] LỖI: Bạn phải truyền vào --file (danh sách txt) HOẶC --input (1 file json).")
        parser.print_help()