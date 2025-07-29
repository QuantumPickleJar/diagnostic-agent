from faiss_utils import reindex

if __name__ == "__main__":
    count = reindex()
    if count:
        print(f"[+] Indexed {count} log entries")
    else:
        print("[+] No entries found; cleared index")
