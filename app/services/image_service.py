from typing import Optional, Dict, List, Tuple
from io import BytesIO
import tempfile
import os
import re
import traceback

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image


class ImageService:
    def __init__(self):
        self.enabled = True
        self.ocr_engine = None
        # 设置 PaddleX 缓存目录到有权限的位置
        os.environ['PADDLEX_HOME'] = os.path.join(os.getcwd(), 'tmp_data', 'paddlex')
        os.makedirs(os.environ['PADDLEX_HOME'], exist_ok=True)

    def _get_ocr_engine(self):
        """
        延迟加载 OCR 模型，避免服务启动过慢。
        """
        if self.ocr_engine is None:
            from paddleocr import PaddleOCR
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang="ch"
            )
        return self.ocr_engine

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像预处理：
        1. 灰度
        2. 去噪
        3. 自适应二值化
        """
        if image is None:
            return image

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31, 10
        )
        return binary

    def _bytes_to_cv2(self, image_data: bytes) -> np.ndarray:
        """
        bytes -> OpenCV 图像
        """
        np_arr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return image

    def _pdf_to_images(self, pdf_bytes: bytes, max_pages: int = 3) -> List[np.ndarray]:
        """
        PDF -> 图片列表，只取前几页，避免太慢
        """
        images = []
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = min(len(pdf), max_pages)

        for i in range(page_count):
            page = pdf[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            images.append(img)

        return images

    def _run_ocr_on_image(self, image: np.ndarray) -> Tuple[str, List[Dict], float]:
        """
        对单张图片做 OCR
        返回：
        - 拼接后的文本
        - 明细结果
        - 平均置信度
        """
        ocr = self._get_ocr_engine()

        # 预处理
        processed = self._preprocess_image(image)

        # PaddleOCR 2.x 对 ndarray 直接识别
        result = ocr.ocr(processed, cls=True)

        lines = []
        details = []
        scores = []

        if result and len(result) > 0:
            for line in result[0]:
                box = line[0]
                text = line[1][0]
                score = float(line[1][1])

                if text and text.strip():
                    lines.append(text.strip())
                    details.append({
                        "text": text.strip(),
                        "score": score,
                        "box": box
                    })
                    scores.append(score)

        full_text = "\n".join(lines)
        avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0

        return full_text, details, avg_score

    def _extract_medical_fields(self, text: str) -> Dict:
        """
        从 OCR 文本中做简单结构化提取
        可根据你们病例模板继续扩展
        """
        def match_one(patterns, default=""):
            for p in patterns:
                m = re.search(p, text, re.I)
                if m:
                    return m.group(1).strip()
            return default

        data = {
            "patient_name": match_one([
                r"姓名[:：]\s*([^\n ]+)",
                r"患者[:：]\s*([^\n ]+)"
            ]),
            "gender": match_one([
                r"性别[:：]\s*(男|女)"
            ]),
            "age": match_one([
                r"年龄[:：]\s*([0-9]{1,3})",
                r"([0-9]{1,3})\s*岁"
            ]),
            "department": match_one([
                r"科室[:：]\s*([^\n]+)"
            ]),
            "diagnosis": match_one([
                r"诊断[:：]\s*([^\n]+)",
                r"出院诊断[:：]\s*([^\n]+)"
            ]),
            "surgery": match_one([
                r"手术名称[:：]\s*([^\n]+)",
                r"术式[:：]\s*([^\n]+)"
            ]),
            "advice": match_one([
                r"医嘱[:：]\s*([\s\S]{0,200})"
            ])
        }

        # 化验指标简单抽取
        indicators = []
        pattern = r"(白细胞|血红蛋白|血小板|C反应蛋白|CRP|血糖|肌酐|尿素氮)[:：]?\s*([0-9]+(?:\.[0-9]+)?)"
        for item in re.finditer(pattern, text, re.I):
            indicators.append({
                "name": item.group(1),
                "value": item.group(2)
            })
        data["indicators"] = indicators

        return data

    async def extract_text_from_report(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        从病例图片/PDF中提取文字
        """
        if not self.enabled:
            return {"text": "", "message": "OCR 识别功能尚未启用"}

        try:
            filename = filename or ""
            content_type = content_type or ""

            all_text = []
            all_details = []
            all_scores = []

            is_pdf = (
                content_type == "application/pdf"
                or filename.lower().endswith(".pdf")
            )

            if is_pdf:
                images = self._pdf_to_images(image_data, max_pages=3)
                for idx, img in enumerate(images):
                    text, details, score = self._run_ocr_on_image(img)
                    all_text.append(f"--- 第{idx+1}页 ---\n{text}")
                    all_details.extend(details)
                    if score > 0:
                        all_scores.append(score)
            else:
                image = self._bytes_to_cv2(image_data)
                text, details, score = self._run_ocr_on_image(image)
                all_text.append(text)
                all_details.extend(details)
                if score > 0:
                    all_scores.append(score)

            final_text = "\n".join([t for t in all_text if t.strip()])
            avg_score = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0
            structured = self._extract_medical_fields(final_text)

            return {
                "text": final_text,
                "avg_score": avg_score,
                "structured": structured,
                "details": all_details[:100]  # 避免返回太大
            }

        except Exception as e:
            traceback.print_exc()
            return {
                "text": "",
                "avg_score": 0.0,
                "structured": {},
                "details": [],
                "message": f"OCR 提取失败: {str(e)}"
            }

    async def analyze_medical_image(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        这里先复用 OCR + 简单结构化分析
        以后你们可以继续扩展成：
        伤口图像分析 / 红肿识别 / 渗液判断 / 风险分级
        """
        return await self.extract_text_from_report(
            image_data=image_data,
            filename=filename,
            content_type=content_type
        )


image_service = ImageService()