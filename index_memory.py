from faiss_utils import reindex

if __name__ == "__main__":
    if reindex():
        print("[+] Reindexed recall log")
    else:
        print("[+] No entries found; cleared index")
