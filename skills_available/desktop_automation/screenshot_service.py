"""
截图服务模块 - 用于截取桌面屏幕
"""

import base64
import io
import logging
from typing import Optional
from PIL import Image
import mss

logger = logging.getLogger(__name__)


class ScreenshotService:
    """截图服务"""

    def __init__(self):
        self.sct = mss.mss()

    def capture_desktop(self) -> Image.Image:
        """
        截取整个桌面
        
        Returns:
            PIL Image 对象
        """
        # 获取主显示器
        monitor = self.sct.monitors[1]  # monitors[0] 是所有显示器的组合，monitors[1] 是主显示器
        logger.debug(f"准备截取主显示器，区域: {monitor}")
        
        # 截取屏幕
        screenshot = self.sct.grab(monitor)
        
        # 转换为PIL Image
        img = Image.frombytes(
            "RGB",
            screenshot.size,
            screenshot.bgra,
            "raw",
            "BGRX"
        )
        
        logger.debug(f"截图完成，尺寸: {img.size}, 模式: {img.mode}")
        return img

    def capture_to_base64(
        self, 
        image: Optional[Image.Image] = None, 
        format: str = "JPEG",
        max_width: int = 1920,
        quality: int = 85
    ) -> str:
        """
        将图片转换为base64字符串（自动压缩以优化性能）
        
        Args:
            image: PIL Image对象，如果为None则先截取桌面
            format: 图片格式，默认JPEG（比PNG更小）
            max_width: 最大宽度，超过会自动缩放，默认1920
            quality: JPEG质量（1-100），默认85
            
        Returns:
            base64编码的图片字符串（不含data URI前缀）
        """
        if image is None:
            image = self.capture_desktop()
        
        # 压缩图片以减小数据量
        original_size = image.size
        if image.width > max_width:
            # 按比例缩放
            scale = max_width / image.width
            new_height = int(image.height * scale)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"截图已压缩: {original_size} -> {image.size}")
        
        # 转换为RGB格式（JPEG不支持透明通道）
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # 将图片保存到内存缓冲区
        buffer = io.BytesIO()
        if format.upper() == "JPEG":
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
        else:
            image.save(buffer, format=format, optimize=True)
        
        buffer.seek(0)
        file_size = len(buffer.getvalue())
        logger.info(f"截图编码完成: 格式={format}, 尺寸={image.size}, 文件大小={file_size/1024:.1f}KB")
        
        # 转换为base64
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        base64_size = len(img_base64)
        logger.info(f"Base64编码完成: {base64_size/1024:.1f}KB")
        
        return img_base64

    def capture_to_file(self, file_path: str, image: Optional[Image.Image] = None) -> str:
        """
        将截图保存到文件
        
        Args:
            file_path: 保存路径
            image: PIL Image对象，如果为None则先截取桌面
            
        Returns:
            文件路径
        """
        if image is None:
            image = self.capture_desktop()
        
        image.save(file_path)
        return file_path

    def close(self):
        """关闭截图服务"""
        if hasattr(self, 'sct'):
            self.sct.close()
