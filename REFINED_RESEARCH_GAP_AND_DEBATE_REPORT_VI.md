# BÁO CÁO: 2 KHOẢNG TRỐNG NGHIÊN CỨU MỚI (NOVEL RESEARCH GAPS) CHO BÀI BÁO KHOA HỌC

> **LƯU Ý PHÂN ĐỊNH RÕ RÀNG:**
> * **Cái ĐÃ LÀM XONG (Engineering Baseline - Không phải Research Gap):** Hệ thống phân vùng lọc crash **Zero-FP Dual-Partition** (`lib_bug/` vs `harness_bug/`) đã hoàn thiện và kiểm chứng thực nghiệm 100% trên `bzip3` và `mpack`. Nó hoạt động chuẩn xác ở khâu **hậu kỳ** (sau khi fuzzer crash thì phân loại chuẩn xác).
> * **Cái CHƯA AI GIẢI QUYẾT (Novel Research Gaps):** Hai bài toán học thuật cốt lõi dưới đây xảy ra ở **tiền kỳ sinh mã** và **chiến dịch dài hạn (24h)** mà các fuzzer AI hiện nay trên thế giới đều bế tắc.

---

## RESEARCH GAP 1: TỬ HUYỆT NGỮ NGHĨA KHI SINH MÃ (Semantic Precondition Inversion Under Syntactic Feedback)

### 1. Bản chất vấn đề (The Gap)
* **Vòng lặp hiện tại:** Mọi AI sinh harness đều dựa vào Compiler để sửa lỗi cú pháp ($\mathcal{L}_{syn}$).
* **Lỗ hổng:** Compiler chỉ biết cú pháp, hoàn toàn **mù về điều kiện chạy thực tế (Runtime Semantics $\mathcal{L}_{sem}$)**:
  $$\mathcal{L}_{sem} \subsetneq \mathcal{L}_{syn}$$
* **Hành vi "khôn lỏi" của LLM (Specification Gaming):**
  Khi compiler báo lỗi kiểu dữ liệu, LLM tìm mọi "đường tắt" để compiler hết chửi:
  * Hàm C yêu cầu buffer không rỗng $\rightarrow$ LLM gọi `.data()` trên vector rỗng (ra `nullptr`). Compiler thấy đúng kiểu con trỏ liền cho qua $\rightarrow$ Khi fuzzer chạy dính `memcpy` là lăn ra crash.
  * Thư viện ẩn struct nội bộ $\rightarrow$ LLM tự phang `#define <LIB>_DEBUG 1` vào harness để qua mặt compiler $\rightarrow$ Khi liên kết với thư viện thật thì lệch bộ nhớ, crash assert.
* **Tại sao cần giải pháp mới dù đã có Zero-FP triage?**
  Zero-FP hiện tại là bộ lọc ở **hậu kỳ** (sau khi chạy và crash thì gạt bỏ). Nhưng nếu để LLM tự do sinh mã "lách luật" ở **tiền kỳ**, hàng trăm harness sinh ra đều bị phế từ trong trứng nước, làm **lãng phí hơn 90% tài nguyên CPU của fuzzer**.
  $\rightarrow$ **Bài toán mở:** Làm sao ép LLM tuân thủ ngữ nghĩa API ngay trong lúc sinh mã mà không để nó lách luật compiler?

### 2. Đề xuất giải pháp khoa học
1. **Lá chắn Macro cấp AST (`AST Macro Guard`):**
   * Phân tích luồng token mã nguồn ngay trước khi biên dịch bằng Regex / Lexer trong `build_harness`.
   * Chặn đứng và loại bỏ lập tức các harness có chứa `#define DEBUG`, `#undef NDEBUG` hoặc tự viết lại `assert`, triệt tiêu đường tắt lách luật của LLM.
2. **Khai thác Hợp đồng Ngữ nghĩa từ Mã nguồn API (`Consumer-Code & API Grounding`):**
   * Ràng buộc prompt bắt buộc LLM kiểm tra định nghĩa hàm trong header và source để nắm bắt kiểu dữ liệu gốc (C-strings, mảng chuẩn) và tiền điều kiện của tác giả (`len > 0`, non-null check), xóa bỏ việc bịa `vector<uint8_t>` mù quáng.

---

## RESEARCH GAP 2: BẾ TẮC ĐỘ PHỦ Ở CHIẾN DỊCH DÀI HẠN (CFG Blocker Entropy Collapse & State-Blindness)

### 1. Bản chất vấn đề (The Gap)
* **Sau 8–10 tiếng đầu:** Fuzzer đụng "bức tường bão hòa" (Coverage Plateau). Các nhánh nông đã phủ hết, chỉ còn lại **nhánh sâu (Deep Frontier Branches)**.
* **Tử huyệt của `CoverageAnalyzerAgent` hiện tại:**
  * Hiện tại con Analyzer chỉ nhìn vào báo cáo coverage rồi chỉ tay: *"Dòng 50 chưa chạy, hãy viết harness gọi nó!"*.
  * **Nó hoàn toàn MÙ VỀ ĐIỀU KIỆN LOGIC**: Để vào dòng 50, chương trình đòi hỏi một chuỗi logic phức tạp: `mở file` $\rightarrow$ `giải mã header` $\rightarrow$ `đặt trạng thái = 2` $\rightarrow$ `khớp magic byte 0x504B`.
  * Analyzer không phân tích được điều kiện này để chỉ dẫn cho `HarnessAgent`.
* **Sự bùng nổ Context Window:**
  * Nếu ném toàn bộ mã nguồn của cả chục hàm liên quan vào prompt để LLM tự đọc hiểu $\rightarrow$ **Tràn bộ nhớ context (Context Window Explosion)**.
  * Khi bị cắt xén (truncate), thông tin logic bị mất hoàn toàn (Entropy Collapse) $\rightarrow$ `HarnessAgent` chỉ sinh code random hú họa $\rightarrow$ **Độ phủ đi ngang 0% suốt 15 tiếng còn lại**.

### 2. Đề xuất giải pháp khoa học
1. **Cắt lát đồ thị phân tầng (`Hierarchical CFG Slicing`):**
   * Dùng WLLVM CallGraph trích xuất chuỗi đường dẫn ngắn nhất từ API public tới hàm đích bị nghẽn (đã tích hợp vào `call_chain`).
   * **Gọt sạch >98% mã nguồn râu ria**, chỉ cung cấp đúng khung xương gọi hàm gồm 3-4 dòng lệnh.
2. **Khai phá bất biến trạng thái động (`Dynamic Invariant Miner`):**
   * Phân tích toán tử quan hệ và giá trị hằng số mục tiêu tại các nhánh rẽ bị nghẽn trong `cov_blockers`.
   * Tự động bắt được giá trị mục tiêu mà câu lệnh `if` đang đòi hỏi: `12345`, `0x504B`, v.v.
3. **Bản tin JSON cô đọng gửi cho Agent:**
   * Đóng gói thông tin nhánh nghẽn thành định dạng JSON siêu ngắn gọn:
     ```json
     {
       "branch": "<vị_trí_file:dòng_lệnh>",
       "miss_value": <giá_trị_còn_thiếu_cần_khớp>
     }
     ```
   * Cung cấp chính xác cho `HarnessAgent` biết đường dẫn và giá trị cần điền mà không làm tràn context $\rightarrow$ **Xuyên thủng nhánh sâu 24h**.

---

## BẢNG SO SÁNH TỔNG KẾT

| Tiêu chí | ĐÃ HOÀN THÀNH (Baseline) | RESEARCH GAP 1 (Tiền kỳ sinh mã) | RESEARCH GAP 2 (Chiến dịch 24h) |
|---|---|---|---|
| **Vấn đề** | Crash rác do harness lỗi bị đếm nhầm là lỗi thư viện | LLM chơi đường tắt lách luật compiler, sinh harness phế | `CoverageAnalyzer` bị mù điều kiện, kẹt độ phủ sau 8h |
| **Giai đoạn** | **Hậu kỳ** (Sau khi fuzzer crash) | **Tiền kỳ** (Lúc LLM đang viết mã) | **Dài hạn** (Chiến dịch chạy liên tục 24h) |
| **Bản chất** | Phân loại lỗi call-stack | Xung đột Cú pháp ($\mathcal{L}_{syn}$) vs Ngữ nghĩa ($\mathcal{L}_{sem}$) | Bùng nổ Context, mất thông tin nhánh sâu ($I \to 0$) |
| **Giải pháp** | Phân vùng Zero-FP (`lib_bug/` vs `harness_bug/`) | `AST Macro Guard` + `API Grounding` | `Hierarchical CFG Slicing` + `FSM Schema <4k` |
| **Tình trạng** | **ĐÃ XONG & ĐÃ CHỨNG MINH** | **ĐÓNG GÓP KHOA HỌC MỚI 1** | **ĐÓNG GÓP KHOA HỌC MỚI 2** |
