from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from schemas import Segment
from translator.base import Translator
from translator.prompt_builder import build_fix_json_prompt, build_translation_prompt
from utils.file_utils import append_text


class ChatGPTBrowserTranslator(Translator):
    def __init__(
        self,
        chromedriver_path: Path,
        profile_dir: Path,
        selectors: dict,
        chatgpt_url: str,
        max_retries: int,
        delay_sec: float,
        logger: logging.Logger,
        headless: bool = False,
        chrome_binary: str | None = None,
    ) -> None:
        self.logger = logger
        self.selectors = selectors
        self.max_retries = max_retries
        self.delay_sec = delay_sec
        self.chatgpt_url = chatgpt_url
        self.driver = self._build_driver(
            chromedriver_path, profile_dir, headless, chrome_binary
        )
        self.wait = WebDriverWait(self.driver, 45)

    def _build_driver(
        self,
        chromedriver_path: Path,
        profile_dir: Path,
        headless: bool,
        chrome_binary: str | None,
    ) -> Chrome:
        options = Options()
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--window-size=1600,1000")
        if headless:
            options.add_argument("--headless=new")
        if chrome_binary:
            options.binary_location = chrome_binary
        service = Service(executable_path=str(chromedriver_path))
        return webdriver.Chrome(service=service, options=options)

    def open_and_wait_login(self) -> None:
        self.driver.get(self.chatgpt_url)
        self.logger.info("Opened ChatGPT page: %s", self.chatgpt_url)
        try:
            self._find_input_box()
        except TimeoutException:
            input(
                "Please login manually in opened Chrome (if needed), then press Enter to continue..."
            )
            self._find_input_box()

    def _find_with_fallback(self, selector_list: list[dict], cond: str = "visible"):
        last_err: Exception | None = None
        for s in selector_list:
            by = By.CSS_SELECTOR if s["by"].lower() == "css" else By.XPATH
            try:
                if cond == "visible":
                    return self.wait.until(
                        EC.visibility_of_element_located((by, s["value"]))
                    )
                return self.wait.until(EC.presence_of_element_located((by, s["value"])))
            except Exception as ex:
                last_err = ex
                continue
        if last_err:
            raise last_err
        raise TimeoutException("No selector matched")

    def _find_input_box(self):
        return self._find_with_fallback(self.selectors["prompt_input"], cond="visible")

    def _click_send(self) -> None:
        send_button = self._find_with_fallback(self.selectors["send_button"], cond="present")
        send_button.click()

    def _wait_response_complete(self) -> None:
        # Wait until stop button disappears OR input enabled again.
        for _ in range(90):
            stop_visible = False
            for s in self.selectors["stop_button"]:
                by = By.CSS_SELECTOR if s["by"].lower() == "css" else By.XPATH
                elems = self.driver.find_elements(by, s["value"])
                if any(e.is_displayed() for e in elems):
                    stop_visible = True
                    break
            if not stop_visible:
                return
            time.sleep(0.5)
        raise TimeoutException("Timed out waiting response completion")

    def _get_latest_response_text(self) -> str:
        nodes = []
        for s in self.selectors["assistant_messages"]:
            by = By.CSS_SELECTOR if s["by"].lower() == "css" else By.XPATH
            nodes = self.driver.find_elements(by, s["value"])
            if nodes:
                break
        if not nodes:
            raise RuntimeError("Cannot find assistant response nodes")
        return nodes[-1].text.strip()

    def _send_prompt(self, prompt: str) -> str:
        input_box = self._find_input_box()
        input_box.click()
        input_box.send_keys(Keys.CONTROL, "a")
        input_box.send_keys(prompt)
        self._click_send()
        self._wait_response_complete()
        return self._get_latest_response_text()

    def _parse_json(self, response: str, seg_id: int) -> dict:
        response = response.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            data = json.loads(response)
            if int(data.get("id")) != seg_id:
                raise ValueError("ID mismatch")
            return data
        except Exception as ex:
            raise ValueError(f"Invalid JSON: {ex}") from ex

    def translate_segments(self, segments: list[Segment]) -> list[Segment]:
        for idx, seg in enumerate(segments):
            if seg.vi_text:
                continue
            prev_text = segments[idx - 1].original_text if idx > 0 else ""
            next_text = segments[idx + 1].original_text if idx < len(segments) - 1 else ""
            prompt = build_translation_prompt(seg, prev_text, next_text)
            raw = ""
            for attempt in range(1, self.max_retries + 1):
                self.logger.info("Translating segment %s attempt %s", seg.id, attempt)
                raw = self._send_prompt(prompt)
                try:
                    parsed = self._parse_json(raw, seg.id)
                    seg.vi_text = parsed["vi_text"].strip()
                    self.logger.info("Segment %s translated", seg.id)
                    break
                except Exception as ex:
                    self.logger.warning("Parse failed seg %s: %s", seg.id, ex)
                    prompt = build_fix_json_prompt(raw, seg.id)
                    if attempt == self.max_retries:
                        raise
                time.sleep(self.delay_sec)
            yield_record = {
                "id": seg.id,
                "original_text": seg.original_text,
                "raw_response": raw,
                "vi_text": seg.vi_text,
            }
            append_text(Path("logs/chatgpt_raw.log"), json.dumps(yield_record, ensure_ascii=False))
        return segments

    def close(self) -> None:
        self.driver.quit()
