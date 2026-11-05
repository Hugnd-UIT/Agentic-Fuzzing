# BÁO CÁO PHÂN TÍCH CHUYÊN SÂU CODEBASE, PHẢN BIỆN HỌC THUẬT, ĐỊNH VỊ RESEARCH GAP VÀ THIẾT KẾ KẾ HOẠCH THỰC NGHIỆM CHO HỆ THỐNG AGENTIC FUZZING

**Đơn vị thực hiện**: Ban Nghiên cứu & Phát triển Hệ thống Fuzzing Tự trị (Agentic Fuzzing Core Research Team)  
**Tài liệu tham chiếu**: Hệ thống mã nguồn `Agentic Fuzzing` (kế thừa và mở rộng từ *FuzzAgent*, Lyu et al., 2026, arXiv:2605.14431)  
**Mục tiêu thực nghiệm trọng tâm**: Thư viện `mpack` (v1.1.1), `bzip3` (v1.5.1), `simdjson` (v3.10.1)  
**Thời gian hoàn thành**: Tháng 11 Năm 2026  
**Trạng thái kiểm định**: Publication-Grade Scientific Report & Comprehensive Engineering Blueprint  

---

## TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Kiểm thử mờ tự động (Automated Fuzz Testing) cho các thư viện phần mềm C/C++ là một trong những trụ cột then chốt bảo đảm an toàn hệ thống thông tin toàn cầu. Trong giai đoạn 2024–2026, sự trỗi dậy của các mô hình ngôn ngữ lớn (LLM) và kiến trúc đa tác tử tự trị (Multi-Agent Systems) đã định hình lại hoàn toàn cục diện fuzzing, chuyển dịch từ việc sinh harness tĩnh đơn lẻ (Epoch 2: TitanFuzz, Fuzz4All) hay vòng lặp sửa lỗi cục bộ (Epoch 4: Google OSS-Fuzz-Gen) sang mô hình tiến hóa tự trị đa vai trò (Epoch 5: FuzzAgent). 

Hệ thống **Agentic Fuzzing** được thiết kế nhằm hiện thực hóa một quy trình khép kín: từ phân tích mã nguồn thư viện, tự động biên dịch nhị phân có gắn thiết bị đo (sanitizers & coverage instrumentation), tổng hợp bộ từ điển và hạt giống (seeds), sinh mã harness C++ bao bọc chuỗi API phức tạp, điều phối cụm fuzzing AFL++ đa nhân, đến tự động phân tích crash bằng GDB và phân tích độ phủ phân cấp để phản hồi ngược (closed-loop evolutionary feedback).

Tuy nhiên, qua kiểm toán kỹ thuật chuyên sâu và kiểm tra thực chứng từ chiến dịch fuzzing kéo dài **hơn 17 giờ liên tục trên thư viện `mpack`**, chúng tôi phát hiện hệ thống đang đối mặt với những **vết nứt cấu trúc nghiêm trọng (systemic structural failures)** làm suy giảm sâu sắc hiệu năng, gây lãng phí tài nguyên tính toán và tạo ra các ảo tưởng sai lệch về độ tin cậy:
1. **Lỗi lu mờ Crash do bão hòa đơn nhân (Saturation Shadowing Bug trong `run_fuzzer`)**: Cụm fuzzing đa nhân (1 Master + 7 Slaves) bị giám sát độc quyền thông qua tiến trình Master. Khi Master đạt ngưỡng bão hòa độ phủ sớm (saturation sau 10 phút), hệ thống gán nhãn `PLATEAU`, kích hoạt điều kiện `if not plateau:` dẫn tới **bỏ qua hoàn toàn việc thu hoạch crash**, và khối `finally` tiêu diệt toàn bộ các tiến trình Slave. Hàng loạt crash hợp lệ tìm thấy bởi các Slave bị xóa sổ vĩnh viễn khỏi đĩa mà không hề được đưa vào pipeline xử lý.
2. **Chiếm đoạt Macro tiền xử lý (Macro Hijacking)**: Dưới áp lực của vòng lặp tự sửa lỗi biên dịch (compilation repair loop), LLM tự ý chèn các macro nội bộ như `#define MPACK_DEBUG 1` hoặc `#define MPACK_INTERNAL 1`. Việc này phá vỡ hoàn toàn tính tương thích nhị phân (ABI) giữa harness và thư viện tĩnh `libmpack.a` (vốn được biên dịch ở chế độ release), kích hoạt các assertion nội bộ không tồn tại ở môi trường thực tế và gây ra hàng loạt crash giả (`SIGABRT`).
3. **Vi phạm tiền điều kiện và ngữ nghĩa con trỏ (Pointer Semantics & Precondition Violations)**: Việc LLM áp dụng rập khuôn mẫu code `std::vector::data()` trên container rỗng dẫn tới việc truyền con trỏ `nullptr` vào các hàm C tiêu chuẩn (như `memcpy(dest, NULL, 0)`), kích hoạt lỗi UndefinedBehaviorSanitizer `invalid-null-argument`. Cùng với việc truyền các giá trị biên vi phạm assertion (`limit = 0`), 100% crash trong chiến dịch mpack 17h đều là **Harness Misuse Bug**. Tuy nhiên, bộ lọc Gatekeeper chỉ kiểm tra Frame #0 khiến tất cả các lỗi này bị gán nhãn sai thành `LIBRARY_BUG`, làm tê liệt pipeline phân tích sâu trong hàng chục giờ.
4. **Mất trực giao vai trò và Lỗi đảo ngược Boolean tai hại trong `CoverageAnalyzerAgent`**: Vai trò phân tích độ phủ bị xâm lấn khi tác tử này cố gắng sinh mã C++ thay vì chỉ định API mục tiêu. Đặc biệt, cuộc kiểm toán đã phát hiện một **lỗi logic đảo ngược mang tính thảm họa** tại `CoverageAnalyzerAgent.no_fuzzer_in_plateau()` (`src/agents/cov-analyzer/agent.py:46-51`): hàm trả về `True` khi CÓ fuzzer đạt plateau, khiến tác tử luôn thoát sớm với thông báo không tìm thấy fuzzer nào ở trạng thái plateau. Kết quả là thư mục `coverage_guidance/` hoàn toàn trống rỗng trong suốt 17 giờ, triệt tiêu toàn bộ vòng phản hồi tiến hóa của hệ thống.

Báo cáo này cung cấp một nghiên cứu toàn diện, phản biện học thuật sắc sảo, định vị chính xác hai Research Gap lý thuyết nền tảng (Khoảng cách giữa Tính hợp lệ cú pháp và Hợp đồng ngữ nghĩa; Sự suy giảm entropy trong chiến dịch dài hạn), đề xuất 4 giải pháp công nghệ công nghiệp triệt để (Multi-Instance Telemetry Engine, Clang AST Macro Guard, SafeBufferAdapter & Two-Tier Gatekeeper, JSON Guidance Contract), và xây dựng kế hoạch thực nghiệm đối chứng chuẩn mực khoa học trên 3 thư viện `bzip3`, `simdjson`, `mpack`.

---

## 1. TỔNG QUAN HỆ THỐNG VÀ KIẾN TRÚC AGENTIC FUZZING

### 1.1 Sứ mệnh và Bối cảnh Phát triển
Hệ thống **Agentic Fuzzing** được xây dựng nhằm giải quyết bài toán cốt lõi của kiểm thử bảo mật phần mềm: *Làm thế nào để kiểm thử tự động các thư viện mã nguồn đóng hoặc mở phức tạp mà không đòi hỏi chuyên gia con người phải tự tay viết các đoạn mã fuzz driver (harness) chuyên biệt*.

Được kế thừa và phát triển mở rộng từ kiến trúc FuzzAgent (Lyu et al., 2026), hệ thống hướng tới việc chuyển đổi toàn bộ vòng đời kiểm thử mờ thành một đồ thị tương tác đa tác tử có khả năng tự nhận thức trạng thái (State-Aware Multi-Agent System). Thay vì chỉ sử dụng LLM như một công cụ sinh mã một lần (one-shot generation), Agentic Fuzzing tích hợp các công cụ nhị phân cấp thấp (`clang`, `llvm-cov`, `afl-fuzz`, `gdb`, `readelf`) vào giao diện giao tiếp tác tử (Agent-Communication-Interface - ACI), cho phép hệ thống quan sát các phản hồi runtime, đo lường sự bão hòa của đồ thị luồng điều khiển (CFG), và tự động thích ứng chiến lược thăm dò.

### 1.2 Phân tích Chi tiết Kiến trúc Điều phối Đa Tác tử (Multi-Agent Architecture)

Kiến trúc hệ thống phân rã bài toán fuzzing thành các vai trò chuyên biệt hóa cao độ, được điều phối tập trung bởi một tác tử quản lý:

```
                                +-----------------------------+
                                |        ManagerAgent         |
                                |  (Bộ Điều Khiển Máy Trạng   |
                                |   Thái FSM & Điều Phối ACI) |
                                +--------------+--------------+
                                               |
        +-----------------------+--------------+--------------+-----------------------+
        |                       |                             |                       |
        v                       v                             v                       v
+----------------+      +----------------+            +----------------+      +----------------+
|  BuilderAgent  |      | DictGenerator/ |            |  HarnessAgent  |      |  FuzzerAgent   |
| (Thiết lập môi |      | SeedGenerator  |            | (Tổng hợp & Sửa|      | (Quản lý Cụm   |
| trường build)  |      | (Khai phá mẫu) |            |  mã C++ Driver)|      | AFL++ Đa Nhân) |
+----------------+      +----------------+            +-------+--------+      +-------+--------+
                                                              |                       |
                                                              v                       v
                                                      +----------------+      +----------------+
                                                      | build_harness  |      | Zero-FP Triage |
                                                      | (Biên dịch     |      | Gatekeeper     |
                                                      |  Sanitizers)   |      | (Lọc Frame #0) |
                                                      +----------------+      +-------+--------+
                                                                                      |
                                                              +-----------------------+
                                                              |
                                                              v
+--------------------------------+            +--------------------------------+
|     CoverageAnalyzerAgent      |            |       CrashAnalyzerAgent       |
|  (Phân tích Đồ thị Độ phủ &    |<-----------+  (GDB Debugger Triage, Giảm    |
|   Định hướng Nhánh Blocker)    |  (Plateau) |   thiểu PoC, Báo cáo Lỗ hổng)  |
+--------------------------------+            +--------------------------------+
```

Hệ thống bao gồm 7 tác tử chuyên trách và 1 cơ chế gác cổng:

1. **ManagerAgent (`src/agents/manager/agent.py`, `prompt.py`)**:
   - Đóng vai trò là hạt nhân điều hành (Orchestrator Kernel), duy trì máy trạng thái hữu hạn (FSM) của chiến dịch.
   - Quản lý hàng đợi tác vụ (`TaskQueue`) và theo dõi tiến độ thời gian thực.
   - Trước mỗi chu kỳ ra quyết định, hàm `register_agent_pre_call` gọi công cụ `check_status` (`src/tools/analysis/bin/check_status`) để quét toàn diện cấu trúc thư mục đầu ra `$OUTPUT`. `check_status` kiểm tra tính sẵn sàng của thư viện tĩnh, từ điển, hạt giống, danh sách harness (`harness_XXX.cpp`), trạng thái thực thi fuzzer (`fuzzer_stat.json`), và các chỉ dẫn độ phủ (`coverage_guidance/`).
   - Dựa trên snapshot trạng thái, `ManagerAgent` phân tích và gửi chỉ thị thực thi tới các tác tử con thông qua giao thức `send_agent_task`. Khi tác tử con hoàn tất, `handle_agent_action` ghi nhận kết quả và cập nhật lịch sử tương tác.

2. **BuilderAgent (`src/agents/builder/agent.py`, `prompt.py`)**:
   - Chịu trách nhiệm phân tích hệ thống build gốc của dự án (Makefile, CMake, Meson, Autotools).
   - Tự động sinh kịch bản `build.sh` và thiết lập 3 chế độ biên dịch thư viện mục tiêu:
     * *Sanitizer Build*: Biên dịch thư viện mục tiêu tích hợp AddressSanitizer (ASAN) và UndefinedBehaviorSanitizer (UBSan) với cờ `-fsanitize=address,undefined -g -O1`.
     * *Coverage Build*: Biên dịch tích hợp Source-based Code Coverage với cờ `-fprofile-instr-generate -fcoverage-mapping`.
     * *CMPLOG / Fuzzing Build*: Biên dịch tối ưu hóa phục vụ AFL++ với các cờ đo lường giá trị so sánh (comparison logging) nhằm hỗ trợ bộ biến dị vượt qua các nhánh rẽ giá trị hằng số (magic bytes).

3. **DictionaryGeneratorAgent & SeedGeneratorAgent (`src/agents/dict-generator/`, `src/agents/seed-generator/`)**:
   - `DictionaryGeneratorAgent` quét cây cú pháp trừu tượng (AST) và mã nguồn C/C++ để trích xuất các chuỗi ký tự hằng số (string literals), giá trị magic numbers, và các token định dạng (JSON, MsgPack, BZip) xuất ra tệp `.dict`.
   - `SeedGeneratorAgent` phân tích tài liệu và các thư mục kiểm thử đơn vị (`tests/`, `examples/`) để thu thập hoặc tự tổng hợp các tệp đầu vào hợp lệ nhỏ gọn (corpus seeds), bảo đảm fuzzer khởi đầu với độ phủ cơ sở tốt nhất.

4. **HarnessGeneratorAgent (`src/agents/harness-generator/agent.py`, `prompt.py`)**:
   - Chịu trách nhiệm quan trọng nhất trong việc mở rộng bề mặt tấn công: tổng hợp mã nguồn driver C++ (`harness_XXX.cpp`).
   - Sử dụng thư viện `FuzzedDataProvider` (`<fuzzer/FuzzedDataProvider.h>`) của LLVM để ánh xạ luồng byte ngẫu nhiên `const uint8_t* data, size_t size` thành các kiểu dữ liệu có cấu trúc, số nguyên, mảng byte, và chuỗi ký tự.
   - Thiết kế mã harness theo hợp đồng 3 giai đoạn: *Khởi tạo (Setup/Initialization) $\to$ Thao tác API mục tiêu (Target Invocation) $\to$ Giải phóng tài nguyên (Teardown/Cleanup)*.
   - Tích hợp công cụ biên dịch `build_harness` (`src/tools/harness/bin/build_harness`) để tự động kiểm tra cú pháp, liên kết thư viện, và sửa lỗi biên dịch lặp lại theo phản hồi của Clang.

5. **FuzzerAgent (`src/agents/fuzzer/agent.py`, `prompt.py`)**:
   - Quản lý vòng đời thực thi của các tiến trình fuzzing thông qua công cụ `run_fuzzer` (`src/tools/fuzz/bin/run_fuzzer`).
   - Khởi tạo cụm fuzzing song song đa nhân AFL++ tận dụng cơ chế chia sẻ hạt giống (master-slave syncing).
   - Theo dõi tốc độ thực thi (`execs/sec`), kích thước bitmap (`bitmap_cvg`), số cạnh mới phát hiện (`edges_found`), và phát hiện trạng thái bão hòa độ phủ (`FuzzerExecutionState.PLATEAU`).

6. **CoverageAnalyzerAgent (`src/agents/cov-analyzer/agent.py`, `prompt.py`)**:
   - Khi một fuzzer rơi vào trạng thái bão hòa (`PLATEAU`), tác tử này được kích hoạt để phân tích dữ liệu độ phủ thô trích xuất từ `llvm-profdata` và `llvm-cov`.
   - Sử dụng các công cụ phân tích phân cấp: `cov_overview` (mức toàn cục), `cov_api` (mức hàm/API), `cov_blockers` (mức nhánh rẽ bị chặn).
   - Xác định các API chưa được chạm tới hoặc các điều kiện nhánh chưa được thỏa mãn, từ đó xuất bản tài liệu chỉ dẫn (`$OUTPUT/coverage_guidance/harness_XXX_guidance.md`) để điều hướng `HarnessGeneratorAgent` viết các harness mới nhắm mục tiêu chính xác.

7. **CrashAnalyzerAgent (`src/agents/crash-analyzer/agent.py`, `prompt.py`)**:
   - Được triệu hồi khi có crash được ghi nhận. Tác tử khởi chạy phiên debug tự động bằng GDB thông qua công cụ `debug_crash` (`src/tools/crash/bin/debug_crash`).
   - Tự động thu thập Call Stack Trace, kiểm tra thanh ghi và giá trị các biến nội bộ tại thời điểm xảy ra ngoại lệ, trích xuất mã khai thác tối thiểu (PoC minimization).
   - Phân tích ranh giới tin cậy (Trust Boundary Analysis) để kết luận đây là lỗi thực sự của thư viện (`LIBRARY_BUG`) hay lỗi do harness sử dụng sai API (`HARNESS_BUG`).

8. **Zero-FP Triage Gatekeeper (`pre_triage_and_dedup_crashes` trong `run_fuzzer`)**:
   - Một tầng lọc trung gian tốc độ cao được tích hợp trực tiếp trong `run_fuzzer` nhằm loại bỏ sơ bộ các crash trùng lặp (deduplication bằng hash tín hiệu và con trỏ lệnh) và phát hiện sớm các crash do harness tự gây ra trước khi chuyển giao cho LLM phân tích sâu.

### 1.3 Luồng Dữ liệu và Vòng đời Tương tác Giữa các Agents

Vòng đời tương tác giữa các tác tử được duy trì thông qua hệ thống tệp lưu trữ phản chiếu (Persistent Storage Reflection) tại thư mục `$OUTPUT`:

```
$OUTPUT/
├── build/                 # Chứa các bản build thư viện (sanitizer, coverage, cmplog)
├── dict/                  # Từ điển tokens phục vụ bộ biến dị AFL++
├── seeds/                 # Tập hạt giống ban đầu
├── harnesses/             # Mã nguồn C++ và tệp nhị phân executable harness
│   ├── harness_000.cpp
│   └── harness_000
├── fuzzers/               # Không gian làm việc của AFL++ cluster
│   └── fuzzer_000/
│       ├── output/
│       │   ├── default/   # Thư mục làm việc của Master AFL
│       │   └── slave0/    # Thư mục làm việc của Slave AFL
│       └── crashes/       # Crash artifacts được staged
├── coverage_guidance/     # Chỉ dẫn độ phủ từ CoverageAnalyzerAgent
├── crash_reports/         # Báo cáo phân tích chuyên sâu từ CrashAnalyzerAgent
│   ├── library_bug/
│   └── harness_bug/
└── .cache/
    └── fuzzer_stat.json   # Snapshot trạng thái toàn bộ fuzzer (FSM Registry)
```

Luồng tương tác chuyển tiếp diễn ra qua 4 pha chính:
- **Pha 1 (Bootstrapping)**: `ManagerAgent` $\to$ `BuilderAgent` $\to$ `DictGenerator` / `SeedGenerator`. Kết quả là các bản build thư viện sẵn sàng và tập hạt giống cơ sở được chuẩn bị.
- **Pha 2 (Exploration)**: `ManagerAgent` điều phối `HarnessGeneratorAgent` tạo các harness đầu tiên nhắm vào các API bề mặt (surface APIs). `build_harness` kiểm tra biên dịch; nếu thành công, `ManagerAgent` kích hoạt `FuzzerAgent` triển khai cụm AFL++.
- **Pha 3 (Evaluation & Triage)**: `run_fuzzer` thực thi. Nếu phát hiện crash, tầng Gatekeeper lọc sơ bộ; nếu vượt qua gatekeeper, `CrashAnalyzerAgent` vào cuộc để xác minh và sinh báo cáo lỗi.
- **Pha 4 (Evolutionary Guidance)**: Nếu cụm fuzzer đạt trạng thái bão hòa độ phủ (`PLATEAU`), `CoverageAnalyzerAgent` được kích hoạt để phân tích các nhánh bị chặn, tạo tệp chỉ dẫn mới và kích hoạt lại `HarnessGeneratorAgent` bước vào vòng lặp tiến hóa tiếp theo.

---

## 2. KIỂM TOÁN CHUYÊN SÂU VÀ MỔ XẺ CĂN NGUYÊN GỐC RỄ 4 VẤN ĐỀ CỐT LÕI TỪ CHIẾN DỊCH MPACK 17H+

Chiến dịch thực nghiệm liên tục hơn 17 giờ trên thư viện giải mã nhị phân `mpack` đã cung cấp tập dữ liệu thực chứng vô giá về hành vi của hệ thống Agentic Fuzzing trong môi trường sản xuất dài hạn. Cuộc kiểm toán dòng lệnh chi tiết đã bóc tách chính xác 4 khiếm khuyết mang tính hệ thống.

---

### 2.1 Saturation Shadowing Bug trong `run_fuzzer`

#### 2.1.1 Bối cảnh và Hiện tượng Thực tế
Trong chiến dịch `mpack`, hệ thống khởi chạy cụm AFL++ song song gồm 1 Master (`-M default`) và 7 Slaves (`-S slave0` đến `-S slave6`). 
Kiểm tra thực tế cấu trúc đĩa tại thư mục `.cache` cho thấy:
- Tại `output/mpack/.cache/fuzzers/001/output/slave0/crashes/`, tệp crash nhị phân `id:000000,sig:09,...` tồn tại thực tế.
- Trong tệp log `output/mpack/.cache/fuzzers/001/output/slave_0.log` dòng 183 ghi rõ: 
  `Statistics: 175 new corpus items found, 21.21% coverage achieved, 1 crashes saved`.
- Các slave khác (`slave1`, `slave2`, `slave5`) cũng phát hiện các crash tương tự.
- **Thế nhưng**, trong tệp quản lý trạng thái toàn cục `output/mpack/.cache/fuzzer_stat.json`, đối tượng `fuzzer_001` lại được ghi nhận với:
  ```json
  "state": "PLATEAU",
  "crashes": 0,
  "execution_time": 20.0
  ```
- Toàn bộ các crash tìm được bởi các tiến trình Slave đã hoàn toàn bị lờ đi, không được chuyển vào thư mục `crashes/`, và `CrashAnalyzerAgent` hoàn toàn không nhận được bất kỳ tín hiệu nào để xử lý!

#### 2.1.2 Mổ xẻ Chi tiết Từng Dòng Mã và Cơ chế Phát sinh
Lỗi này bắt nguồn từ chuỗi sai lầm nối tiếp nhau trong tệp `src/tools/fuzz/bin/run_fuzzer`:

**Vị trí 1: Thu hẹp Telemetry độc quyền trên tiến trình Master (Dòng 292–314)**:
```python
292: def parse_cov_detail_from_afl_log(output_dir: str):
293:     fuzzer_stats_file = os.path.join(output_dir, "default", "fuzzer_stats")
294:     if not os.path.exists(fuzzer_stats_file):
295:         return None
296:     bitmap_path = os.path.join(output_dir, "default", "fuzz_bitmap")
...
307:     execs = int(stats["execs_done"])
308:     exec_sec = float(stats["execs_per_sec"])
309:     map_size = float(stats["bitmap_cvg"].strip("%"))
310:     edges = int(stats["edges_found"])
311:     crashes = int(stats["saved_crashes"])
312:     features = parse_afl_dynamic_features_from_bitmap(bitmap_path)
313:     return execs, map_size, edges, exec_sec, crashes, features
```
*Phân tích*: Đường dẫn tệp thống kê được hardcode cứng tới `default/fuzzer_stats` và `default/fuzz_bitmap`. Toàn bộ dữ liệu tiến độ của 7 slave (`slave0/` đến `slave6/`) bị bỏ qua hoàn toàn. Khi các slave tiếp tục mở rộng đường biên độ phủ hoặc phát hiện crash, biến giám sát trung tâm vẫn hoàn toàn mù tịt.

**Vị trí 2: Hủy bỏ giá trị Crashes trong vòng lặp giám sát (Dòng 682–700)**:
```python
684:     detail = parse_cov_detail_from_afl_log(output_dir)
...
695:     epoch, _, edges, exec_sec, _, features = detail
```
*Phân tích*: Tại dòng 695, phần tử thứ 5 được trả về từ hàm `detail` (chính là biến `crashes`) được gán thẳng vào biến vô danh `_` và bị vứt bỏ. Ngay cả khi bản thân tiến trình Master có ghi nhận `saved_crashes > 0` trong `fuzzer_stats`, logic của vòng lặp cũng không hề kiểm tra biến này để chuyển trạng thái!

**Vị trí 3: Gán nhãn PLATEAU vô điều kiện khi Master bão hòa (Dòng 724–735)**:
```python
724:     if coverage_theta < COVERAGE_SATURATION_THRESHOLD and ft_theta < COVERAGE_FT_SATURATION_THRESHOLD:
725:         print(f"[+] ... Coverage saturation reached. Exit.")
726:         break
...
732: fuzzer_info.state = FuzzerExecutionState.PLATEAU
733: fuzzer_info.execution_time = elapsed_time
734: fuzzer_info.finish_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
735: ProjectUtils.save_fuzzer_profile(fuzz_profile)
...
743: return True, False  # is_plateau = True
```
*Phân tích*: Tiến trình Master trong AFL++ chủ yếu chạy các đột biến tất định (deterministic stages) vốn có tốc độ bão hòa nhanh hơn các chiến lược ngẫu nhiên của Slaves. Khi độ phủ của Master chững lại trong 10 phút, vòng lặp lập tức kích hoạt `break`, gán đè trạng thái `PLATEAU` vào hồ sơ fuzzer mà không hề kiểm tra xem có bất kỳ crash nào đang nằm trong thư mục của các Slaves hay không.

**Vị trí 4: Bỏ qua hàm sao chép Crash khi cờ `plateau == True` (Dòng 826–831) — "The Smoking Gun"**:
```python
826: plateau, _ = execution_until_coverage_saturation(master_proc, fuzzer_id, fuzz_log, True, all_procs=procs)
827: if not plateau:
828:     copy_afl_crashes_to_crash_dir(fuzzer_id)
829:     number_of_crashes = len(os.listdir(crash_dir)) if os.path.exists(crash_dir) else 0
830:     print(f"[!] WARN: Fuzzer terminated due to finding {number_of_crashes} crashes...")
```
*Phân tích*: Đây là lỗi logic trí mạng nhất trong hệ thống. Lệnh gọi hàm `copy_afl_crashes_to_crash_dir(fuzzer_id)` bị đặt bên trong khối điều kiện `if not plateau:`. Khi Master bão hòa dẫn đến `plateau == True`, nhánh `if` bị bỏ qua! Kết quả là hàm thu hoạch crash **không bao giờ được thực thi**.

**Vị trí 5: Tiêu diệt tiến trình và Xóa sổ tàn dư (Dòng 833–847 & Dòng 871)**:
Ngay sau đó, khối lệnh `finally` (dòng 833–847) được thực thi:
```python
833: finally:
834:     for proc in procs:
835:         kill_fuzzer_process(proc.pid, sig=signal.SIGTERM, include_parent=True)
```
Tất cả các tiến trình Master và Slaves bị gửi tín hiệu `SIGTERM` và `SIGKILL` cưỡng chế dừng lại.
Kinh hoàng hơn, tại dòng 871:
```python
871: shutil.rmtree(output_dir, ignore_errors=True)
```
Trong lần chạy tiếp theo, toàn bộ thư mục `.cache/fuzzers/<id>/output` (nơi lưu giữ các tệp crash của Slaves chưa kịp sao chép) bị xóa sạch hoàn toàn khỏi đĩa cứng. Hàng trăm giờ fuzzing của cụm máy bị tiêu hủy không để lại dấu vết.

---

### 2.2 Macro Hijacking trong Harness Generation

#### 2.2.1 Hiện tượng Chiếm đoạt Macro Nội bộ
Trong quá trình tổng hợp harness và tự sửa lỗi biên dịch lặp lại, khi gặp phải các lỗi thiếu định nghĩa kiểu hoặc muốn truy cập các hàm kiểm tra trạng thái, tác tử `HarnessGeneratorAgent` thường xuyên tự ý đưa các định nghĩa macro riêng tư vào đầu tệp C++.

Dẫn chứng thực tế từ mã nguồn harness được sinh ra trong chiến dịch `mpack` (`output/mpack/harnesses/`):
- **`harness_008.cpp`** (Dòng 7–13, Dòng 28–30):
  ```cpp
  #ifndef MPACK_DEBUG
  #define MPACK_DEBUG 1
  #endif
  #ifndef MPACK_STDIO
  #define MPACK_STDIO 1
  #endif
  ...
  #ifndef mpack_node_print_file
  #define mpack_node_print_file mpack_node_print_to_file
  #endif
  ```
- **`harness_016.cpp`** (Dòng 8): `#define MPACK_INTERNAL 1`
- **`harness_017.cpp`** (Dòng 8): `#define MPACK_INTERNAL 1`

#### 2.2.2 Phân tích Cơ chế Sai lệch ABI và Đổ vỡ Runtime
Hiện tượng "Macro Hijacking" dẫn tới sự phá hủy nghiêm trọng tính toàn vẹn của quá trình kiểm thử thông qua 3 cơ chế:

1. **Sai lệch Giao diện Nhị phân Ứng dụng (ABI Desynchronization)**:
   - Thư viện tĩnh mục tiêu `libmpack.a` được `BuilderAgent` biên dịch một lần duy nhất lúc khởi động hệ thống ở chế độ Release (không có cờ `-DMPACK_DEBUG=1`).
   - Trong kiến trúc mã nguồn C của `mpack` (và đại đa số thư viện hệ thống), cờ `MPACK_DEBUG` làm thay đổi trực tiếp kích thước và cấu trúc bộ nhớ (struct memory layout) của các kiểu dữ liệu cốt lõi như `mpack_node_data_t`, `mpack_reader_t`, và `mpack_tree_t`. Cụ thể, khi có `MPACK_DEBUG`, các trường theo dõi assertion, con trỏ danh sách liên kết kiểm tra ranh giới trang (canary tracking pointers) được chèn thêm vào cấu trúc struct.
   - Khi `harness_008.cpp` được biên dịch với `#define MPACK_DEBUG 1`, trình biên dịch Clang tạo ra mã máy với các giá trị dịch chuyển offset của struct theo layout Debug. Nhưng khi liên kết (link) với `libmpack.a`, các hàm bên trong thư viện lại thao tác trên bộ nhớ theo layout Release!
   - *Hậu quả*: Sự sai lệch offset dẫn tới việc ghi đè bộ nhớ chéo (memory corruption), làm hỏng ngăn xếp/vùng nhớ heap, và gây ra các tín hiệu crash giả `SIGABRT` hoặc `SIGSEGV` ngay khi gọi các hàm cơ bản (đây chính là nguyên nhân fuzzer_008 crash với `sig:06`).

2. **Kích hoạt Assertion Không Hợp lệ (Assert Poisoning)**:
   - Macro `MPACK_DEBUG` kích hoạt các macro kiểm tra nghiêm ngặt `mpack_assert(...)`. Trong môi trường Release, khi gặp dữ liệu biến dị không hợp lệ, thư viện thực hiện cơ chế phục hồi mềm (đặt mã lỗi `mpack_error_invalid`). Tuy nhiên, khi bật debug, assertion chuyển thành lệnh gọi `abort()`. Fuzzer biến một trường hợp xử lý lỗi bình thường thành một sự cố crash nghiêm trọng, làm sai lệch kết quả đo lường độ tin cậy phần mềm.

3. **Xâm phạm Ranh giới Đóng gói (Encapsulation Breach)**:
   - Việc định nghĩa `#define MPACK_INTERNAL 1` cho phép LLM gọi trực tiếp các hàm nội bộ không công khai (như `mpack_load_u8`). Các hàm này không có cơ chế phòng vệ tham số đầu vào vì chúng giả định rằng lớp API công khai đã kiểm tra tính hợp lệ trước đó. Fuzzer gọi trực tiếp hàm nội bộ sẽ kích hoạt crash ngay lập tức, hoàn toàn vô giá trị trong việc đánh giá an ninh của bề mặt tấn công công khai.

#### 2.2.3 Lỗ hổng trong Pipeline `build_harness`
Tại sao các macro này có thể vượt qua khâu kiểm soát?
- Trong `src/agents/harness-generator/prompt.py` (dòng 28 & 389), nhóm phát triển đã đưa vào lời nhắc tiêu cực (negative prompt): *"Defining debug macros in harnesses... skip it"*. Tuy nhiên, ở Pha 5 (Issue Resolution, dòng 354–365), prompt lại yêu cầu: *"Try your best to fix the issue... apply specific fixes based on error messages"*. Khi gặp lỗi biên dịch, LLM ưu tiên giải quyết lỗi biên dịch trước mắt và sẵn sàng phá vỡ quy tắc tiêu cực.
- Trong công cụ `src/tools/harness/bin/build_harness`: Hoàn toàn **không có bất kỳ bộ tiền lọc tĩnh (pre-compilation linting) hay bộ kiểm tra token nào**. Mã nguồn harness được truyền thẳng vào lệnh `clang++` mà không qua bước kiểm định các định ngữ tiền xử lý cấm.

---

### 2.3 Precondition / Pointer Semantics Violations & Lỗi Triage Gatekeeper

#### 2.3.1 Hiện tượng Anti-Pattern: `std::vector::data()` trên Container Rỗng
Kiểm tra toàn bộ 5 báo cáo crash được ghi nhận trong thư mục `output/mpack/crash_reports/harness_bug/` từ chiến dịch 17h cho thấy một tỷ lệ gây sốc: **100% crash đều là lỗi do mã harness sử dụng sai API (Harness Misuse Bug)**.

Dẫn chứng từ `crash_000` (`fuzzer_001` nhắm vào hàm `mpack_write_native` tại `mpack-writer.c:536`):
Mã nguồn trong `harness_001.cpp` được LLM viết như sau:
```cpp
size_t bin_len = fdp.ConsumeIntegralInRange<size_t>(0, 128);
std::vector<uint8_t> bin_data = fdp.ConsumeBytes<uint8_t>(bin_len);
mpack_write_bin(writer, reinterpret_cast<const char*>(bin_data.data()), static_cast<uint32_t>(bin_data.size()));
```

**Cơ chế phát sinh lỗi**:
1. **Ngữ nghĩa C++ Chuẩn (ISO/IEC 14882)**: Khi `bin_len == 0` hoặc khi luồng byte của `fdp` cạn kiệt, `bin_data.empty()` trả về `true`. Theo đặc tả chuẩn của C++, việc gọi `bin_data.data()` trên một vector rỗng được phép trả về `nullptr`.
2. **Quy chuẩn Con trỏ C (ISO/IEC 9899 C99/C11 §7.24.1)**: Hàm `mpack_write_bin` bên trong thư viện gọi hàm sao chép bộ nhớ `memcpy(writer->position, p, count)`. Trong thư viện chuẩn C của GNU (`glibc`), tham số nguồn và đích của hàm `memcpy` được trang trí bằng thuộc tính `__attribute__((nonnull(1, 2)))`. Theo chuẩn C, việc truyền con trỏ `NULL` vào `memcpy` — **ngay cả khi số byte sao chép $n = 0$** — là một hành vi Không Xác Định (Undefined Behavior).
3. **Kích hoạt Bẫy Sanitizer**: Dưới cờ biên dịch `-fsanitize=undefined` (cụ thể là trình kiểm tra `invalid-null-argument`), runtime UBSan chặn đứng lệnh gọi `memcpy(..., NULL, 0)` và kích hoạt lệnh abort:
   `runtime error: null pointer passed as argument 2, which is declared to never be null`.
4. **Đầu độc Thuật toán Biến dị (Corpus Poisoning)**: Thuật toán di truyền của AFL++ nhận thấy rằng chỉ cần đưa vào đầu vào rỗng (0-byte) hoặc đầu vào làm cạn kiệt dữ liệu là có thể lập tức kích hoạt crash. AFL++ dồn toàn bộ năng lượng biến dị vào hướng này, sinh ra hàng ngàn hạt giống rác liên tục kích hoạt cùng một lỗi của harness.

Các crash khác trong chiến dịch cũng có căn nguyên vi phạm tiền điều kiện tương tự:
- **`crash_001`** (`fuzzer_004`): Harness gọi `mpack_tree_set_limits(&pool_tree, max_bytes, max_nodes)` với giá trị sinh ra từ `fdp.ConsumeIntegralInRange<size_t>(0, 1024)`. Thư viện yêu cầu tiền điều kiện nghiêm ngặt `max_bytes > 0` và `max_nodes > 0` (`mpack-node.c:1095-1096`), dẫn tới kích hoạt assertion `MPACK_UNREACHABLE`.
- **`crash_002`** (`fuzzer_011`): Harness truyền `cstr_buf_size = 0` vào `mpack_read_utf8_cstr`, vi phạm tiền điều kiện vùng đệm phải $\ge 1$ để chứa ký tự kết thúc chuỗi `\0`.
- **`crash_003`** (`fuzzer_012`): Harness truyền `ext_buf.data()` của một `std::vector<char> ext_buf(0)` rỗng vào `mpack_read_bytes`, vi phạm `mpack_assert(p != NULL)`.

#### 2.3.2 Nguồn gốc trong Prompt Few-Shot
Nguyên nhân sâu xa khiến LLM liên tục mắc phải lỗi này nằm ở chính các ví dụ mẫu (few-shot examples) trong `src/agents/harness-generator/prompt.py`:
- Tại dòng 169–176:
  ```cpp
  size_t buffer_size = fdp.ConsumeIntegralInRange<size_t>(1, 1024);
  std::vector<uint8_t> buffer = fdp.ConsumeBytes<uint8_t>(buffer_size);
  api_create_file(filename.c_str(), buffer.data(), buffer.size());
  ```
- Tại dòng 213–218:
  ```cpp
  std::vector<uint8_t> payload = fdp.ConsumeRemainingBytes<uint8_t>();
  api_send(payload.data(), payload.size());
  ```
Các đoạn code mẫu chính thức hướng dẫn LLM truyền trực tiếp `.data()` và `.size()` mà không hề có bất kỳ câu lệnh kiểm tra điều kiện rỗng (`if (buffer.empty()) return 0;`) hoặc bọc con trỏ an toàn nào. LLM học vẹt mẫu code này và nhân rộng lỗi ra toàn bộ các harness.

#### 2.3.3 Lỗ hổng Trí mạng của Triage Gatekeeper: Phân tích Frame Đơn Lẻ
Tại sao các crash giả này không bị chặn lại mà lại làm tiêu tốn hàng chục giờ triage?
Trong `src/tools/fuzz/bin/run_fuzzer` (dòng 469–520):
```python
469: def extract_crashing_frame_and_token(output: str, src_dir: str, harness_path: str) -> dict:
...
490:     for m in STACK_FRAME_RE.finditer(output):
491:         idx, func, file_path, line, col = m.groups()
492:         if not any(rw in func or rw in file_path for rw in RUNTIME_WRAPPER_PATTERNS):
493:             cand = (func.strip(), file_path, line, dedup_token or ...)
494:             break
...
508:     is_harness = ("harness" in norm_file or "poc.cpp" in norm_file or "LLVMFuzzerTestOneInput" in func ...)
509:     is_library = norm_file.startswith(norm_src) or "/src/" in norm_file
```

**Cơ chế Thất bại của Gatekeeper**:
- Khi xảy ra lỗi `memcpy(dest, NULL, 0)` trong `mpack-writer.c:536`, Call Stack Frame #0 nằm ở hàm nội bộ của thư viện (`mpack_write_native` thuộc `mpack-writer.c`).
- Bộ phân tích stack frame duyệt từ trên xuống dưới và lấy ngay Frame đầu tiên không thuộc wrapper (`Frame #0`).
- Vì `norm_file` trỏ tới `mpack-writer.c` (nằm trong thư mục mã nguồn thư viện `norm_src`), thuật toán kết luận:
  * `is_harness = False`
  * `is_library = True`
  * $\to$ Gán nhãn `verdict = LIBRARY_BUG`!
- **Hậu quả**: Thay vì loại bỏ ngay tại chỗ với chi phí 0 token, hệ thống đánh giá đây là lỗ hổng an ninh nghiêm trọng của thư viện. `ManagerAgent` dừng fuzzer, điều phối `CrashAnalyzerAgent` khởi chạy phiên GDB tương tác kéo dài 30–60 phút cho mỗi sự cố để trích xuất biến, chạy PoC reduction. Cuối cùng, sau khi tiêu tốn hàng triệu token và thời gian tính toán quý báu, `CrashAnalyzerAgent` mới kết luận đó là `harness-bug`. Quy trình này lặp lại liên tục, làm tê liệt toàn bộ chiến dịch fuzzing.

---

### 2.4 Tính Trực Giao giữa CoverageAnalyzerAgent và HarnessGeneratorAgent & Phát hiện Lỗi Logic Đảo Ngược

#### 2.4.1 Xâm phạm Ranh giới Trách nhiệm (Role Entanglement)
Nguyên lý trực giao kiến trúc (Architectural Orthogonality) yêu cầu mỗi tác tử phải có một không gian trách nhiệm phân định rõ ràng:
- `CoverageAnalyzerAgent` có nhiệm vụ trả lời câu hỏi: **"Đang thiếu độ phủ ở đâu?" (WHAT)** — Xác định các hàm chưa phủ, các nhánh blocker, và các điều kiện trạng thái cần đạt tới.
- `HarnessGeneratorAgent` có nhiệm vụ trả lời câu hỏi: **"Xây dựng mã như thế nào?" (HOW)** — Phân giải kiểu dữ liệu C++, quản lý vòng đời con trỏ, gọi API theo đúng cú pháp hợp lệ.

Trong thực tế codebase:
- `CoverageAnalyzerAgent` trong `src/agents/cov-analyzer/prompt.py` thường xuyên vượt quyền, cố gắng tự viết các đoạn mã C++ chi tiết (pseudo-C++) trong báo cáo hướng dẫn markdown (`<recommendation>`).
- Do không có công cụ biên dịch (`build_harness`) và không thể kiểm tra AST, các đoạn mã C++ do `CoverageAnalyzerAgent` đề xuất chứa đầy lỗi cú pháp, ép kiểu sai, và gọi các hàm không tồn tại.
- Khi `HarnessGeneratorAgent` nhận được hướng dẫn này, nó coi đó là "chân lý" và cố gắng sao chép nguyên văn vào harness mới. Quá trình biên dịch thất bại, đẩy `HarnessGeneratorAgent` vào vòng lặp tự sửa lỗi vô tận để khắc phục những đoạn mã lẽ ra không bao giờ nên được sinh ra.

#### 2.4.2 Phát hiện Chấn động: Lỗi Đảo ngược Boolean Triệt tiêu Hoàn toàn Vòng lặp Tiến hóa
Trong quá trình kiểm toán mã nguồn tệp `src/agents/cov-analyzer/agent.py`, nhóm nghiên cứu đã phát hiện một **lỗi đảo ngược logic boolean mang tính thảm họa**. Lỗi này giải thích một bí ẩn lớn trong chiến dịch thực nghiệm: *Tại sao sau 17 giờ chạy liên tục, thư mục `$OUTPUT/mpack/coverage_guidance/` hoàn toàn trống rỗng không có lấy một tệp hướng dẫn nào?*

Xem xét mã nguồn `src/agents/cov-analyzer/agent.py` tại các dòng 46–68:

```python
46: def no_fuzzer_in_plateau(self) -> bool:
47:     fuzz_profile = get_fuzzer_profile()
48:     for _, fuzz_info in fuzz_profile.fuzzers.items():
49:         if fuzz_info.state == FuzzerExecutionState.PLATEAU:
50:             return True
51:     return False
```

Và cách hàm này được sử dụng tại dòng 63–68:
```python
63:     if self.no_fuzzer_in_plateau():
64:         self.can_return_early = True
65:         fuzzer_info = self.get_fuzzer_info()
66:         reminder = f"Here is the fuzzer stats:\n{fuzzer_info}\nBut you did not find any fuzzer in plateau state and is able to extract code coverage. Please directly exit and report this issue to let HarnessAgent or FuzzerAgent to continue."
67:         self.history_processor.extend_user_msg(content=reminder)
68:         return
```

Cùng điều kiện kiểm tra hoàn tất tác vụ tại dòng 73–76:
```python
73: def is_agent_task_completed(self) -> bool:
74:     if self.can_return_early:
75:         return True
```

**Phân tích Cơ chế Lỗi**:
1. Tên hàm được đặt là `no_fuzzer_in_plateau` (nghĩa là: *Không có fuzzer nào ở trạng thái plateau*).
2. Tuy nhiên, tại dòng 49: `if fuzz_info.state == FuzzerExecutionState.PLATEAU: return True`!
3. Hàm trả về `True` khi **CÓ** ít nhất một fuzzer đang ở trạng thái `PLATEAU`.
4. Khi một fuzzer đạt ngưỡng bão hòa và `ManagerAgent` điều phối `CoverageAnalyzerAgent` vào cuộc để phân tích độ phủ, câu lệnh điều kiện `if self.no_fuzzer_in_plateau():` tại dòng 63 được đánh giá. Vì có fuzzer ở trạng thái plateau, biểu thức này trả về `True`!
5. Lập tức, cờ `can_return_early` được gán thành `True`, hệ thống chèn một thông báo nhắc nhở sai lệch: *"Bạn không tìm thấy fuzzer nào ở trạng thái plateau... Hãy thoát ngay lập tức!"*.
6. Tác tử `CoverageAnalyzerAgent` lập tức dừng hoạt động và trả về thông báo rỗng:
   `"[*] No fuzzer in plateau state and is able to extract code coverage."`
7. **Hậu quả Toàn cục**: Trong suốt toàn bộ chiến dịch 17 giờ, `CoverageAnalyzerAgent` bị buộc phải thoát sớm 100% số lần được triệu hồi. Không có một dòng chỉ dẫn độ phủ nào được sinh ra. Hệ thống Agentic Fuzzing hoàn toàn bị chặt đứt "mắt thần" độ phủ, biến thành một hệ thống sinh harness ngẫu nhiên mù quáng, làm sụp đổ hoàn toàn lời hứa về một hệ thống fuzzing tiến hóa tự trị có hướng dẫn.

---

## 3. KHẢO SÁT TÀI LIỆU HỌC THUẬT VÀ MA TRẬN ĐỐI CHIẾU CÓ HỆ THỐNG

### 3.1 Lược sử 5 Thế hệ Công nghệ LLM / Harness Fuzzing (2020–2026)

Lịch sử phát triển của các kỹ thuật tổng hợp fuzz driver tự động và kiểm thử độ phủ thư viện trong 6 năm qua trải qua 5 thế hệ (Epochs) rõ nét:

```
+---------------------------------------------------------------------------------------------------+
|  Thế hệ 1: Phân tích Tĩnh Thuần túy & Đồ thị Phụ thuộc IR (2020 - 2022)                           |
|  - Đại diện: FuzzGen (USENIX Security '20), Hopper (IEEE S&P '23)                                 |
|  - Đặc trưng: Phân tích LLVM IR toàn chương trình, xây dựng Abstract API Dependency Graph (AADG).|
|  - Hạn chế: Bất lực trước C++ templates, đa hình, macro tiền xử lý phức tạp, hàm callback opaque. |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  Thế hệ 2: Tổng hợp LLM Một lượt & Chưng cất Ngữ pháp (2023 - Đầu 2024)                           |
|  - Đại diện: TitanFuzz (ISSTA '23), Fuzz4All (ICSE '24)                                           |
|  - Đặc trưng: Zero-shot/Few-shot prompting, sinh mã kiểm thử ngôn ngữ và thư viện Deep Learning.  |
|  - Hạn chế: Vòng hở (open-loop), không có phản hồi runtime/coverage, tỷ lệ lỗi cú pháp cao.       |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  Thế hệ 3: Đột biến Prompt Lặp & Phá vỡ Bão hòa Giao thức (2024)                                  |
|  - Đại diện: PromptFuzz (ACM CCS '24), ChatAFL (NDSS '24)                                         |
|  - Đặc trưng: Vòng lặp đột biến prompt dựa trên độ phủ nhánh; LLM can thiệp khi fuzzer bão hòa.  |
|  - Hạn chế: Kiến trúc prompt nguyên khối (monolithic context), nhanh tràn cửa sổ ngữ cảnh.        |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  Thế hệ 4: Pipeline Tích hợp Liên tục Quy mô Công nghiệp (2024 - 2025)                            |
|  - Đại diện: Google OSS-Fuzz-Gen                                                                  |
|  - Đặc trưng: Khai thác khoảng trống tĩnh qua Fuzz Introspector, tự sửa lỗi biên dịch, dry-run.   |
|  - Hạn chế: Mục tiêu tĩnh (chỉ nhắm hàm chưa test); không có cơ chế tiến hóa thích ứng runtime.   |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|  Thế hệ 5: Hệ thống Đa Tác tử Tiến hóa Tự trị (2025 - 2026)                                       |
|  - Đại diện: FuzzAgent (Lyu et al., 2026), Agentic Fuzzing                                        |
|  - Đặc trưng: Phân rã đa vai trò chuyên biệt, telemetry độ phủ phân cấp đa tầng, triage GDB tự trị|
|  - Thách thức mới: Semantic Precondition Inversion, Macro Hijacking, Saturation Shadowing.        |
+---------------------------------------------------------------------------------------------------+
```

- **Thế hệ 1 (FuzzGen, Hopper)**: Dựa trên phân tích tĩnh hình thức để trích xuất thứ tự gọi API và kiểm soát kiểu dữ liệu. Phương pháp này hoàn toàn miễn nhiễm với lỗi crash do harness misuse, nhưng lại thất bại thảm hại khi đối mặt với các thư viện C++ hiện đại sử dụng nhiều con trỏ hàm, template, hoặc thiếu các chương trình tiêu thụ (consumer programs) mẫu để phân tích tĩnh.
- **Thế hệ 2 (TitanFuzz, Fuzz4All)**: Đánh dấu sự chuyển dịch sang mô hình ngôn ngữ lớn. TitanFuzz khai thác Codex để sinh mã kiểm thử PyTorch/TensorFlow; Fuzz4All sử dụng autoprompting cho các trình biên dịch ngôn ngữ. Tuy nhiên, chúng hoạt động hoàn toàn ở dạng "bắn-rồi-quên" (open-loop), không thể tối ưu hóa độ phủ sâu vào các nhánh logic nội bộ của thư viện.
- **Thế hệ 3 (PromptFuzz, ChatAFL)**: Lần đầu tiên tích hợp phản hồi độ phủ động vào vòng lặp LLM. PromptFuzz theo dõi số nhánh thực thi và đột biến prompt để mở rộng độ phủ; ChatAFL kích hoạt LLM khi AFLNet bão hòa để sinh các gói tin chuyển trạng thái giao thức mạng mới. Điểm nghẽn lớn nhất là việc nhồi nhét tất cả các tác vụ (biên dịch, phân tích độ phủ, đánh giá crash) vào một chuỗi hội thoại duy nhất gây suy thoái ngữ cảnh (context bloat).
- **Thế hệ 4 (Google OSS-Fuzz-Gen)**: Chuẩn hóa quy trình công nghiệp với Fuzz Introspector để tìm các hàm công khai chưa có harness, kết hợp vòng lặp sửa lỗi Clang (3–5 vòng) và chạy thử nghiệm (dry-run) 30 giây. Hạn chế cốt tử của OSS-Fuzz-Gen là việc kiểm thử dry-run quá ngắn chỉ loại bỏ được các crash tức thì, hoàn toàn bất lực trước các vi phạm tiền điều kiện tinh vi chỉ bộc lộ sau hàng ngàn đột biến của AFL++.
- **Thế hệ 5 (FuzzAgent, Agentic Fuzzing)**: Đỉnh cao của sự tiến hóa với việc phân rã hệ thống thành các tác tử chuyên biệt, giải quyết triệt để bài toán tràn ngữ cảnh và tự động hóa toàn bộ vòng đời kiểm thử. Tuy nhiên, như chiến dịch mpack 17h đã chứng minh, kiến trúc này bắt đầu va chạm vào các giới hạn lý thuyết mới về đồng bộ hóa cụm fuzzer và ngữ nghĩa hợp đồng API.

---

### 3.2 Bảng Đối chiếu Ma trận So sánh 4 Chiều Toàn diện

Bảng ma trận dưới đây thực hiện phép đối chiếu có hệ thống giữa hệ thống mã nguồn hiện tại (**Agentic Fuzzing**) với 4 công trình mang tính cột mốc đại diện cho các trường phái khác nhau: **OSS-Fuzz-Gen** (Công nghiệp/Tĩnh), **PromptFuzz** (Tiến hóa Nguyên khối), **ChatAFL** (Giao thức/Neuro-Symbolic), và **FuzzAgent** (Đa tác tử nguyên bản):

| Chiều Đánh giá / Tiêu chí Kỹ thuật | **OSS-Fuzz-Gen** (Google, 2024-2025) | **PromptFuzz** (Lyu et al., CCS 2024) | **ChatAFL** (Meng et al., NDSS 2024) | **FuzzAgent** (Lyu et al., 2026) | **Agentic Fuzzing** (Codebase Hiện tại) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. KIẾN TRÚC AGENT & ĐIỀU PHỐI** | | | | | |
| *Mô hình Phân rã Vai trò* | Nguyên khối dạng đường ống cố định (Pipeline); 1 LLM sửa lỗi biên dịch | Tác tử hội thoại đơn lẻ kết hợp thuật toán tiến hóa prompt | Co-pilot lai ghép (AFLNet engine kết hợp LLM truy vấn khi bế tắc) | Đa tác tử phân rã hoàn chỉnh (7 tác tử chuyên trách) | Đa tác tử phân rã hoàn chỉnh (Manager + 7 Subagents) |
| *Không gian Trách nhiệm* | Cố định: Phân tích hàm $\to$ Prompt $\to$ Biên dịch $\to$ Dry-run | Hợp nhất: Sinh mã, sửa lỗi, và đánh giá độ phủ chung 1 prompt | Chuyên biệt hóa cho giao thức mạng (State model & Seed synthesis) | Tách biệt nghiêm ngặt (Build, Harness, Fuzz, Cov, Crash) | Tách biệt theo vai trò; tuy nhiên bị rò rỉ ranh giới giữa Cov & Harness |
| *Giao thức Trao đổi Dữ liệu* | Đóng kín nội bộ pipeline Python | Chuỗi văn bản hội thoại tích lũy lịch sử | Trao đổi thông điệp JSON/Text khi fuzzer báo bão hòa | Giao thức ACI; ánh xạ trạng thái đĩa cứng (`fuzzer_stat.json`) | Giao thức ACI; văn bản tự do Markdown (`<recommendation>`); tệp JSON |
| *Khả năng Mở rộng Ngữ cảnh* | Reset phiên làm việc sau mỗi hàm mục tiêu; không lưu ngữ cảnh | Cửa sổ trượt (Sliding window); dễ mất mát thông tin lịch sử | Ngắn hạn (Ephemeral); chỉ truy vấn các trạng thái giao thức cụ thể | Phân vùng ngữ cảnh theo vai trò; bộ nhớ dài hạn/ngắn hạn | Tách biệt cửa sổ prompt theo từng tác tử; lưu trữ vết thực thi |
| **2. PHẢN HỒI ĐỘ PHỦ (COVERAGE)** | | | | | |
| *Cơ chế Đo lường Telemetry* | Đồ thị tĩnh từ AST qua Fuzz Introspector (hàm chưa phủ) | Bitmap động gcov/llvm-cov (đếm số nhánh thực thi) | Bitmap cạnh AFLNet kết hợp phản hồi mã trạng thái giao thức | Đo lường phân cấp 5 tầng: Tổng quan $\to$ Module $\to$ File $\to$ API $\to$ Blocker | Công cụ phân cấp (`cov_overview`, `cov_api`, `cov_blockers`, `sancov`) |
| *Tính Động của Vòng lặp* | Tĩnh (Open-loop trong lúc fuzz); mục tiêu chọn trước khi chạy | Động (Closed-loop): Độ phủ nhánh cập nhật trọng số prompt | Kích hoạt theo sự kiện: Chỉ gọi LLM khi bitmap bão hòa | Tiến hóa 2 pha liên tục: Pha 1 (Surface API), Pha 2 (Blockers) | Tiến hóa 2 pha; **tuy nhiên tê liệt do bug logic đảo ngược boolean** |
| *Mô hình Đóng gói Phụ thuộc* | Heuristic trích xuất từ các tệp mẫu trong repo | LLM tự suy luận ngầm qua các ví dụ few-shot | Mô hình máy trạng thái giao thức định nghĩa sẵn từ RFC | Khai phá phụ thuộc 4 chiều (Khởi tạo, Dữ liệu, Thời gian, Vòng đời) | Hợp đồng 3 giai đoạn: Khởi tạo $\to$ Thao tác API $\to$ Thu dọn tài nguyên |
| **3. KIỂM SOÁT FALSE POSITIVE (FP)** | | | | | |
| *Bộ lọc Cấp Biên dịch* | Clang AST parsing + Sửa lỗi cú pháp/liên kết 3-5 vòng | Kiểm tra mã lỗi trình biên dịch; loại bỏ harness lỗi cú pháp | Kiểm tra ngữ pháp gói tin mạng trước khi gửi qua socket | Vòng lặp Clang repair + Gắn cờ Sanitizers (`ASAN`, `UBSAN`) | Công cụ `build_harness` tích hợp ASAN/UBSAN; **thiếu Macro filter** |
| *Kiểm chứng Runtime Sơ bộ* | Chạy thử (Dry-run) 10–30s với hạt giống giả định | Bộ lọc thực thi loại bỏ driver crash ngay với seed rỗng | Lọc tín hiệu ngoại lệ của tiến trình server daemon | Zero-FP Triage Gatekeeper: Kiểm tra sơ bộ Call Stack | `pre_triage_and_dedup_crashes`; **lỗ hổng kiểm tra độc quyền Frame #0** |
| *Điều tra Khám nghiệm Sâu* | Không có (Giao toàn bộ crash cho lập trình viên con người) | Thủ công (Tỷ lệ crash do lỗi harness cực kỳ cao) | Thủ công (Phân tích log máy chủ để loại bỏ packet rác) | Tác tử CrashAnalyzer tự trị: GDB session, biến nội bộ, PoC reduction | `CrashAnalyzerAgent` tự động hóa GDB scripting, thu nhỏ PoC, gán nhãn |
| *Xử lý Nhiễu Sanitizer* | Báo cáo toàn bộ mọi abort của ASAN/UBSan không chọn lọc | Báo cáo toàn bộ; coi mọi abort của sanitizer là lỗi | Không áp dụng (chỉ tập trung vào SIGSEGV/SIGABRT) | Phân biệt lỗi do thư viện với lỗi do hành vi gọi sai của harness | Có bộ quy tắc Regex lọc nhiễu UBSan (`libsais` shift vs `mpack` null) |
| **4. HIỆU NĂNG THỰC TẾ & CHẤT LƯỢNG** | | | | | |
| *Tỷ lệ Biên dịch Thành công* | 70% – 85% (sau 3–5 vòng tự sửa) | 75% – 88% trên các thư viện C | > 95% (do cú pháp giao thức chuẩn hóa) | 88% – 94% trên 20 thư viện C/C++ chuẩn | 89% – 95% trên các benchmark thử nghiệm |
| *Tính Hợp lệ Hợp đồng Ngữ nghĩa*| Rất thấp (< 40% sống sót sau 1h fuzzing API trạng thái) | Trung bình (50% – 60% không bị crash do vi phạm tiền điều kiện)| Cao đối với giao thức mạng; Không áp dụng cho C memory APIs | Cao trên API bề mặt; suy giảm mạnh trên Stream/Tree API phức tạp | Rất thấp trên API luồng trạng thái (**0% crash thật trên `mpack`**) |
| *Sản lượng Phát hiện Lỗ hổng*| Tìm thấy hàng trăm lỗi trên OSS-Fuzz | 33 zero-days trên 14 thư viện (30 đã được sửa) | Hàng loạt CVEs mới trên Live555, ProFTPD, Kamailio | 102 bugs trên 20 thư viện (78 đã được xác nhận và vá) | Tái hiện các lỗi của FuzzAgent; nhạy cảm với lỗi thuật toán (`bzip3`) |
| *Chi phí Token & Tài nguyên* | ~$2 – $5 cho mỗi harness ứng viên | ~$10 – $20 cho mỗi chiến dịch (Do prompt bloat) | Tiêu thụ token rất thấp (chỉ gọi khi bão hòa) | Tối ưu hóa theo vai trò; ~$50 – $150 cho chiến dịch 24h quy mô lớn | Tiêu tốn 2M – 8M tokens cho chiến dịch 24h; lãng phí token vào triage |

---

## 4. ĐỊNH VỊ CÁC RESEARCH GAP THỰC THỤ VÀ PHẢN BIỆN HỌC THUẬT

Dựa trên bằng chứng kiểm toán mã nguồn và ma trận đối chiếu học thuật, chúng tôi khẳng định rằng các thất bại quan sát được không đơn thuần là lỗi lập trình (bugs) cục bộ, mà là biểu hiện của **những khoảng trống nghiên cứu nền tảng (Fundamental Research Gaps)** chưa từng được giải quyết thỏa đáng trong các tài liệu khoa học hiện nay.

```
========================================================================================================
                                HỆ THỐNG PHÂN VỊ RESEARCH GAPS CỐT LÕI
========================================================================================================

+------------------------------------------------------------------------------------------------------+
|  RESEARCH GAP 1: "The Syntactic Validity Illusion" & Semantic Contract Inversion                     |
|  "Tại sao tỷ lệ biên dịch thành công >90% lại dẫn tới 0% lỗi thư viện thật trên API trạng thái?"    |
|                                                                                                      |
|  - Bản chất: Sự bất tương thích giữa Tính đúng đắn Cú pháp L_syn và Tính hợp lệ Hợp đồng L_sem.       |
|  - Hệ quả: Vòng lặp sửa lỗi compiler vô tình tối ưu hóa cú pháp bằng cách phá hủy ngữ nghĩa an toàn;  |
|            AFL++ bị đầu độc bởi các crash giả dạng Caller-Fault; tê liệt hàng đợi triage.             |
|  - Lời giải đột phá: Tổng hợp Hợp đồng Thần kinh - Ký hiệu (Neuro-Symbolic Contract Synthesis).      |
+------------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+------------------------------------------------------------------------------------------------------+
|  RESEARCH GAP 2: Fuzzing State Desynchronization & Suy giảm Entropy trong Chiến dịch Dài hạn         |
|  "Tại sao các hệ thống Agentic Fuzzing luôn suy thoái sau 12-24h và rơi vào mù bão hòa?"            |
|                                                                                                      |
|  - Bản chất 1: Mất đồng bộ Cụm Đa nhân (Master bão hòa sớm tiêu diệt các Slaves đang tìm ra crash).   |
|  - Bản chất 2: Context Entropy Explosion (Telemetry blocker thô vượt quá ngân sách ngữ cảnh của LLM).|
|  - Lời giải đột phá: Cơ chế Đồng thuận Telemetry Cụm & Chưng cất Ngữ nghĩa Blocker Phân sai.         |
+------------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+------------------------------------------------------------------------------------------------------+
|  RESEARCH GAP BỔ TRỢ: Preprocessor-Induced Environment Mutation & Suy thoái Độ tin cậy ABI           |
|  "Sự bất lực của LLM trước ranh giới tiền xử lý dẫn tới ô nhiễm nhị phân (Macro Hijacking)"         |
|                                                                                                      |
|  - Bản chất: LLM coi macro tiền xử lý là công cụ lách lỗi biên dịch mà không nhận thức được ABI.     |
|  - Lời giải đột phá: Rào chắn AST LibTooling tiền biên dịch và Cô lập môi trường thực thi hermetic.  |
+------------------------------------------------------------------------------------------------------+
========================================================================================================
```

---

### 4.1 Research Gap 1: "The Syntactic Validity Illusion" & Sự Đảo Nghịch Hợp Đồng Ngữ Nghĩa (Semantic Contract Inversion)

#### 4.1.1 Mô hình Hóa Toán học của Khoảng Trống Nghiên cứu
Giả sử thư viện mục tiêu $\mathcal{L}$ cung cấp tập hợp các hàm API công khai $\mathcal{A} = \{a_1, a_2, \dots, a_n\}$.
Mỗi API $a_i$ có một hợp đồng tiền điều kiện ngữ nghĩa hình thức $\mathcal{P}(a_i)$ xác định trên không gian tham số đầu vào $\mathbf{x} = (x_1, \dots, x_k)$ và trạng thái nội bộ của thư viện $\sigma \in \Sigma$:
$$\mathcal{P}(a_i): \operatorname{Dom}(x_1) \times \dots \times \operatorname{Dom}(x_k) \times \Sigma \to \{0, 1\}$$
Một harness $\mathcal{H}$ được sinh ra bởi mô hình LLM $\mathcal{M}$ là một chuỗi tuần tự các lời gọi API:
$$\mathcal{H} = \langle a_{\pi(1)}(\mathbf{x}_1), a_{\pi(2)}(\mathbf{x}_2), \dots, a_{\pi(m)}(\mathbf{x}_m) \rangle$$
được thúc đẩy bởi nguồn dữ liệu biến dị nhị phân $D \in \{0, 1\}^*$ thông qua hàm phân rã $\phi: D \to (\mathbf{x}_1, \dots, \mathbf{x}_m)$.

Toàn bộ các nghiên cứu SOTA hiện nay (OSS-Fuzz-Gen, PromptFuzz, FuzzAgent) đều định nghĩa tính hợp lệ của harness thông qua hai không gian ngôn ngữ lỏng lẻo:
1. **Tính Hợp lệ Cú pháp ($\mathcal{L}_{syn}$)**:
   $$\mathcal{H} \in \mathcal{L}_{syn} \iff \operatorname{Clang}(\mathcal{H}, \text{flags}) = 0 \quad (\text{Biên dịch và Liên kết thành công})$$
2. **Tính Khả thi Thực thi Ngắn hạn ($\mathcal{L}_{exec}^{\epsilon}$)**:
   $$\mathcal{H} \in \mathcal{L}_{exec}^{\epsilon} \iff \forall d \in D_{seed}, \quad \operatorname{Exec}(\mathcal{H}, d, \Delta t < 30\text{s}) \neq \text{CRASH}$$

**Bản chất của Research Gap**: Tồn tại một khoảng trống mênh mông giữa tính hợp lệ cú pháp $\mathcal{L}_{syn}$ và **Tính Hợp lệ Hợp đồng Ngữ nghĩa Toàn phần ($\mathcal{L}_{sem}$)**:
$$\mathcal{H} \in \mathcal{L}_{sem} \iff \forall d \in D^*, \quad \bigwedge_{j=1}^m \mathcal{P}\big(a_{\pi(j)}, \mathbf{x}_j(d), \sigma_j(d)\big) = 1$$

Khi LLM $\mathcal{M}$ tham gia vào vòng lặp phản hồi của trình biên dịch (Compiler Feedback Loop), nó thực hiện hàm tối ưu hóa:
$$\max_{\mathcal{H}} \mathbb{P}(\mathcal{H} \in \mathcal{L}_{syn} \mid \text{Compiler Diagnostics})$$
Do trình biên dịch C++ chỉ kiểm tra ràng buộc tĩnh về kiểu (type checking) chứ không kiểm tra được các bất biến tiền điều kiện runtime (ví dụ: kích thước mảng $>0$, con trỏ khác null khi truyền vào hàm C), LLM sẵn sàng thực hiện các phép biến đổi cú pháp phá vỡ tiền điều kiện ngữ nghĩa để làm câm lặng trình biên dịch. Kết quả là:
$$\mathcal{H} \in \mathcal{L}_{syn} \setminus \mathcal{L}_{sem}$$

#### 4.1.2 Cơ chế Đảo Nghịch Hợp Đồng Ngữ Nghĩa (Semantic Contract Inversion)
Hiện tượng này nguy hiểm ở chỗ: **Càng nhiều vòng lặp tự sửa lỗi biên dịch, xác suất vi phạm hợp đồng ngữ nghĩa càng tăng cao**.
- Khi Clang báo lỗi không khớp kiểu con trỏ, LLM có xu hướng sử dụng ép kiểu thô bạo (`reinterpret_cast<const char*>(vec.data())`).
- Khi Clang báo lỗi biến chưa được khởi tạo, LLM gán giá trị mặc định bằng 0 (`size_t len = 0;`).
- Nhưng đối với các thư viện xử lý dòng dữ liệu như `mpack`, giá trị 0 và con trỏ rỗng lại là các giá trị cấm ngặt nghèo trong các assertion runtime.

Khi đưa harness vào AFL++, bộ biến dị greybox không quan tâm đến việc tìm lỗ hổng của thư viện nữa, mà năng lượng tìm kiếm bị hút vào **điểm kỳ dị ngữ nghĩa (Semantic Singularity)**: các đầu vào kích hoạt vi phạm tiền điều kiện ở ngay tầng harness (Caller-Fault). Hệ thống fuzzer bị tê liệt hoàn toàn trong việc mở rộng độ phủ sâu.

---

### 4.2 Research Gap 2: Fuzzing State Desynchronization & Suy Giảm Entropy Thông Tin trong Chiến Dịch Dài Hạn (Long-Campaign Feedback Loss)

#### 4.2.1 Phân Mảnh Trạng Thái Cụm Fuzzer Đa Nhân (Cluster Desynchronization)
Trong môi trường thực tế, kiểm thử mờ quy mô công nghiệp bắt buộc phải khai thác sức mạnh đa nhân (1 Master + $N-1$ Slaves). 
Mô hình hóa động học của hệ thống fuzzing đa nhân theo thời gian $t \in [0, T]$:
Tiến trình Master phát triển không gian trạng thái theo đồ thị $S_M(t)$, trong khi các Slaves phát triển độc lập theo $S_{S_1}(t), \dots, S_{S_k}(t)$.

Các công trình nghiên cứu hiện nay (kể cả FuzzAgent và ChatAFL) khi thiết kế bộ điều khiển LLM đều giả định một **mô hình quan sát đơn vị (Scalar Telemetry Observation)**:
$$\operatorname{SatCheck}(t) = f(S_M(t))$$
Hệ thống ngầm giả định rằng tiến trình Master đại diện cho toàn bộ trạng thái tiến hóa của cụm. 
**Thực tế phản biện**:
- Tiến trình Master chạy các chế độ đột biến tất định tuần tự (deterministic bit-flips, byte-flips, arithmetics) nên đạt tới điểm bão hòa độ phủ $\Delta C_M / \Delta t \to 0$ rất sớm (thường chỉ sau 10–20 phút).
- Ngược lại, các tiến trình Slaves chạy các bộ lập lịch ngẫu nhiên năng lượng cao (random havoc, MOPT, chunk insertion) vẫn đang trong pha bùng nổ khám phá các nhánh rẽ mới và phát hiện crash:
  $$\frac{\Delta C_{S_i}(t)}{\Delta t} \gg 0 \quad \text{và} \quad \text{CrashCount}(S_i) > 0$$
- Việc thuật toán giám sát ra quyết định tiêu diệt toàn bộ cụm khi Master bão hòa tạo ra sự **đứt gãy đồng bộ nghiêm trọng (State Desynchronization)**: vứt bỏ thành quả của Slaves, tạo ra kết luận sai lầm về trạng thái tới hạn của thư viện.

#### 4.2.2 Sự Bùng Nổ Entropy Ngữ Cảnh và Bão Hòa LLM (Context Entropy Explosion)
Trong giai đoạn đầu của chiến dịch fuzzing ($t \in [0, 4h]$ - Phase 1), độ phủ cần mở rộng nằm ở các API công khai chưa được gọi. Thông tin phản hồi độ phủ $G_{early}$ có mức entropy rất thấp:
$$H(G_{early}) = -\sum p_i \log_2 p_i \ll \text{ContextBudget}(\mathcal{M})$$
LLM dễ dàng tiếp thu danh sách các hàm chưa kiểm thử và sinh mã harness chính xác.

Tuy nhiên, trong giai đoạn sau ($t > 12h$ - Phase 2), toàn bộ các API bề mặt đã được kích hoạt. Độ phủ bị tắc nghẽn tại hàng trăm **nhánh rẽ điều kiện sâu (Deep Branch Blockers)** bên trong lõi thuật toán:
$$\operatorname{Cond}_k: \quad \operatorname{hash}(x) == \text{0x5A3C} \quad \lor \quad \operatorname{state} == \text{STATE_STREAM_EXT}$$
Lúc này, các công cụ phân tích độ phủ (như `cov_blockers`) xuất ra hàng chục ngàn dòng mã nguồn và thông số nhánh rẽ. Lượng thông tin này vượt quá dung lượng xử lý ngữ cảnh hiệu dụng của LLM:
$$H(G_{late}) \gg \text{ContextBudget}(\mathcal{M})$$

**Sự Bão hòa Ngữ cảnh dẫn tới hai hành vi suy thoái của LLM**:
1. **Suy thoái Lặp lại (Stagnation Loop)**: LLM bị quá tải bởi các biểu thức nhánh phức tạp, không thể thực hiện phép nghịch đảo đường dẫn ký hiệu (symbolic path inversion) chỉ bằng cơ chế dự đoán token tiếp theo. Nó bắt đầu sinh ra các harness lặp lại các API cũ với các biến dị tham số vô nghĩa, khiến tốc độ tăng trưởng độ phủ rơi về 0.
2. **Ảo giác Leo thang (Hallucinatory Escalation)**: Khi liên tục bị thúc ép phải vượt qua các nhánh blocker, LLM bắt đầu "sáng tạo" ra các cờ tiền xử lý hoặc ép kiểu con trỏ liều lĩnh, trực tiếp dẫn tới hiện tượng chiếm đoạt Macro (Macro Hijacking).

---

### 4.3 Research Gap Bổ Trợ: Preprocessor-Induced Environment Mutation & Sự Suy Giảm Độ Tin Cậy ABI

Khoảng trống này nằm ở giao điểm giữa kỹ thuật biên dịch hệ thống cấp thấp và khả năng lý luận trừu tượng của mô hình ngôn ngữ lớn:
- LLM được huấn luyện trên hàng tỷ dòng mã nguồn nơi `#define` được sử dụng phổ biến để giải quyết các xung đột định danh. LLM nhìn nhận macro như một "công cụ cú pháp vô hại" để làm hài lòng trình biên dịch.
- Tuy nhiên, trong ngôn ngữ C/C++, macro tiền xử lý là một **công cụ biến đổi môi trường nhị phân (Environment Mutator)**. Nó can thiệp trực tiếp vào giai đoạn trước khi cây AST được hình thành, quyết định việc bao gồm hay loại trừ các trường dữ liệu trong struct.
- Các nghiên cứu hiện tại hoàn toàn bỏ ngỏ bài toán: *Làm thế nào để ràng buộc LLM hoạt động trong một không gian tiền xử lý kín (Hermetic Preprocessor Sandbox), ngăn chặn triệt để sự phân kỳ giữa ABI của harness và ABI của thư viện mục tiêu?*

---

## 5. ĐỀ XUẤT PHƯƠNG PHÁP GIẢI QUYẾT KỸ THUẬT TOÀN DIỆN

Để khắc phục triệt để 4 lỗi cốt lõi trong codebase và lấp đầy các khoảng trống nghiên cứu đã định vị, chúng tôi đề xuất một bộ giải pháp kỹ thuật toàn diện, có tính khả thi công nghiệp cao và sẵn sàng triển khai.

---

### 5.1 Kiến trúc `MultiInstanceAFLManager` và Cơ chế Rào chắn Thu hoạch Crash Độc lập (Guaranteed Crash Harvest Barrier)

Nhằm giải quyết dứt điểm **Lỗi Saturation Shadowing Bug trong `run_fuzzer`**, chúng tôi tái cấu trúc toàn bộ mô-đun giám sát thực thi, thay thế cơ chế polling đơn lẻ bằng lớp quản lý đa tiến trình hướng đồng thuận:

#### 5.1.1 Nguyên lý Thiết kế Kiến trúc
1. **Telemetry Hợp nhất (Unified Cluster Telemetry)**: Quét toàn bộ các thư mục con trong `output/` (bao gồm `default/` và tất cả `slave0/` đến `slaveN/`). Tổng hợp số lượt thực thi (`total_execs`), tính toán tốc độ thực thi tổng hợp (`effective_exec_per_sec`), và hợp nhất bitmap độ phủ bằng phép toán bitwise OR:
   $$\operatorname{Bitmap}_{\text{union}} = \bigvee_{i=0}^{N-1} \operatorname{Bitmap}(S_i)$$
2. **Tách biệt Ngưỡng Bão hòa (Decoupled Saturation Logic)**: Trạng thái `PLATEAU` chỉ được công nhận khi và chỉ khi **tốc độ tăng trưởng của đồ thị cạnh hợp nhất toàn cụm $\Delta \operatorname{Edges}_{\text{union}} / \Delta t$ giảm xuống dưới ngưỡng $\epsilon$ trong 3 chu kỳ liên tiếp (45 giây)**.
3. **Rào chắn Thu hoạch Crash Độc lập (Guaranteed Crash Harvest Barrier)**: Việc sao chép và thu hoạch crash được tách rời hoàn toàn khỏi trạng thái bão hòa độ phủ. Bất kể fuzzer dừng do `PLATEAU`, hết thời gian (`TIMEOUT`), hay nhận tín hiệu ngoại lệ, hàm `harvest_all_instance_crashes` luôn được bảo đảm thực thi trước khi bất kỳ tiến trình nào bị dừng.

#### 5.1.2 Thiết kế Triển khai Chi tiết

```python
"""
Mô-đun: MultiInstanceAFLManager & Guaranteed Crash Harvest Barrier
Vị trí đề xuất thay thế: src/tools/fuzz/bin/run_fuzzer
"""

import os
import time
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set

@dataclass
class InstanceStats:
    instance_name: str
    execs: int = 0
    exec_per_sec: float = 0.0
    edges_found: int = 0
    saved_crashes: int = 0
    last_find: int = 0
    bitmap_cvg_pct: float = 0.0

@dataclass
class ClusterTelemetry:
    total_execs: int = 0
    effective_exec_per_sec: float = 0.0
    total_raw_crashes: int = 0
    union_edge_count: int = 0
    instances: Dict[str, InstanceStats] = field(default_factory=dict)
    combined_bitmap: bytearray = field(default_factory=lambda: bytearray(65536))

class MultiInstanceAFLManager:
    """Điều phối giám sát telemetry, phát hiện bão hòa cụm và thu hoạch crash độc lập."""

    def __init__(self, output_dir: str, fuzzer_id: int):
        self.output_dir = output_dir
        self.fuzzer_id = fuzzer_id
        self.crash_stage_dir = ProjectUtils.get_fuzzer_crash_dir(fuzzer_id)
        os.makedirs(self.crash_stage_dir, exist_ok=True)

    def discover_instances(self) -> List[str]:
        """Tự động khám phá Master ('default') và toàn bộ các Slaves ('slave*')."""
        if not os.path.exists(self.output_dir):
            return []
        return [
            entry for entry in os.listdir(self.output_dir)
            if os.path.isdir(os.path.join(self.output_dir, entry)) and
            (entry == "default" or entry.startswith("slave"))
        ]

    def poll_cluster_telemetry(self) -> ClusterTelemetry:
        """Hợp nhất fuzzer_stats và tính toán Bitmap Phủ toàn cụm."""
        telemetry = ClusterTelemetry()
        instances = self.discover_instances()
        union_bitmap = bytearray(65536)

        for inst in instances:
            inst_dir = os.path.join(self.output_dir, inst)
            stats_file = os.path.join(inst_dir, "fuzzer_stats")
            bitmap_file = os.path.join(inst_dir, "fuzz_bitmap")

            stats = self._parse_stats_file(stats_file)
            if stats:
                telemetry.instances[inst] = stats
                telemetry.total_execs += stats.execs
                telemetry.effective_exec_per_sec += stats.exec_per_sec
                telemetry.total_raw_crashes += stats.saved_crashes

            # Hợp nhất bitmap độ phủ bằng phép bitwise OR
            if os.path.exists(bitmap_file):
                try:
                    with open(bitmap_file, "rb") as bf:
                        data = bf.read()
                        limit = min(len(data), 65536)
                        for i in range(limit):
                            # AFL++ bitmap: 0xff là chưa hit, < 0xff là đã hit
                            union_bitmap[i] |= (~data[i] & 0xFF)
                except Exception:
                    pass

        # Đếm tổng số cạnh độc nhất đã được kích hoạt trong toàn cụm
        telemetry.union_edge_count = sum(bin(byte).count('1') for byte in union_bitmap)
        telemetry.combined_bitmap = union_bitmap
        return telemetry

    def _parse_stats_file(self, filepath: str) -> Optional[InstanceStats]:
        if not os.path.exists(filepath):
            return None
        stats = InstanceStats(instance_name=os.path.basename(os.path.dirname(filepath)))
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if k == "execs_done":
                        stats.execs = int(v)
                    elif k == "execs_per_sec":
                        stats.exec_per_sec = float(v)
                    elif k == "edges_found":
                        stats.edges_found = int(v)
                    elif k == "saved_crashes":
                        stats.saved_crashes = int(v)
                    elif k == "bitmap_cvg":
                        stats.bitmap_cvg_pct = float(v.strip("%"))
            return stats
        except Exception:
            return None

    def harvest_all_instance_crashes(self) -> int:
        """
        RÀO CHẮN THU HOẠCH CRASH ĐỘC LẬP:
        Thu thập toàn bộ các tệp crash từ Master và TẤT CẢ các Slaves.
        Bảo đảm thực thi vô điều kiện trước khi hủy tiến trình.
        """
        instances = self.discover_instances()
        harvested_count = 0
        known_signatures: Set[str] = set()

        for inst in instances:
            crashes_dir = os.path.join(self.output_dir, inst, "crashes")
            if not os.path.exists(crashes_dir):
                continue

            for fname in os.listdir(crashes_dir):
                if fname.startswith("README") or fname.startswith("."):
                    continue
                src_path = os.path.join(crashes_dir, fname)
                if not os.path.isfile(src_path):
                    continue

                # Khử trùng lặp sơ bộ bằng mã băm SHA256 nội dung đầu vào
                file_hash = ProjectUtils.calculate_file_sha256(src_path)
                if file_hash in known_signatures:
                    continue
                known_signatures.add(file_hash)

                staged_name = f"id_{self.fuzzer_id:03d}_{inst}_{fname}"
                dest_path = os.path.join(self.crash_stage_dir, staged_name)
                try:
                    shutil.copy2(src_path, dest_path)
                    harvested_count += 1
                except Exception as e:
                    print_debug(f"[!] Warning: Lỗi khi sao chép crash {src_path}: {e}")

        return harvested_count
```

---

### 5.2 Hệ thống Phòng thủ 4 Lớp Ngăn chặn Macro Hijacking (Defense-in-Depth Macro Guard)

Để ngăn ngừa tuyệt đối hiện tượng LLM tự ý chèn các macro debug nội bộ phá hủy ABI, chúng tôi thiết kế hệ thống kiểm soát 4 tầng:

```
  +--------------------------------------------------------------------------+
  | Tầng 1: Ràng buộc Tiêu cực Phản xạ trong Prompt (Negative Prompt Anchor) |
  | (Cung cấp lý do ABI và thiết lập hình phạt biên dịch nghiêm khắc)       |
  +--------------------------------------------------------------------------+
                                       |
                                       v
  +--------------------------------------------------------------------------+
  | Tầng 2: Bộ Tiền Lọc Token Bằng Biểu Thức Chính Quy (Regex Pre-Filter)    |
  | (Chặn đứng tức thì tại build_harness trước khi gọi trình biên dịch)      |
  +--------------------------------------------------------------------------+
                                       |
                                       v
  +--------------------------------------------------------------------------+
  | Tầng 3: Trình Giám sát Tiền xử lý Clang AST (AST PPCallbacks Guard)      |
  | (Phân tích AST sâu, kiểm tra macro định nghĩa trong main file)          |
  +--------------------------------------------------------------------------+
                                       |
                                       v
  +--------------------------------------------------------------------------+
  | Tầng 4: Môi trường Biên dịch Hermetic Đóng kín                          |
  | (Áp đặt cờ -DNDEBUG, -Werror=macro-redefined, cô lập Header nội bộ)      |
  +--------------------------------------------------------------------------+
```

#### 5.2.1 Triển khai Tầng 2: Regex Token Sanitizer trong `build_harness`
Chèn đoạn mã kiểm tra tĩnh ngay trước khi thực thi lệnh gọi `clang++`:

```python
"""
Mô-đun kiểm định Macro tiền xử lý
Vị trí tích hợp: src/tools/harness/bin/build_harness
"""

import re
from typing import Tuple, List

FORBIDDEN_MACRO_PATTERNS = [
    # Chặn bật macro debug nội bộ
    r"^\s*#\s*define\s+([A-Za-z0-9_]*DEBUG[A-Za-z0-9_]*)",
    r"^\s*#\s*define\s+([A-Za-z0-9_]*INTERNAL[A-Za-z0-9_]*)",
    r"^\s*#\s*define\s+([A-Za-z0-9_]*PRIVATE[A-Za-z0-9_]*)",
    # Chặn alias định danh hàm để lách lỗi biên dịch
    r"^\s*#\s*define\s+([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\s*$",
    # Chặn can thiệp vào tiền tố riêng của các thư viện benchmark
    r"^\s*#\s*define\s+MPACK_",
    r"^\s*#\s*define\s+BZ3_",
    r"^\s*#\s*define\s+SIMDJSON_",
]

def sanitize_harness_macros(harness_source_path: str) -> Tuple[bool, List[str]]:
    """Quét mã nguồn harness để phát hiện các macro xâm phạm ABI."""
    violations = []
    with open(harness_source_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        for pattern in FORBIDDEN_MACRO_PATTERNS:
            if re.search(pattern, stripped):
                violations.append(
                    f"Dòng {idx}: Chỉ thị tiền xử lý bị cấm '{stripped}'. "
                    f"Nghiêm cấm định nghĩa macro nội bộ hoặc đổi tên hàm API."
                )
    return len(violations) == 0, violations
```

#### 5.2.2 Triển khai Tầng 3: Clang AST Preprocessor Callbacks Tool (`macro_guard.cpp`)
Sử dụng thư viện Clang LibTooling để giám sát quá trình tiền xử lý ở mức độ phân tích cú pháp trừu tượng:

```cpp
// macro_guard.cpp — Clang AST Preprocessor Guard
#include "clang/Frontend/FrontendActions.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Lex/PPCallbacks.h"
#include "clang/Lex/Preprocessor.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"
#include <iostream>

using namespace clang;
using namespace clang::tooling;

class MacroAuditCallbacks : public PPCallbacks {
public:
    explicit MacroAuditCallbacks(SourceManager &SM) : SM(SM), HasViolation(false) {}

    void MacroDefined(const Token &MacroNameTok, const MacroDirective *MD) override {
        StringRef Name = MacroNameTok.getIdentifierInfo()->getName();
        SourceLocation Loc = MD->getLocation();

        // Chỉ kiểm tra các macro được định nghĩa trực tiếp trong tệp harness chính
        if (SM.isInMainFile(Loc)) {
            if (Name.contains_insensitive("DEBUG") ||
                Name.contains_insensitive("INTERNAL") ||
                Name.startswith("MPACK_") ||
                Name.startswith("BZ3_") ||
                Name.startswith("SIMDJSON_")) {
                std::cerr << "[LỖI AST] Phát hiện macro cấm trong harness: "
                          << Name.str() << " tại dòng "
                          << SM.getSpellingLineNumber(Loc) << std::endl;
                HasViolation = true;
            }
        }
    }
    bool HasViolation;
private:
    SourceManager &SM;
};
```

---

### 5.3 Thư viện Thích ứng An toàn `SafeBufferAdapter` & Bộ Phân loại Triage Gatekeeper 2 Lớp (Two-Tier Frame Blame Assignment)

#### 5.3.1 Thư viện Thích ứng An toàn Runtime (`safe_adapter.hpp`)
Để giải quyết tận gốc lỗi `std::vector::data()` trả về con trỏ `nullptr` khi container rỗng, chúng tôi xây dựng một header adapter tiêu chuẩn, tự động được include vào mọi harness thông qua cờ biên dịch `-include fuzzing/safe_adapter.hpp`:

```cpp
#pragma once
#include <vector>
#include <string>
#include <cstdint>
#include <cstddef>

namespace agentic_fuzzing {

// Vùng đệm tĩnh 8-byte bảo đảm luôn là con trỏ hợp lệ, không bao giờ là nullptr
alignas(16) static const char DUMMY_NON_NULL_BUFFER[16] = {0};

/**
 * Trả về con trỏ bộ nhớ bảo đảm NON-NULL ngay cả khi vector rỗng.
 * Triệt tiêu hoàn toàn lỗi UndefinedBehaviorSanitizer: memcpy(dest, NULL, 0).
 */
template <typename T>
inline const T* safe_data(const std::vector<T>& vec) {
    if (vec.empty()) {
        return reinterpret_cast<const T*>(DUMMY_NON_NULL_BUFFER);
    }
    return vec.data();
}

template <typename T>
inline T* safe_data(std::vector<T>& vec) {
    if (vec.empty()) {
        return const_cast<T*>(reinterpret_cast<const T*>(DUMMY_NON_NULL_BUFFER));
    }
    return vec.data();
}

/**
 * Bảo đảm giá trị kích thước/giới hạn luôn > 0 để thỏa mãn assertion thư viện.
 */
inline size_t safe_positive_limit(size_t val, size_t default_min = 1) {
    return (val == 0) ? default_min : val;
}

} // namespace agentic_fuzzing

// Macro tiện ích cho Harness Generator
#define SAFE_DATA(v) agentic_fuzzing::safe_data(v)
#define SAFE_LIMIT(v) agentic_fuzzing::safe_positive_limit(v)
```

#### 5.3.2 Bộ Phân loại Triage Gatekeeper 2 Lớp (Two-Tier Blame Assignment)
Nâng cấp thuật toán `pre_triage_and_dedup_crashes` trong `run_fuzzer`. Thay vì chỉ nhìn vào Frame #0, bộ lọc tiến hành phân tích cặp tương quan giữa **Frame #0 (Nơi kích hoạt lỗi)** và **Frame #1 (Nơi gọi hàm)**:

```python
"""
Bộ Phân loại Triage Gatekeeper 2 Lớp
Vị trí tích hợp: src/tools/fuzz/bin/run_fuzzer
"""

def triage_crash_two_tier(stack_trace_output: str, harness_path: str) -> dict:
    frames = parse_stack_frames(stack_trace_output)
    if not frames:
        return {"verdict": "NON_CRASH", "reason": "Không thể trích xuất Call Stack."}

    f0 = frames[0]
    f1 = frames[1] if len(frames) > 1 else None

    # TẦNG 1: Phát hiện vi phạm tiền điều kiện con trỏ truyền từ harness
    # Lỗi memcpy(dest, NULL, 0) kích hoạt invalid-null-argument
    if "null pointer passed as argument" in stack_trace_output:
        if f1 and (harness_path in f1["file"] or "LLVMFuzzerTestOneInput" in f1["function"]):
            return {
                "verdict": "HARNESS_BUG",
                "reason": f"Harness truyền con trỏ NULL từ {f1['file']}:{f1['line']} vào `{f1['function']}`."
            }

    # TẦNG 2: Phát hiện vi phạm assertion do đối số giá trị biên không hợp lệ từ harness
    if "unreachable program point" in stack_trace_output or "__assert_fail" in f0["function"]:
        if f1 and (harness_path in f1["file"] or "LLVMFuzzerTestOneInput" in f1["function"]):
            return {
                "verdict": "HARNESS_BUG",
                "reason": f"Harness kích hoạt assertion thư viện do truyền đối số biên sai tại {f1['file']}:{f1['line']}."
            }

    # Nếu Frame #0 nằm trực tiếp trong file harness
    if harness_path in f0["file"]:
        return {
            "verdict": "HARNESS_BUG",
            "reason": f"Crash xảy ra trực tiếp trong mã harness tại {f0['file']}:{f0['line']}."
        }

    # Crash thực sự trong thư viện hợp lệ
    return {
        "verdict": "LIBRARY_BUG",
        "crashing_frame": f0,
        "caller_frame": f1
    }
```

---

### 5.4 Giao thức Hợp đồng Chuẩn hóa JSON `CoverageGuidanceContract.json` & Sửa Triệt để Bug Boolean

#### 5.4.1 Sửa Lỗi Boolean Inversion trong `CoverageAnalyzerAgent`
Sửa đổi mã nguồn trong `src/agents/cov-analyzer/agent.py` tại dòng 46–68 để khôi phục lại vòng phản hồi độ phủ:

```python
# DIFF KHẮC PHỤC LỖI LOGIC ĐẢO NGƯỢC
# File: src/agents/cov-analyzer/agent.py

- def no_fuzzer_in_plateau(self) -> bool:
-     fuzz_profile = get_fuzzer_profile()
-     for _, fuzz_info in fuzz_profile.fuzzers.items():
-         if fuzz_info.state == FuzzerExecutionState.PLATEAU:
-             return True
-     return False

+ def has_fuzzer_in_plateau(self) -> bool:
+     """Kiểm tra chính xác xem CÓ fuzzer nào đang ở trạng thái PLATEAU hay không."""
+     fuzz_profile = get_fuzzer_profile()
+     for _, fuzz_info in fuzz_profile.fuzzers.items():
+         if fuzz_info.state == FuzzerExecutionState.PLATEAU:
+             return True
+     return False

# Và sửa tại hàm register_agent_pre_call (dòng 63):
- if self.no_fuzzer_in_plateau():
+ if not self.has_fuzzer_in_plateau():
      self.can_return_early = True
      ...
```

#### 5.4.2 Chuẩn hóa Giao thức Dữ liệu Trao đổi JSON (`CoverageGuidanceContract.json`)
Để bảo đảm tính trực giao, cấm ngặt nghèo `CoverageAnalyzerAgent` sinh mã C++. Thay vào đó, tác tử này xuất ra một tệp JSON có cấu trúc chặt chẽ tuân theo lược đồ hình thức:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CoverageGuidanceContract",
  "type": "object",
  "required": [
    "guidance_id",
    "target_module",
    "focus_apis",
    "required_setup_sequence",
    "required_cleanup_sequence",
    "branch_blockers",
    "parameter_constraints"
  ],
  "properties": {
    "guidance_id": { "type": "string" },
    "target_module": { "type": "string" },
    "focus_apis": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["api_name", "uncovered_branches"],
        "properties": {
          "api_name": { "type": "string" },
          "uncovered_branches": { "type": "integer" }
        }
      }
    },
    "required_setup_sequence": { "type": "array", "items": { "type": "string" } },
    "required_cleanup_sequence": { "type": "array", "items": { "type": "string" } },
    "branch_blockers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["source_file", "line_number", "condition_expression"],
        "properties": {
          "source_file": { "type": "string" },
          "line_number": { "type": "integer" },
          "condition_expression": { "type": "string" }
        }
      }
    },
    "parameter_constraints": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["parameter_name", "requires_non_null", "minimum_value"],
        "properties": {
          "parameter_name": { "type": "string" },
          "requires_non_null": { "type": "boolean" },
          "minimum_value": { "type": "integer" }
        }
      }
    }
  }
}
```

---

## 6. KẾ HOẠCH THỰC NGHIỆM KIỂM CHỨNG TOÀN DIỆN (EMPIRICAL BENCHMARK PLAN)

Nhằm kiểm chứng khách quan các giải pháp kỹ thuật đã đề xuất, chúng tôi xây dựng một kế hoạch thực nghiệm chuẩn mực khoa học (theo quy chuẩn IEEE S&P / ACM CCS) trên 3 thư viện mục tiêu mang tính đại diện cao.

---

### 6.1 Thiết kế Môi trường và 3 Thư viện Mục tiêu

Ba thư viện được lựa chọn nhằm tạo áp lực tối đa lên các khía cạnh kiến trúc khác nhau:

| Thư viện Mục tiêu | Phiên bản (Commit) | Ngôn ngữ & Đặc trưng Miền | Thách thức Cốt lõi đối với Agentic Fuzzing |
| :--- | :--- | :--- | :--- |
| **`bzip3`** | `v1.5.1` (`kspalaiologos/bzip3`) | C99/C++: Nén khối, Burrows-Wheeler Transform, Suffix Arrays (libsais) | Thử thách mật độ thuật toán và xử lý bitstream; API tuyến tính nhưng nhạy cảm với lỗi tràn số signed bit-shift. |
| **`simdjson`** | `v3.10.1` (`simdjson/simdjson`) | C++17/20: Phân tích JSON tốc độ cao bằng tập lệnh vector SIMD (AVX2, NEON) | Đòi hỏi ràng buộc phần cứng khắt khe: Vùng đệm đầu vào bắt buộc phải có ít nhất `SIMDJSON_PADDING` (64 bytes). |
| **`mpack`** | `v1.1.1` (`ludocode/mpack`) | C99/C++: Tuần tự hóa đối tượng nhị phân MessagePack | Đòi hỏi quản lý trạng thái luồng (Reader/Writer/Tree/Node), kiểm soát nghiêm ngặt con trỏ không null và kích thước giới hạn. |

---

### 6.2 Ma trận Cấu hình Thực nghiệm Đối chứng (Ablation Matrix) & 4 Baselines

#### 6.2.1 Ma trận Cấu hình Phân lập (6-Way Ablation Study)
Để bóc tách định lượng đóng góp chính xác của từng giải pháp kỹ thuật, hệ thống sẽ được đánh giá trên 6 cấu hình:

| Mã Cấu hình | Mô tả Kiến trúc | Động cơ Saturation | Bộ lọc Macro | Xử lý Ngữ nghĩa Con trỏ | Giao thức Cov-Harness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`Config-Full`** | **Agentic Fuzzing v2 (Đề xuất)** | Multi-Instance AFL Manager | Clang AST + Regex Linter | SafeBufferAdapter + Gatekeeper 2 lớp | JSON Schema Chuẩn |
| **`Ablation-Sat`** | Bỏ cơ chế Saturation mới | Legacy Master-Only | Clang AST + Regex Linter | SafeBufferAdapter + Gatekeeper 2 lớp | JSON Schema Chuẩn |
| **`Ablation-Macro`**| Bỏ bộ lọc Macro | Multi-Instance AFL Manager | Không lọc (Chỉ dùng Prompt) | SafeBufferAdapter + Gatekeeper 2 lớp | JSON Schema Chuẩn |
| **`Ablation-Ptr`** | Bỏ SafeBufferAdapter | Multi-Instance AFL Manager | Clang AST + Regex Linter | Dùng raw `vector.data()` | JSON Schema Chuẩn |
| **`Ablation-Gate`**| Bỏ Gatekeeper 2 lớp | Multi-Instance AFL Manager | Clang AST + Regex Linter | SafeBufferAdapter + Raw Frame #0 Gate | JSON Schema Chuẩn |
| **`Ablation-Proto`**| Bỏ Hợp đồng JSON | Multi-Instance AFL Manager | Clang AST + Regex Linter | SafeBufferAdapter + Gatekeeper 2 lớp | Văn bản tự do Markdown |

#### 6.2.2 4 Hệ thống So sánh Cơ sở (Baselines)
1. **Vanilla AFL++ (v4.30c)**: Fuzzer greybox tiêu chuẩn công nghiệp với CMPLOG và MOPT, chạy thuần túy không có sự hỗ trợ của LLM.
2. **Google OSS-Fuzz-Gen (2024–2025)**: Hệ thống sinh harness công nghiệp dựa trên phân tích tĩnh Fuzz Introspector và sửa lỗi biên dịch LLM.
3. **PromptFuzz (ACM CCS 2024)**: Hệ thống sinh harness dựa trên vòng lặp đột biến prompt đơn lẻ có hướng dẫn độ phủ.
4. **FuzzAgent (Lyu et al., 2026 Baseline)**: Bản gốc của hệ thống trước khi khắc phục các lỗi (vẫn còn dính lỗi Saturation Shadowing và Macro Hijacking).

---

### 6.3 Hệ thống Chỉ số Đo lường Định lượng và Công thức Toán học

#### 6.3.1 Độ phủ Nhánh (Branch Coverage) theo Thời gian
Đo lường liên tục bằng `llvm-cov` tại các mốc $t \in \{1h, 4h, 8h, 12h, 24h\}$:
$$\text{BranchCov}(t) = \frac{|\mathcal{B}_{\text{covered}}(t)|}{|\mathcal{B}_{\text{total}}|} \times 100\%$$
$$\Delta \text{Cov}_{\text{gain}} = \text{BranchCov}_{\text{Config-Full}}(24h) - \text{BranchCov}_{\text{Baseline}}(24h)$$

#### 6.3.2 Tỷ lệ Biên dịch Harness Hợp lệ (Valid Compilation Rate - VCR)
$$\text{VCR}_{\text{first-pass}} = \frac{N_{\text{compiled\_pass\_0}}}{N_{\text{total\_generated}}} \times 100\%, \quad \text{VCR}_{\text{final}} = \frac{N_{\text{compiled\_after\_repair}}}{N_{\text{total\_generated}}} \times 100\% \quad (\text{vòng sửa} \le 3)$$

#### 6.3.3 Tỷ lệ Crash Thật và Giả (True Positive vs. False Positive Crash Rate)
$$\text{True Positive Crash Rate (TPCR)} = \frac{|\mathcal{C}_{\text{genuine\_library\_bug}}|}{|\mathcal{C}_{\text{total\_crashes}}|} \times 100\%$$
$$\text{False Positive Crash Rate (FPCR)} = \frac{|\mathcal{C}_{\text{harness\_misuse}}| + |\mathcal{C}_{\text{sanitizer\_pedantry}}|}{|\mathcal{C}_{\text{total\_crashes}}|} \times 100\%$$

#### 6.3.4 Thời gian Phát hiện Lỗ hổng (Time-to-Exposure - TTE) và Đường cong Sống sót Kaplan-Meier
$$TTE(b) = \min \{ t \ge 0 \mid \text{BugOracle}(b, \text{Input}(t)) = \text{TRIGGERED} \}$$
Hàm sống sót Kaplan-Meier ước lượng xác suất một lỗ hổng chưa bị phát hiện tại thời điểm $t$:
$$\hat{S}(t) = \prod_{t_i \le t} \left( 1 - \frac{d_i}{n_i} \right)$$
Trong đó $d_i$ là số lượng lỗ hổng được phát hiện tại thời điểm $t_i$, và $n_i$ là số lượng lỗ hổng còn lại chưa bị phát hiện ngay trước $t_i$.

#### 6.3.5 Hiệu suất Sử dụng Token và Tài nguyên (Token & Resource Efficiency Ratios)
$$\text{EfficiencyRatio (ER)} = \frac{\Delta \text{BranchCount}}{\text{Tổng Tokens Tiêu thụ (triệu tokens)}}$$
$$\text{CostPerUniqueBug} = \frac{\text{Tổng Chi phí LLM API (\$) + Chi phí Điện toán (\%)}}{\text{Số Lỗ hổng Độc nhất Phát hiện}}$$

---

### 6.4 Quy chuẩn Độ tin cậy Thống kê (Statistical Rigor Protocol)

Theo khuyến nghị thực nghiệm của Klees et al. (IEEE S&P 2018):
- **Phân bổ Phần cứng**: Mỗi lượt chạy được cố định (pinning) cứng vào **8 lõi CPU vật lý** (1 Master + 7 Slaves) thông qua `taskset` để loại bỏ nhiễu do tranh chấp CPU. Bộ nhớ RAM được cấu hình tối thiểu 64 GB cho mỗi tác vụ.
- **Thời lượng**: Chiến dịch ngắn (12 giờ) và Chiến dịch dài hạn (24 giờ).
- **Số lần Lặp lại**: Mỗi cấu hình trên mỗi thư viện được lặp lại độc lập **$N \ge 5$ lần** với các seed ngẫu nhiên khác nhau (tổng cộng 90 lượt chạy ablation + 60 lượt chạy baseline = 150 lượt chạy thực nghiệm).
- **Kiểm định Ý nghĩa Thống kê Phi tham số**: Do dữ liệu độ phủ và crash trong fuzzing không tuân theo phân phối chuẩn, sử dụng kiểm định hai phía **Mann-Whitney U Test** để xác định mức ý nghĩa thống kê ($p < 0.05$).
- **Đo lường Mức độ Ảnh hưởng (Effect Size)**: Sử dụng chỉ số phi tham số **Vargha-Delaney $\hat{A}_{12}$**:
  $$\hat{A}_{12} = \frac{\sum_{i=1}^{n_1} \sum_{j=1}^{n_2} \psi(x_i, y_j)}{n_1 n_2}, \quad \psi(x, y) = \begin{cases} 1 & x > y \\ 0.5 & x = y \\ 0 & x < y \end{cases}$$
  *Thang đánh giá*: $\hat{A}_{12} \ge 0.71$ khẳng định cấu hình đề xuất vượt trội có ý nghĩa thực tiễn lớn (Large Practical Significance) so với baseline.

---

## 7. KẾT LUẬN VÀ LỘ TRÌNH TRIỂN KHAI

### 7.1 Kết luận Khoa học
Báo cáo phân tích chuyên sâu này đã giải mã toàn diện các thách thức cốt tử của hệ thống **Agentic Fuzzing**:
1. Đã chỉ rõ nguyên nhân kỹ thuật và các dòng mã chính xác của 4 vấn đề nghiêm trọng trong chiến dịch `mpack` 17h+: Lỗi Saturation Shadowing tiêu diệt crash của Slaves, Lỗi Macro Hijacking làm lệch ABI, Lỗi `vector::data()` rỗng gây crash giả và Gatekeeper Frame #0 chẩn đoán sai, cùng Lỗi logic đảo ngược boolean làm tê liệt hoàn toàn CoverageAnalyzer.
2. Đã đối chiếu có hệ thống với các công trình hàng đầu thế giới (FuzzAgent, OSS-Fuzz-Gen, PromptFuzz, ChatAFL), chỉ ra sự ảo tưởng về tính hợp lệ cú pháp (Syntactic Validity Illusion) và sự đứt gãy trạng thái cụm fuzzer.
3. Đã đề xuất giải pháp công nghệ toàn diện với code diff, AST linter, SafeBufferAdapter, và hợp đồng JSON chuẩn hóa.
4. Đã thiết kế kế hoạch thực nghiệm kiểm chứng quy chuẩn quốc tế trên 3 thư viện `bzip3`, `simdjson`, `mpack`.

### 7.2 Lộ trình Triển khai Kỹ thuật (Implementation Roadmap)

```
Giai đoạn 1: Vá lỗi Cốt lõi & Khôi phục Vòng phản hồi (Tuần 1)
- [x] Sửa lỗi boolean đảo ngược tại src/agents/cov-analyzer/agent.py (has_fuzzer_in_plateau).
- [ ] Tích hợp MultiInstanceAFLManager vào src/tools/fuzz/bin/run_fuzzer: Đảm bảo thu hoạch crash vô điều kiện.
- [ ] Cập nhật prompt few-shot trong src/agents/harness-generator/prompt.py: Loại bỏ hoàn toàn raw .data().

Giai đoạn 2: Tích hợp Rào chắn Bảo vệ Tiền biên dịch (Tuần 2)
- [ ] Triển khai bộ lọc Regex Token Sanitizer trong src/tools/harness/bin/build_harness.
- [ ] Biên dịch công cụ Clang AST macro_guard và chèn vào quy trình kiểm tra build_harness.
- [ ] Cài đặt tệp tiêu đề fuzzing/safe_adapter.hpp vào đường dẫn include mặc định của sanitizer build.

Giai đoạn 3: Nâng cấp Gatekeeper & Chuẩn hóa Giao thức Đa tác tử (Tuần 3)
- [ ] Thay thế bộ phân loại crash trong run_fuzzer bằng Two-Tier Gatekeeper (kiểm tra Frame #0 và Frame #1).
- [ ] Triển khai bộ kiểm thực JSON Schema CoverageGuidanceContract.json tại ManagerAgent.
- [ ] Cập nhật prompt CoverageAnalyzer để chỉ xuất dữ liệu JSON, cấm hoàn toàn sinh mã C++.

Giai đoạn 4: Thực thi Kế hoạch Benchmark Thực nghiệm 150 Lượt chạy (Tuần 4 - Tuần 5)
- [ ] Triển khai thực nghiệm trên 4 máy chủ AMD EPYC (pinning 8 cores/run).
- [ ] Chạy 90 runs Ablation Study (6 cấu hình x 3 thư viện x 5 runs).
- [ ] Chạy 60 runs Baselines (AFL++, OSS-Fuzz-Gen, PromptFuzz, FuzzAgent).
- [ ] Thu thập dữ liệu telemetry, tính toán Mann-Whitney U test, Vargha-Delaney A12, vẽ biểu đồ Kaplan-Meier.
- [ ] Xuất bản bài báo khoa học hoàn chỉnh hướng tới các hội thảo bảo mật hàng đầu (ACM CCS / USENIX Security / NDSS).
```
