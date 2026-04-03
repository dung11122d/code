from __future__ import annotations

from schemas import Segment


def build_translation_prompt(segment: Segment, prev_text: str, next_text: str) -> str:
    return (
        "Bạn là biên dịch viên chuyên dịch thoại phim từ tiếng Trung sang tiếng Việt.\n"
        "Mục tiêu: câu dịch tự nhiên, ngắn gọn, đúng ngữ cảnh, dễ đọc thành voice.\n"
        "Luôn giữ nhất quán tên riêng và đại từ xưng hô.\n"
        "Không giải thích. Không thêm ghi chú.\n"
        "BẮT BUỘC chỉ trả về JSON hợp lệ đúng schema:\n"
        '{"id": <int>, "vi_text": "<string>"}\n\n'
        f"id: {segment.id}\n"
        f"text: {segment.original_text}\n"
        f"context_previous: {prev_text or '[none]'}\n"
        f"context_next: {next_text or '[none]'}\n"
    )


def build_fix_json_prompt(invalid_response: str, seg_id: int) -> str:
    return (
        "Chuỗi sau không đúng JSON.\n"
        f"Hãy chuyển thành JSON hợp lệ duy nhất cho id={seg_id}, schema: "
        '{"id": <int>, "vi_text": "<string>"}.\n'
        "Không thêm markdown/code block.\n"
        f"raw: {invalid_response}"
    )
