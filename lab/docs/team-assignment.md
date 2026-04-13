# Phan Cong Nhom 5 Nguoi

## Thanh vien

- Nhan
- Minh
- Tan
- Ly Ly
- Hung

## Phan cong de xuat

### 1. Minh - Nhom truong / Tich hop / Demo cuoi

**Vai tro chinh**
- Theo doi tien do 4 sprint va nhac cac moc ban giao.
- Ghep code tu cac thanh vien vao ban chay cuoi.
- Kiem tra luong `index.py -> rag_answer.py -> eval.py`.
- Chay demo tong va xu ly loi nho khi merge.

**File can nam**
- `lab/index.py`
- `lab/rag_answer.py`
- `lab/eval.py`

**Ban giao**
- Ban code cuoi cung chay duoc end-to-end.
- Cau hinh chay demo va checklist nop bai.

### 2. Nhan - Indexing Owner

**Vai tro chinh**
- Lam preprocessing tai lieu trong `index.py`.
- Cai dat chunking theo heading/paragraph cho hop ly.
- Lam `get_embedding()`.
- Lam `build_index()` va kiem tra du lieu da vao ChromaDB.
- Dam bao metadata co `source`, `section`, `effective_date`, `department`, `access`.

**File can nam**
- `lab/index.py`

**Ban giao**
- Index du 5 tai lieu.
- Chunk preview doc duoc, khong cat do y.
- Thong nhat cho Tan cach dat metadata va embedding model.

### 3. Tan - Retrieval + Generation Owner

**Vai tro chinh**
- Lam `retrieve_dense()` trong `rag_answer.py`.
- Lam `call_llm()`.
- Hoan thien ham `rag_answer()`.
- Test cac cau hoi chinh: SLA, refund, level 3.
- Lam them 1 variant Sprint 3, uu tien `hybrid`.

**File can nam**
- `lab/rag_answer.py`

**Ban giao**
- Baseline dense retrieval chay duoc.
- Cau tra loi co citation va co `sources`.
- Cau thieu context biet abstain.
- Co variant de Hung chay evaluation.

### 4. Hung - Evaluation Owner

**Vai tro chinh**
- Doc `test_questions.json` va expected sources.
- Chay baseline scorecard.
- Chay variant scorecard.
- So sanh A/B trong `eval.py`.
- Tong hop cau nao tot hon, cau nao kem hon, va vi sao.

**File can nam**
- `lab/eval.py`
- `lab/data/test_questions.json`

**Ban giao**
- Ket qua baseline.
- Ket qua variant.
- Bang so sanh A/B va nhan xet ngan.

### 5. Ly Ly - Documentation Owner

**Vai tro chinh**
- Dien `architecture.md`.
- Dien `tuning-log.md`.
- Ghi lai quyet dinh chunk size, overlap, model, retrieval mode.
- Ho tro ca nhom viet bao cao ca nhan theo template.
- Gom ket qua tu Minh, Nhan, Tan, Hung de chot tai lieu nop bai.

**File can nam**
- `lab/docs/architecture.md`
- `lab/docs/tuning-log.md`
- `lab/reports/individual/template.md`

**Ban giao**
- `architecture.md` hoan chinh.
- `tuning-log.md` hoan chinh.
- Danh sach viec can nop cho tung thanh vien.

## Luong phoi hop

1. Nhan xong index thi ban giao ngay cho Tan.
2. Tan xong baseline va variant thi chuyen cho Hung chay eval.
3. Hung co scorecard thi gui cho Ly Ly cap nhat docs.
4. Minh theo sat ca nhom, ghap code, va chot ban nop cuoi.

## Ke hoach 4 gio

### Gio 1
- Minh doc tong the project, chia nhanh task, theo doi tien do.
- Nhan lam `index.py`.
- Ly Ly mo template docs va dien truoc cac muc co the dien san.

### Gio 2
- Tan lam baseline trong `rag_answer.py`.
- Minh test ket noi giua index va retrieval.
- Nhan ho tro neu can doi metadata hoac chunking.

### Gio 3
- Tan lam variant Sprint 3.
- Hung chay `eval.py`, cham scorecard baseline/variant.
- Ly Ly cap nhat `tuning-log.md` theo ket qua that.

### Gio 4
- Minh merge code va chay demo cuoi.
- Hung chot bang so sanh A/B.
- Ly Ly chot docs.
- Moi nguoi viet bao cao ca nhan.

## Ghi chu

- Minh khong om toan bo code ma tap trung dieu phoi va tich hop.
- Nhan va Tan la 2 dau viec code chinh, can trao doi sat ve metadata va embedding model.
- Hung vao evaluation de tach rieng phan kiem chung ket qua.
- Ly Ly giu docs de nhom khong bi thieu deliverables luc nop bai.
