import sphobjinv as soi
import json
import argparse
import os

def get_all_library_urls(inv_url):
    """
    Sử dụng file objects.inv để lấy URL.
    """
    base_url = inv_url.replace("objects.inv", "")
    print(f"  -> Đang tải và giải mã: {inv_url}")
    
    try:
        inv = soi.Inventory(url=inv_url)
    except Exception as e:
        print(f"  [!] Lỗi khi tải objects.inv: {e}")
        return []

    unique_urls = set()
    for obj in inv.objects:
        html_file = obj.uri.split('#')[0]
        if html_file.endswith('.html'):
            full_url = base_url + html_file
            unique_urls.add(full_url)
            
    url_list = list(unique_urls)
    print(f"  -> Đã trích xuất thành công {len(url_list)} trang HTML duy nhất!")
    return url_list

def categorize_urls(url_list):
    """
    Bộ phân loại tổng quát (Routing Rules) cho 4 Tầng tri thức.
    """
    categorized_docs = []
    
    for url in url_list:
        layer = "Unknown"
        url_lower = url.lower()
        
        # Tầng 1: API Reference
        if "/reference/" in url_lower or "/api/" in url_lower or "/modules/" in url_lower or "/generated/" in url_lower:
            layer = "Tầng 1: API Reference"
            
        # Tầng 4: Release Notes
        elif "/release/" in url_lower or "/whatsnew/" in url_lower or "changelog" in url_lower or "release_notes" in url_lower:
            layer = "Tầng 4: Release Notes"
            
        # Tầng 3: Code Recipes
        elif "tutorial" in url_lower or "howto" in url_lower or "/gallery/" in url_lower or "/auto_examples/" in url_lower:
            layer = "Tầng 3: Code Recipes"
            
        # Tầng 2: Concept
        elif "/user/" in url_lower or "/basics/" in url_lower or "/user_guide/" in url_lower or "getting_started" in url_lower:
            layer = "Tầng 2: Concept"
            
        # Bỏ qua tài liệu C/C++ core
        elif "/f2py/" in url_lower or "/dev/" in url_lower or "/building/" in url_lower:
            continue 
            
        if layer != "Unknown":
            categorized_docs.append({"url": url, "layer": layer})
            
    return categorized_docs

def process_single_library(lib_name, inv_url):
    """
    Hàm xử lý trọn gói cho 1 thư viện.
    """
    print(f"\n{'='*50}\n[*] BẮT ĐẦU XỬ LÝ THƯ VIỆN: {lib_name.upper()}\n{'='*50}")
    
    all_urls = get_all_library_urls(inv_url)
    
    if not all_urls:
        print(f"[!] Bỏ qua {lib_name.upper()} do không lấy được URL.")
        return
        
    final_doc_list = categorize_urls(all_urls)
    
    # Thống kê
    stats = {}
    for doc in final_doc_list:
        stats[doc['layer']] = stats.get(doc['layer'], 0) + 1
        
    print(f"\n  --- THỐNG KÊ KHO TRI THỨC [{lib_name.upper()}] ---")
    for layer, count in stats.items():
        print(f"  {layer}: {count} tài liệu")
        
    folder_path = "data"
    file_name = f"{lib_name}_urls.json"
    file_path = os.path.join(folder_path, file_name)

    file_name_list = "list_library.txt"
    content = file_path +"\n"
    # 1. Tạo thư mục nếu chưa tồn tại
    os.makedirs(folder_path, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(final_doc_list, f, ensure_ascii=False, indent=4)
        
    file_path_list = os.path.join(folder_path,file_name_list)
    with open(file_path_list,'a', encoding="utf-8") as file:
        file.write(content)
    print(f"  [+] Đã lưu danh sách vào file: {file_path}\n Và lưu list vào {file_path_list}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trích xuất URL từ objects.inv")
    
    # Các tham số cho chế độ chạy 1 link
    parser.add_argument("--name", help="Tên thư viện (VD: numpy) - Bắt buộc nếu dùng --inv_url")
    parser.add_argument("--inv_url", help="Đường dẫn đến objects.inv")
    
    # Tham số cho chế độ chạy hàng loạt
    parser.add_argument("--file", help="File txt chứa cấu trúc 'Tên: Link' (VD: inv_url.txt)")
    
    args = parser.parse_args()
    
    # Xử lý Logic chạy từ file TXT
    if args.file:
        if not os.path.exists(args.file):
            print(f"[!] Không tìm thấy file: {args.file}")
            exit(1)
            
        print(f"[*] Đang đọc danh sách từ file: {args.file}")
        with open(args.file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            
        for line in lines:
            # Tách chuỗi tại dấu hai chấm đầu tiên (tham số 1)
            parts = line.split(":", 1)
            if len(parts) == 2:
                lib_name = parts[0].strip()
                url = parts[1].strip()
                process_single_library(lib_name, url)
            else:
                print(f"[!] Bỏ qua dòng sai định dạng: {line}")
                
        print("\n[*] HOÀN TẤT XỬ LÝ TOÀN BỘ FILE TXT!")
        
    # Xử lý Logic chạy thủ công 1 Link (Giữ nguyên tính năng cũ)
    elif args.inv_url:
        if not args.name:
            print("[!] LỖI: Khi truyền --inv_url, bạn bắt buộc phải truyền thêm tham số --name.")
            exit(1)
        process_single_library(args.name, args.inv_url)
        
    else:
        print("[!] LỖI: Bạn phải truyền vào file txt (--file) HOẶC truyền 1 link thủ công (--inv_url kèm --name).")
        parser.print_help()