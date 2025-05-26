from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import astrbot.api.message_components
import aiohttp
import base64
import json
from urllib.parse import unquote
from .baidu_auth import get_baidu_access_token


async def get_beauty_score(event: AstrMessageEvent):
    """获取图片颜值评分（使用百度人脸识别API）。"""
    try:
        try:
            access_token = await get_baidu_access_token()
            if not access_token:
                return event.plain_result("获取百度API凭证失败，暂时无法评分，请稍后再试。")
        except Exception as e:
            logger.error(f"获取百度access_token时发生错误: {e}")
            return event.plain_result("获取百度API凭证时发生错误，请稍后再试。")

        image_components = [c for c in event.message_obj.message if isinstance(c, astrbot.api.message_components.Image)]
        if not image_components:
            return event.plain_result("请发送一张图片来进行颜值评分。")
            
        image_url_orig = image_components[0].url
        base64_data = await get_image_as_base64(image_url_orig)
        
        access_token = await get_baidu_access_token()
        if not access_token:
            # get_baidu_access_token 函数已记录详细错误
            return event.plain_result("获取百度API凭证失败，暂时无法评分，请稍后再试。")

        detect_url = f"https://aip.baidubce.com/rest/2.0/face/v3/detect?access_token={access_token}"
        
        payload = {
            "image": base64_data,
            "image_type": "BASE64",
            "face_field": "beauty,age,gender,emotion,glasses,face_shape,quality,mask,spoofing,eye_status,landmark150",
            "max_face_num": 1, # 仅分析最大的人脸
            "liveness_control": "NORMAL" # 增加活体检测
        }
        
        headers = {'Content-Type': 'application/json'}

        async with aiohttp.ClientSession() as session:
            async with session.post(detect_url, json=payload, headers=headers) as resp:
                response_text_for_logging = await resp.text() # 记录原始响应以进行调试
                if resp.status == 200:
                    try:
                        response_data = json.loads(response_text_for_logging)
                    except json.JSONDecodeError:
                        logger.error(f"百度API响应非JSON格式: {response_text_for_logging}")
                        return event.plain_result("颜值评分服务返回异常，请稍后再试。")

                    if response_data.get("error_code") == 0:
                        if response_data.get("result") and response_data["result"].get("face_num", 0) > 0:
                            face_info = response_data["result"]["face_list"][0]
                            beauty_score = face_info.get("beauty", 0)
                            age = face_info.get("age", "未知")
                            
                            gender_info = face_info.get("gender", {}).get("type")
                            gender = {"male": "帅哥", "female": "美女"}.get(gender_info, "人物")
                            
                            emotion_info = face_info.get("emotion", {}).get("type")
                            # 更新情绪映射以匹配API文档
                            emotions_map = {
                                "angry": "愤怒", "disgust": "厌恶", "fear": "恐惧", 
                                "happy": "高兴", "sad": "伤心", "surprise": "惊讶", 
                                "neutral": "平静", "pouty": "撅嘴", "grimace": "鬼脸",
                                # 保留旧的映射以兼容可能的情况，但优先使用API标准
                                "none": "平静", "smile": "微笑", "laugh": "大笑"
                            }
                            emotion = emotions_map.get(emotion_info, "自然")

                            glasses_info = face_info.get("glasses", {}).get("type")
                            glasses_map = {"none": "未戴眼镜", "common": "普通眼镜", "sun": "太阳镜"}
                            glasses = glasses_map.get(glasses_info, "")

                            face_shape_info = face_info.get("face_shape", {}).get("type", "未知")
                            face_shape_map = {
                                "square": "方形脸", "triangle": "三角脸", "oval": "椭圆脸", 
                                "heart": "心形脸", "round": "圆形脸"
                            }
                            face_shape = face_shape_map.get(face_shape_info, "未知脸型")

                            quality = face_info.get("quality", {})
                            blur = quality.get("blur", 0) # API: 0清晰, 1模糊. 代码中 >0.7 提示模糊, 逻辑保持但默认值改为0
                            illumination = quality.get("illumination", 128) # API: [0~255], 越大越好. 代码中 <40 提示暗, 逻辑保持但默认值改为中间值
                            completeness = quality.get("completeness", 1) # API: 0或1. 0为人脸溢出, 1为完整

                            mask_info = face_info.get("mask", {}).get("type") # 0未戴, 1戴
                            mask_status = "戴口罩" if mask_info == 1 else "未戴口罩"

                            eye_status_info = face_info.get("eye_status", {})
                            left_eye_val = eye_status_info.get("left_eye", -1.0) # API: [0,1], 越接近0闭合
                            right_eye_val = eye_status_info.get("right_eye", -1.0)
                            
                            def get_eye_state_desc(val):
                                if val < 0: return "未知"
                                return "睁眼" if val > 0.5 else "闭眼"

                            left_eye_str = get_eye_state_desc(left_eye_val)
                            right_eye_str = get_eye_state_desc(right_eye_val)
                            eye_desc = None
                            if left_eye_val >= 0 or right_eye_val >= 0:
                                eye_desc = f"眼睛状态：左眼 {left_eye_str}, 右眼 {right_eye_str}"

                            liveness_score = face_info.get("liveness", {}).get("livemapscore", -1.0)
                            spoofing_score = face_info.get("spoofing", -1.0) # 判断图片是合成图的概率
                            

                                
                            # 增强质量分析报告
                            quality = face_info.get("quality", {})
                            blur = quality.get("blur", 0)
                            illumination = quality.get("illumination", 128)
                            completeness = quality.get("completeness", 1)
                            quality_score = quality.get("score", 0)
                            
                            # 初始化result_parts列表
                            result_parts = []
                            
                            # 增强质量分析报告
                            result_parts.append("--------------------")
                            result_parts.append("📊 质量分析：")
                            if quality_score > 0:
                                result_parts.append(f"  综合质量评分：{quality_score:.1f}/100")
                                
                            # 详细质量指标
                            blur_status = "清晰" if blur <= 0.3 else "轻微模糊" if blur <= 0.7 else "模糊"
                            light_status = "明亮" if illumination > 200 else "正常" if illumination > 100 else "较暗" if illumination > 40 else "很暗"
                            result_parts.append(f"  清晰度：{blur_status} (值：{blur:.2f})")
                            result_parts.append(f"  光照：{light_status} (值：{illumination})")
                            result_parts.append(f"  完整度：{'完整' if completeness == 1 else '不完整'}")
                            
                            # 增强活体分析
                            liveness_analysis = ""
                            if liveness_score != -1:
                                if liveness_score > 0.8:
                                    liveness_analysis = "(真人可能性很高)"
                                elif liveness_score > 0.5:
                                    liveness_analysis = "(可能是真人)"
                                else:
                                    liveness_analysis = "(可能是照片)"
                                
                                # 添加活体检测详细分析
                                liveness_details = face_info.get("liveness", {})
                                if "faceliveness" in liveness_details:
                                    liveness_analysis += f"，活体检测得分：{liveness_details['faceliveness']:.2f}"
                                if "faceliveness_threshold" in liveness_details:
                                    liveness_analysis += f" (阈值：{liveness_details['faceliveness_threshold']:.2f})"
                                
                                # 添加活体检测详细评分
                                result_parts.append(f"  活体检测总分：{liveness_score:.2f}")
                                if "faceliveness" in liveness_details:
                                    result_parts.append(f"  活体检测详细得分：{liveness_details['faceliveness']:.2f}")
                                if "faceliveness_threshold" in liveness_details:
                                    result_parts.append(f"  活体检测阈值：{liveness_details['faceliveness_threshold']:.2f}")
                            
                            # 构建结果
                            result_parts = ["✨ 颜值分析报告 ✨"]
                            result_parts.append("--------------------")
                            result_parts.append(f"👤 基本信息：")
                            result_parts.append(f"  这位{gender}的颜值评分为：{beauty_score:.0f}分！")
                            
                            # 添加详细质量分析
                            if quality_score > 0:
                                result_parts.append(f"  综合质量评分：{quality_score:.1f}/100")
                            

                                
                            # 添加活体检测详细分析
                            if liveness_score != -1:
                                liveness_status = "真人" if liveness_score > 0.8 else "可能是真人" if liveness_score > 0.5 else "可能是照片"
                                result_parts.append(f"  活体检测：{liveness_status} (得分：{liveness_score:.2f})")
                                
                            # 添加防伪检测
                            if spoofing_score != -1:
                                spoofing_status = "真实照片" if spoofing_score < 0.3 else "可能是真实照片" if spoofing_score < 0.7 else "可能是合成图片"
                                result_parts.append(f"  防伪检测：{spoofing_status} (得分：{spoofing_score:.2f})")
                                
                            # 添加活体检测详细分析
                            if liveness_score != -1:
                                liveness_status = "真人" if liveness_score > 0.8 else "可能是真人" if liveness_score > 0.5 else "可能是照片"
                                result_parts.append(f"  活体检测：{liveness_status} (得分：{liveness_score:.2f})")
                            if beauty_score > 85: result_parts.append("    评价：倾国倾城，颜值爆表！")
                            elif beauty_score > 75: result_parts.append("    评价：相当出众，魅力十足！")
                            elif beauty_score > 60: result_parts.append("    评价：颜值在线，还不错哦！")
                            elif beauty_score > 40: result_parts.append("    评价：嗯...大众脸型吧。")
                            else: result_parts.append("    评价：颜值...可能需要美颜相机加持一下。")
                            result_parts.append(f"  年龄大约：{age}岁")
                            result_parts.append(f"  当前表情：{emotion}")
                            result_parts.append(f"  脸型判断：{face_shape}")
                            result_parts.append(f"  人脸置信度：{face_info.get('face_probability', 0)*100:.1f}%")
                            
                            
                            # 添加角度信息
                            angle = face_info.get('angle', {})
                            yaw = angle.get('yaw', 0)
                            pitch = angle.get('pitch', 0)
                            roll = angle.get('roll', 0)
                            result_parts.append(f"  头部角度：左右{yaw:.1f}°, 上下{pitch:.1f}°, 旋转{roll:.1f}°")

                            result_parts.append("--------------------")
                            result_parts.append("👓 外观细节：")
                            if glasses: result_parts.append(f"  眼镜情况：{glasses}")
                            else: result_parts.append("  眼镜情况：未戴眼镜或未识别")
                            result_parts.append(f"  口罩状态：{mask_status}")
                            if eye_desc: result_parts.append(f"  {eye_desc}")
                            else: result_parts.append("  眼睛状态：未识别")

                            result_parts.append("--------------------")
                            result_parts.append("📸 图片分析：")
                            if liveness_score != -1:
                                result_parts.append(f"  活体得分：{liveness_score:.2f} (越高越像真人)")
                            else:
                                result_parts.append("  活体得分：未检测到")
                            if spoofing_score != -1:
                                if spoofing_score > 0.00048: # 使用推荐阈值
                                    result_parts.append(f"  真实度分析：有较高概率为合成图片 (置信度 {spoofing_score:.5f})")
                                else:
                                    result_parts.append(f"  真实度分析：较高概率为真实人像 (合成置信度 {spoofing_score:.5f})")
                            else:
                                result_parts.append("  真实度分析：未检测到")

                            quality_warnings = []
                            if blur > 0.7: quality_warnings.append("照片有点模糊")
                            if illumination < 40: quality_warnings.append("照片光线有点暗")
                            if completeness == 0: quality_warnings.append("人脸可能不完整或溢出图像边界")

                            occlusion_info = quality.get("occlusion", {})
                            occlusion_parts_desc = []
                            occlusion_threshold = 0.3 # 遮挡超过30%才提示
                            if occlusion_info.get("left_eye", 0) > occlusion_threshold: occlusion_parts_desc.append("左眼")
                            if occlusion_info.get("right_eye", 0) > occlusion_threshold: occlusion_parts_desc.append("右眼")
                            if occlusion_info.get("nose", 0) > occlusion_threshold: occlusion_parts_desc.append("鼻子")
                            if occlusion_info.get("mouth", 0) > occlusion_threshold: occlusion_parts_desc.append("嘴巴")
                            if occlusion_info.get("left_cheek", 0) > occlusion_threshold: occlusion_parts_desc.append("左脸颊")
                            if occlusion_info.get("right_cheek", 0) > occlusion_threshold: occlusion_parts_desc.append("右脸颊")
                            if occlusion_info.get("chin_contour", 0) > occlusion_threshold: occlusion_parts_desc.append("下巴")
                            if occlusion_parts_desc:
                                quality_warnings.append(f"以下部位可能被遮挡：{', '.join(occlusion_parts_desc)}")

                            if quality_warnings:
                                result_parts.append("--------------------")
                                result_parts.append("⚠️ 温馨提示：")
                                for warning in quality_warnings:
                                    result_parts.append(f"  - {warning}")
                                
                            return event.plain_result("\n".join(result_parts))
                        else: 
                            logger.info(f"百度API未检测到人脸或结果为空: {response_data}")
                            return event.plain_result("图片中未检测到清晰人像，换张试试？")
                    elif response_data.get("error_code") == 222202: 
                        logger.info(f"百度API未检测到人脸: {response_data.get('error_msg')}")
                        return event.plain_result("图片中未检测到清晰人像，换张试试？")
                    elif response_data.get("error_code") == 18: 
                         logger.warning(f"百度API QPS超限: {response_data.get('error_msg')}")
                         return event.plain_result("请求太快啦，请稍等片刻再试~")
                    else:
                        error_msg = response_data.get('error_msg', '未知错误')
                        error_code = response_data.get('error_code')
                        logger.error(f"百度API调用出错: {error_msg}, Code: {error_code}. Raw: {response_text_for_logging}")
                        return event.plain_result(f"人脸分析失败: {error_msg} (错误码: {error_code})")
                else: 
                    logger.error(f"请求百度人脸检测API失败，状态码: {resp.status}, 响应: {response_text_for_logging}")
                    return event.plain_result("颜值评分服务暂时不可用 (网络请求失败)，请稍后再试。")
            
    except aiohttp.ClientError as e: 
        logger.error(f"连接百度人脸检测服务时发生错误: {e}", exc_info=True)
        return event.plain_result("连接颜值评分服务失败，请检查网络或稍后再试。")
    except Exception as e: 
        logger.error(f"获取颜值评分时发生未知错误: {e}", exc_info=True)
        return event.plain_result("获取颜值评分时发生了内部错误，请联系管理员。")

async def get_image_as_base64(image_url: str) -> str:
    """下载图片并转换为Base64编码。"""
    if 'multimedia.nt.qq.com.cn' in image_url and 'url=' in image_url:
        image_url = image_url.split('url=')[-1]
        image_url = unquote(image_url)
        
    try:
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            async with session.get(image_url, headers=headers, timeout=10) as resp: 
                if resp.status == 200:
                    data = await resp.read()
                    return base64.b64encode(data).decode('utf-8')
                else:
                    logger.error(f"下载图片失败，URL: {image_url}, 状态码: {resp.status}")
                    raise Exception(f"下载图片失败，状态码: {resp.status}")
    except aiohttp.ClientError as e:
        logger.error(f"下载图片时发生网络错误，URL: {image_url}, 错误: {e}")
        raise Exception(f"下载图片时发生网络错误: {e}")
    except Exception as e: 
        logger.error(f"下载图片时发生未知错误，URL: {image_url}, 错误: {e}")
        raise Exception(f"下载图片时发生未知错误: {e}")