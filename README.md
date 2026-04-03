# CN -> VI Video Dubbing (Local-first, No Paid API)

Ứng dụng Python chạy trên Windows để tự động:
1) tách audio từ video tiếng Trung,
2) nhận diện lời nói bằng `faster-whisper` local,
3) dịch từng câu qua ChatGPT Web bằng Selenium,
4) tạo giọng Việt local (Coqui XTTS hoặc Piper),
5) ghép lại thành video lồng tiếng Việt.

> Không dùng OpenAI API/Google API/Azure API/ElevenLabs API.

---

## 1) Kiến trúc chính

Pipeline:
- **Extract**: `video/audio_extractor.py`
- **ASR**: `speech/transcriber.py`
- **Translate** (browser automation): `translator/chatgpt_browser.py`
- **TTS**: `tts/voice_generator.py`
- **Timeline + Mix**: `dubbing/timeline_builder.py`, `dubbing/audio_mixer.py`
- **Mux video**: `dubbing/video_muxer.py`
- **Orchestration**: `main.py`

Thiết kế có cache + resume:
- `transcript.json`, `translated_segments.json`, `progress.json`
- nếu dừng giữa chừng, chạy lại sẽ tận dụng file trung gian.

---

## 2) Cài đặt môi trường

### 2.1 Python
- Cài **Python 3.11+**
- Tạo venv:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

### 2.2 ffmpeg
- Tải ffmpeg bản Windows, thêm vào PATH.
- Kiểm tra:

```powershell
ffmpeg -version
```

### 2.3 Chrome + ChromeDriver
- Cài Google Chrome.
- Tải ChromeDriver đúng phiên bản Chrome.
- Cấu hình đường dẫn tại `config/config.example.yaml`:
  - `chrome.chromedriver_path`
  - `chrome.binary` (nếu cần)
  - `chrome.profile_dir` (để lưu session đăng nhập ChatGPT)

---

## 3) Cấu hình

Sao chép và sửa file mẫu:

```powershell
copy config\config.example.yaml config\config.yaml
```

Sửa các mục quan trọng:
- `input_video`
- `output_root`
- `chrome.chromedriver_path`
- `chrome.profile_dir`
- `asr.model`
- `tts.backend`, `tts.model` (hoặc Piper path)
- `audio.mix_mode`
- `chatgpt.selectors` (khi UI ChatGPT thay đổi)

---

## 4) Đăng nhập ChatGPT lần đầu

1. Chạy pipeline.
2. Chrome sẽ mở bằng profile riêng (`user-data-dir`).
3. Nếu chưa đăng nhập, app sẽ chờ bạn login thủ công.
4. Sau khi login thành công, quay lại terminal và nhấn Enter.
5. Lần sau app dùng lại profile, không cần login lại (trừ khi hết phiên).

---

## 5) Chạy chương trình

```powershell
python main.py --config config/config.yaml --export-srt
```

Tuỳ chọn:
- `--resume`: chạy tiếp theo trạng thái cache.
- `--skip-translation`: bỏ qua bước Selenium translation (dùng `translated_segments.json` có sẵn).
- `--skip-tts`: bỏ qua bước tạo giọng.

---

## 6) Kết quả output

Mỗi video tạo một thư mục timestamp riêng, ví dụ:

- `extracted_audio.wav`
- `transcript.json`
- `translated_segments.json`
- `generated_tts/seg_XXXX.wav`
- `final_voice_track.wav`
- `final_audio.wav`
- `final_video_vi.mp4`
- `translated_vi.srt` (nếu bật `--export-srt`)
- `pipeline.log`
- `progress.json`

---

## 7) Resume khi lỗi giữa chừng

- Bản dịch/TTS từng segment đã lưu trong `translated_segments.json`.
- Chạy lại với cùng config + input sẽ sử dụng cache.
- Nếu lỗi một segment TTS, sửa xong chỉ cần chạy lại, các segment đã có file WAV sẽ được bỏ qua.

---

## 8) Đổi model ASR/TTS

- ASR: thay `asr.model` (ví dụ `small`, `medium`, `large-v3`)
- TTS:
  - `coqui`: đặt `tts.backend=coqui`, chọn model phù hợp.
  - `piper`: đặt `tts.backend=piper`, cấu hình `piper_exe`, `piper_model_path`.

---

## 9) Lỗi thường gặp

1. **Không tìm thấy prompt input/send button của ChatGPT**
   - Nguyên nhân: UI ChatGPT đổi selector.
   - Cách xử lý: cập nhật `chatgpt.selectors` trong config.

2. **ChromeDriver version mismatch**
   - Cập nhật ChromeDriver đúng phiên bản Chrome.

3. **ffmpeg not found**
   - Thêm ffmpeg vào PATH hoặc set `ffmpeg_path` đầy đủ.

4. **Model TTS quá nặng**
   - Chuyển sang Piper cho máy yếu.

5. **JSON trả về không đúng format**
   - Hệ thống đã có retry + prompt sửa định dạng.
   - Tăng `translation.max_retries` nếu cần.

---

## 10) Lưu ý quan trọng về Selenium + ChatGPT

- Đây là automation UI nên dễ vỡ khi frontend đổi.
- Luôn dùng selector fallback (đã hỗ trợ trong config).
- Dùng explicit waits thay vì sleep cứng cho thao tác chính.
- Không triển khai bypass CAPTCHA/login/rate-limit.

---

## 11) Lệnh chạy mẫu nhanh

```powershell
python main.py --config config/config.yaml --export-srt
```

