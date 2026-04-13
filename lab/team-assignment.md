# Phan Cong Nhom

> Muc tieu: ca 5 nguoi deu co it nhat 1 commit tren repo.
## Workflow

`Nhan -> Tan -> Hung -> Ly Ly -> Minh chot cuoi`

- `Nhan` lam xong `lab/index.py` thi chuyen cho `Tan`.
- `Tan` lam xong `lab/rag_answer.py` thi chuyen cho `Hung`.
- `Hung` chay `lab/eval.py` xong thi gui ket qua cho `Ly Ly`.
- `Ly Ly` cap nhat docs va tong hop noi dung nop bai.
- `Minh` theo sat tu dau, ghep code, kiem tra commit, va chay demo cuoi.

## Ai lam file nao

### Nhan
- Lam o file: `lab/index.py`
- Nhiem vu: preprocess, chunking, embedding, build index
- Commit nen co:
  - implement `get_embedding()`
  - implement `build_index()`
  - chinh chunking hoac metadata neu can

### Tan
- Lam o file: `lab/rag_answer.py`
- Nhiem vu: dense retrieval, LLM call, baseline, variant
- Commit nen co:
  - implement `retrieve_dense()`
  - implement `call_llm()`
  - them `retrieve_hybrid()` hoac variant Sprint 3

### Hung
- Lam o file: `lab/eval.py`
- Nhiem vu: chay baseline, variant, scorecard, so sanh A/B
- Commit nen co:
  - cap nhat `BASELINE_CONFIG` va `VARIANT_CONFIG`
  - chay scorecard va hoan thien logic so sanh
  - xuat ket qua baseline/variant neu nhom dung de nop

### Ly Ly
- Lam o file: `lab/docs/architecture.md`, `lab/docs/tuning-log.md`, `lab/reports/individual/`
- Nhiem vu: cap nhat docs, tong hop tuning log, ho tro bao cao
- Commit nen co:
  - dien `architecture.md`
  - dien `tuning-log.md`
  - tao hoac cap nhat report ca nhan

### Minh
- Lam o file: phan tich hop giua `lab/index.py`, `lab/rag_answer.py`, `lab/eval.py`
- Nhiem vu: ghep code, kiem tra ban nop, chay demo cuoi
- Commit nen co:
  - fix loi import hoac ket noi giua cac file
  - cap nhat huong dan chay hoac ghi chu demo
  - chot ban chay end-to-end


## Kiem tra commit

1. Moi nguoi phai tu tao it nhat 1 commit.
2. Moi nguoi commit dung phan viec cua minh.
3. Truoc khi nop, Minh kiem tra:

```bash
git shortlog -sn --all
git log --oneline --all --author="Minh"
git log --oneline --all --author="Nhan"
git log --oneline --all --author="Tan"
git log --oneline --all --author="Hung"
git log --oneline --all --author="Ly Ly"
```

4. Neu ten git chua dung, moi nguoi can set:

```bash
git config user.name "Ten cua ban"
git config user.email "email_cua_ban@example.com"
```
