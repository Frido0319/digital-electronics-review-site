from __future__ import annotations

import json
import re
from pathlib import Path

import fitz

from . import config
from .models import KnowledgePoint, Question, SourcePage, SubQuestion, to_jsonable


def _source(file: str, page: int, image: str) -> SourcePage:
    return SourcePage(file=file, page=page, image_path=image)


OFFICIAL_ANSWER_FILE = "课后作业/电子技术部分章节作业参考答案to中德.pdf"

OFFICIAL_ANSWER_PAGE_LOOKUP: dict[str, list[int]] = {
    "1.3.6": [1],
    "1.3.9": [1, 2],
    "1.4.3": [2],
    "1.5.8": [2, 3],
    "1.5.9": [2, 3],
    "2.2.5": [3, 4],
    "2.3.4": [4],
    "2.3.5": [4],
    "2.4.5": [4, 5],
    "2.4.6": [5, 6],
    "2.4.7": [6],
    "2.6.2": [6],
    "2.6.3": [6, 7, 8],
    "2.6.4": [8, 9],
    "3.1.2": [9, 10],
    "3.2.8": [10],
    "3.2.13": [11],
    "3.2.16": [11, 12],
    "3.2.21": [12],
    "3.3.4": [12, 13, 14],
    "4.2.6": [14],
    "4.2.12": [14, 15],
}


def _official_answer_image_name(page: int) -> str:
    return f"assets/official_answer_pages/official_answers_p{page:03d}.png"


def _official_answer_pages(question_id: str) -> list[SourcePage]:
    return [
        _source(OFFICIAL_ANSWER_FILE, page, _official_answer_image_name(page))
        for page in OFFICIAL_ANSWER_PAGE_LOOKUP.get(question_id, [])
    ]


def _apply_official_answer_pages(questions: list[Question]) -> list[Question]:
    updated: list[Question] = []
    for question in questions:
        pages = _official_answer_pages(question.id)
        if not pages:
            updated.append(question)
            continue
        page_list = "、".join(f"p.{page.page}" for page in pages)
        official_subquestions = [
            SubQuestion(
                id=subquestion.id,
                prompt=subquestion.prompt,
                answer=f"见本题下方官方参考答案截图（{page_list}），以截图中的手写推导、公式和最终结果为准。",
                solution_steps=subquestion.solution_steps,
            )
            for subquestion in question.subquestions
        ]
        updated.append(
            Question(
                id=question.id,
                chapter=question.chapter,
                title=question.title,
                prompt=question.prompt,
                image_paths=question.image_paths,
                knowledge_ids=question.knowledge_ids,
                source_pages=question.source_pages,
                subquestions=official_subquestions,
                answer_source="官方答案",
                official_answer_pages=pages,
            )
        )
    return updated


def _pending_question(
    id: str,
    chapter: str,
    title: str,
    prompt: str,
    image_paths: list[str],
    knowledge_ids: list[str],
    source_pages: list[SourcePage],
    route: list[str],
) -> Question:
    return Question(
        id=id,
        chapter=chapter,
        title=title,
        prompt=prompt,
        image_paths=image_paths,
        knowledge_ids=knowledge_ids,
        source_pages=source_pages,
        subquestions=[SubQuestion(id, "完成本题。", "待接入官方答案或进一步推导。", route)],
        answer_source="待核对",
    )


def _ai_fallback_question(
    id: str,
    chapter: str,
    title: str,
    prompt: str,
    image_paths: list[str],
    knowledge_ids: list[str],
    source_pages: list[SourcePage],
    answer: str,
    route: list[str],
) -> Question:
    return Question(
        id=id,
        chapter=chapter,
        title=title,
        prompt=prompt,
        image_paths=image_paths,
        knowledge_ids=knowledge_ids,
        source_pages=source_pages,
        subquestions=[SubQuestion(id, "完成本题。", answer, route)],
        answer_source="AI兜底答案",
    )


def _gallery_image_name(file: str, page: int) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", file).strip("_").lower()
    if len(stem) > 64:
        stem = stem[-64:]
    return f"assets/course_pages/gallery_{stem}_p{page:03d}.png"


def _ppt_gallery_image_name(file: str, page: int) -> str:
    if file == "第4章  电子电路中的反馈.ppt":
        return f"assets/course_pages/gallery_ppt_ch4_feedback_p{page:03d}.png"
    return _gallery_image_name(file, page)


def _gallery_source(file: str, page: int) -> SourcePage:
    image_name = _ppt_gallery_image_name if file.lower().endswith((".ppt", ".pptx")) else _gallery_image_name
    return _source(file, page, image_name(file, page))


def _gallery_sources(file: str, pages: list[int]) -> list[SourcePage]:
    return [_gallery_source(file, page) for page in pages]


def _office_pdf_path(path: Path) -> Path:
    if path.name == "第4章  电子电路中的反馈.ppt":
        return config.PROJECT_ROOT / "tmp" / "office_convert" / "ch4_feedback.pdf"
    return config.PROJECT_ROOT / "tmp" / "office_convert" / f"{path.stem}.pdf"


def _office_page_count(path: Path) -> int:
    output_pdf = _office_pdf_path(path)
    if not output_pdf.is_file():
        from .extract_sources import convert_office_to_pdf

        if not convert_office_to_pdf(path, output_pdf):
            return 0
    try:
        doc = fitz.open(str(output_pdf))
    except Exception:
        return 0
    page_count = doc.page_count
    doc.close()
    return page_count


def _source_file_key(path) -> str:
    return str(path.relative_to(config.SOURCE_ROOT)).replace("\\", "/")


EXCLUDED_LECTURE_GALLERY_RANGES: dict[str, list[tuple[int, int]]] = {
    "第2章 基本放大电路/第2章-基本放大电路9.pdf": [(1, 24)],  # 2.6 场效应晶体管放大电路
    "第2章 基本放大电路/第2章-基本放大电路10.pdf": [(21, 25)],  # 2.8 放大电路的频率特性
    "第5章-直流稳压电源.pdf": [
        (18, 22),  # 5.1.3 三相桥式整流电路
        (33, 34),  # 5.2.2 电感电容滤波器；5.2.3 π形滤波器
        (59, 62),  # 5.3.4 开关型稳压电源
    ],
    "第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路5.pdf": [(61, 67)],  # 7.12 应用举例
}

SUPER_KEY_DIR_NAME = "\u91cd\u70b9\u4e2d\u7684\u91cd\u70b9"
SUPER_KEY_REASON_PREFIX = "\u91cd\u70b9\u4e2d\u7684\u91cd\u70b9\u622a\u56fe\u547d\u4e2d"


SUPER_KEY_SOURCE_PAGE_RULES: dict[str, list[tuple[str, list[int]]]] = {
    "1.jpg": [
        ("第7章-门电路和组合逻辑电路1.pdf", [1, 12, 16, 18, 19, 20, 21, 22, 23, 24, 27, 28, 30]),
        ("第7章 门电路和组合逻辑电路2.pdf", [1, 7, 8, 11, 13, 14, 19, 20, 21, 25]),
        ("第7章 门电路和组合逻辑电路3.pdf", [1, 2, 3, 6, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22, 23, 24]),
        ("第7章 门电路和组合逻辑电路4.pdf", [1, 2, 4, 10, 12, 13, 16, 22]),
        ("第7章 门电路和组合逻辑电路5.pdf", [1, 20, 36, 50, 51, 52, 53, 54, 55, 56, 57, 58]),
    ],
    "2.jpg": [
        ("第5章-直流稳压电源.pdf", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 23, 24, 25, 26, 28, 29, 30, 31, 32, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]),
    ],
    "4.jpg": [
        ("第3章  集成运算放大电路11.pdf", [1, 2, 3, 4, 5, 7, 9, 11, 12, 13, 14, 16, 17, 18, 19, 21, 22, 24, 28]),
        ("第3章  集成运算放大电路12.pdf", [1, 2, 7, 9, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 27, 28, 30, 40]),
    ],
    "5.jpg": [
        ("第2章-基本放大电路5.pdf", [2, 3, 5, 13, 22]),
        ("第2章-基本放大电路6.pdf", [1, 2, 3]),
        ("第2章-基本放大电路10.pdf", [1, 6, 7, 8, 9, 10, 11, 16, 17, 19, 20, 26, 28, 37, 38]),
    ],
    "7.jpg": [
        ("第2章-基本放大电路5.pdf", [2, 3, 5, 13, 22]),
        ("第2章-基本放大电路6.pdf", [1, 2, 3]),
        ("第2章-基本放大电路7.pdf", [1, 10]),
        ("第2章-基本放大电路8.pdf", [2, 3, 4]),
        ("第2章-基本放大电路10.pdf", [7, 8, 9, 10, 11, 16, 17, 19, 20, 26, 28, 37, 38]),
        ("第3章  集成运算放大电路11.pdf", [1, 2, 4, 5, 11, 13, 16, 17, 18, 21, 28]),
        ("第3章  集成运算放大电路12.pdf", [1, 2, 7, 12, 15, 18, 19, 20, 30, 40]),
    ],
    "8.jpg": [
        ("第1章-半导体器件1.pdf", [16, 17, 29, 31, 33, 34]),
        ("第1章-半导体器件2.pdf", [3, 4, 6, 7, 8, 9, 10, 11, 17, 18, 19, 22, 23, 24]),
        ("第1章-半导体器件34-.pdf", [1, 2, 3, 5, 7, 8, 9, 15, 17, 18, 19, 22, 23, 24, 27, 31]),
    ],
    "9.jpg": [
        ("第1章-半导体器件1.pdf", [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 29, 30, 31, 32, 33, 34]),
        ("第1章-半导体器件2.pdf", [3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]),
        ("第1章-半导体器件34-.pdf", [1, 2, 3, 5, 7, 8, 9, 15, 17, 18, 19, 22, 23, 24, 27, 31]),
    ],
    "9b3303554c659be093baf22ab61de8e0.jpg": [
        ("第7章 门电路和组合逻辑电路4.pdf", [1, 2, 10, 12, 13, 16, 22, 23, 29]),
        ("第7章 门电路和组合逻辑电路5.pdf", [1, 20, 22, 26, 31, 32, 34, 36, 37, 42, 43, 44, 48, 50, 51, 52, 53, 54, 55, 56, 57, 58, 78, 80, 86, 87, 92, 94, 102, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 124, 125]),
    ],
    "10.jpg": [
        ("第7章 门电路和组合逻辑电路5.pdf", [114, 115, 116, 117, 118, 119, 124, 125]),
    ],
}


EXAM_ESSENTIAL_REASON = "一定会考"


def build_exam_essentials() -> list[dict]:
    return [
        {
            "id": "essential-intrinsic-semiconductor",
            "chapter": "1",
            "title": "本征半导体",
            "prompt": "什么是本征半导体？",
            "answer": "本征半导体是完全纯净、晶格完整的半导体，例如高纯硅或锗。它靠本征激发产生等量自由电子和空穴，两类载流子都参与导电，但载流子数量很少，所以导电能力较弱。",
            "prerequisites": ["知道硅、锗是四价元素", "知道自由电子和空穴都能形成电流"],
            "source_pages": _gallery_sources("第1章 半导体器件讲义/第1章-半导体器件1.pdf", [18, 20, 21, 22, 23, 24]),
            "note": "重点背定义、载流子来源和温度升高导电能力增强。",
        },
        {
            "id": "essential-impurity-semiconductor",
            "chapter": "1",
            "title": "杂质半导体与多子少子",
            "prompt": "什么是杂质半导体？有哪些类型？多子、少子分别是谁？",
            "answer": "在本征半导体中掺入微量杂质后形成杂质半导体。掺五价元素形成 N 型半导体，多数载流子是自由电子，少数载流子是空穴；掺三价元素形成 P 型半导体，多数载流子是空穴，少数载流子是自由电子。多子数量主要由掺杂浓度决定，少子数量主要受温度影响。",
            "prerequisites": ["本征半导体", "自由电子、空穴和载流子的含义"],
            "source_pages": _gallery_sources("第1章 半导体器件讲义/第1章-半导体器件1.pdf", [25, 26, 27, 28]),
            "note": "考试常问 N 型/P 型谁是多子少子，要直接答清。",
        },
        {
            "id": "essential-pn-junction",
            "chapter": "1",
            "title": "PN 结",
            "prompt": "PN 结怎么形成？为什么单向导电？",
            "answer": "P 区和 N 区接触后，多子扩散形成空间电荷区和内电场；内电场阻碍扩散、促进少子漂移，最终达到动态平衡。正向偏置时势垒降低、PN 结变窄、多子扩散增强，电流大，表现为导通；反向偏置时势垒升高、PN 结变宽，只剩很小反向电流，表现为截止。",
            "prerequisites": ["P 型和 N 型半导体", "扩散运动与漂移运动", "正向/反向偏置极性"],
            "source_pages": _gallery_sources("第1章 半导体器件讲义/第1章-半导体器件1.pdf", [29, 30, 31, 33, 34]),
            "note": "重点是正偏导通、反偏截止和伏安特性。",
        },
        {
            "id": "essential-zener",
            "chapter": "1",
            "title": "稳压管与特性曲线",
            "prompt": "稳压管怎么工作？特性曲线怎么看？",
            "answer": "稳压二极管正常工作在反向击穿区。进入稳定区后，电流变化很大而两端电压变化很小，因此可用于稳压。读特性曲线时要找稳定电压 UZ、稳定电流范围、最大稳定电流 IZM 和动态电阻 rZ；rZ 越小，曲线越陡，稳压性能越好。使用时必须串限流电阻。",
            "prerequisites": ["PN 结伏安特性", "反向击穿不是普通损坏", "限流电阻作用"],
            "source_pages": _gallery_sources("第1章 半导体器件讲义/第1章-半导体器件2.pdf", [17, 18, 19]),
            "note": "稳压管反向工作，普通二极管通常正向使用。",
        },
        {
            "id": "essential-bjt-structure-regions",
            "chapter": "1",
            "title": "晶体管构成与放大/截止/饱和",
            "prompt": "晶体管怎么构成？什么时候放大、截止、饱和？",
            "answer": "双极型晶体管由两个 PN 结构成，有 NPN 和 PNP 两类，含发射区、基区、集电区，对应 E、B、C 三个电极。放大区：发射结正偏、集电结反偏，IC≈βIB；截止区：IB≈0，IC≈0，近似开关断开；饱和区：发射结和集电结都正偏，UCE 很小，近似开关闭合。模拟放大电路要求工作在放大区，数字电路常让晶体管工作在截止或饱和区。",
            "prerequisites": ["PN 结偏置", "NPN/PNP 电流方向", "β 电流放大系数"],
            "source_pages": _gallery_sources("第1章 半导体器件讲义/第1章-半导体器件34-.pdf", [3, 5, 10, 12, 18, 19, 20, 21, 22]),
            "note": "判断区间优先看两个结的偏置，再结合 IC 与 βIB。",
        },
        {
            "id": "essential-q-point-adjustment",
            "chapter": "2",
            "title": "Q 点不合适怎么调整",
            "prompt": "静态工作点 Q 点偏高或偏低怎么处理？",
            "answer": "Q 点应放在放大区中部，给输出信号留出上下摆动空间。Q 点过高容易进入饱和区，出现饱和失真；Q 点过低容易进入截止区，出现截止失真。固定偏置电路中可通过调整偏置电阻 RB、集电极电阻 RC 或电源 UCC 改变 IB、IC、UCE；分压式偏置电路中通过 RB1、RB2、RE 设置并稳定 Q 点。温度升高导致 IC 增大时，RE 的直流负反馈可抑制 Q 点漂移。",
            "prerequisites": ["输出特性曲线", "直流负载线", "截止失真和饱和失真"],
            "source_pages": _gallery_sources("第2章 基本放大电路/第2章-基本放大电路5.pdf", [23, 24, 25, 26, 27, 28, 29, 30])
            + _gallery_sources("第2章 基本放大电路/第2章-基本放大电路7.pdf", [5, 6, 7, 8, 9]),
            "note": "答题时要写清偏高/偏低对应失真方向和调参方向。",
        },
        {
            "id": "essential-static-analysis-q",
            "chapter": "2",
            "title": "放大电路静态分析求 Q 点",
            "prompt": "怎么做静态分析并求 Q 点？",
            "answer": "静态分析只看直流通路：电容开路、信号源置零，只保留直流电源和偏置电阻。固定偏置常用 IB≈(UCC-UBE)/RB，IC≈βIB，UCE=UCC-ICRC。分压式偏置先求 VB≈UCC·RB2/(RB1+RB2)，再求 IE≈(VB-UBE)/RE，IC≈IE，最后 UCE≈UCC-IC(RC+RE)。Q 点就是 IB、IC、UCE 或 IC、UCE 组成的静态工作位置。",
            "prerequisites": ["欧姆定律", "KVL", "电容直流开路", "UBE 近似值"],
            "source_pages": _gallery_sources("第2章 基本放大电路/第2章-基本放大电路5.pdf", [23])
            + _gallery_sources("第2章 基本放大电路/第2章-基本放大电路7.pdf", [9, 16, 17]),
            "note": "考试计算题必须先写直流通路，再代公式。",
        },
        {
            "id": "essential-dynamic-small-signal",
            "chapter": "2",
            "title": "动态分析与晶体管线性模型",
            "prompt": "动态分析时晶体管怎么线性化、怎么化简？",
            "answer": "动态分析只看交流通路：耦合电容和旁路电容按交流短路处理，直流电源作交流地。晶体管在 Q 点附近小信号工作，可把 B-E 间等效为 rbe，把 C-E 间等效为受控电流源 βib。共射基本公式常写为 Au=-β(RC//RL)/rbe，ri≈RB1//RB2//rbe，ro≈RC。若发射极电阻未被旁路，它引入交流负反馈，使电压增益绝对值下降、输入电阻增大。",
            "prerequisites": ["Q 点已在放大区", "电容交流短路", "电阻串并联"],
            "source_pages": _gallery_sources("第1章 半导体器件讲义/第1章-半导体器件34-.pdf", [35, 36, 37, 38])
            + _gallery_sources("第2章 基本放大电路/第2章-基本放大电路6.pdf", [6, 8, 12])
            + _gallery_sources("第2章 基本放大电路/第2章-基本放大电路7.pdf", [10, 11, 15, 18]),
            "note": "公式和算式按论文式分步写，不把所有推导挤成一行。",
        },
        {
            "id": "essential-differential-amplifier",
            "chapter": "2",
            "title": "差分放大电路",
            "prompt": "差分电路主要看什么？",
            "answer": "差分放大电路的核心作用是放大差模信号、抑制共模信号和零点漂移。理想对称时，两管静态工作点相同；温度引起的同向漂移在双端输出中相互抵消。复习时抓住四个词：对称、差模、共模、共模抑制比。若考计算，常围绕静态值、差模放大倍数和 CMRR。",
            "prerequisites": ["多级直接耦合", "零点漂移", "共模/差模信号分解"],
            "source_pages": _gallery_sources("第2章 基本放大电路/第2章-基本放大电路10.pdf", [1, 4, 6, 7, 8, 9, 10, 11, 15, 19, 20]),
            "note": "如果考试只要求了解，能解释抑制零漂和共模即可。",
        },
        {
            "id": "essential-power-amplifier",
            "chapter": "2",
            "title": "功率放大与甲乙类",
            "prompt": "功率放大电路有什么要求？甲类、乙类、甲乙类区别是什么？",
            "answer": "功率放大电路作为输出级，用来向负载提供足够功率，要求输出功率大、效率高、失真小、器件安全。甲类：整个周期导通，失真小但效率低；乙类：半个周期导通，效率高但有交越失真；甲乙类：导通时间大于半个周期，静态电流很小，兼顾效率并减小交越失真，互补功放常用。克服交越失真通常给两管加适当偏置，使其工作在甲乙类。",
            "prerequisites": ["晶体管导通角", "交越失真", "互补对称输出级"],
            "source_pages": _gallery_sources("第2章 基本放大电路/第2章-基本放大电路10.pdf", [26, 27, 28, 31, 32, 37, 38]),
            "note": "重点背甲/乙/甲乙类的导通时间、效率和失真特征。",
        },
        {
            "id": "essential-fet",
            "chapter": "1",
            "title": "场效应管了解",
            "prompt": "场效应管需要了解什么？",
            "answer": "场效应管是电压控制器件，输入电阻高，基本不需要信号源提供输入电流，温度稳定性较好。与双极型晶体管相比，BJT 是电流控制器件，FET 是电压控制器件；BJT 有 NPN/PNP，FET 常看 N 沟道/P 沟道；对应电极可粗略记为 B-G、E-S、C-D。",
            "prerequisites": ["晶体管电流控制概念", "输入电阻含义"],
            "source_pages": _gallery_sources("第1章 半导体器件讲义/第1章-半导体器件34-.pdf", [40, 55]),
            "note": "这里只按了解处理，不进入第 2 章 2.6 场效应管放大电路计算。",
        },
        {
            "id": "essential-opamp-ideal",
            "chapter": "3",
            "title": "集成运放理想假设、虚短、虚断",
            "prompt": "理想运放假设有哪些？什么时候用虚短和虚断？",
            "answer": "理想运放常用假设：开环电压放大倍数 Auo→∞，输入电阻 rid→∞，输出电阻 ro→0，共模抑制比 KCMR→∞，带宽无限，失调和噪声忽略。线性区且有负反馈时可用虚短 u+=u- 和虚断 i+=i-=0；非线性比较器中仍有虚断，但没有虚短，输出只取正/负饱和值。",
            "prerequisites": ["运放输入端正负号", "线性区和饱和区", "负反馈条件"],
            "source_pages": _gallery_sources("第3章 集成运算放大电路/第3章  集成运算放大电路11.pdf", [11, 12, 13, 14, 16]),
            "note": "虚短不是物理短路，虚断不是反馈支路断开。",
        },
        {
            "id": "essential-signal-opamp",
            "chapter": "3",
            "title": "信号运放",
            "prompt": "运放在线性信号运算中怎么答？",
            "answer": "信号运算类运放通常工作在线性区，靠深度负反馈让输出主要由外接电阻、电容决定。常见类型包括反相比例、同相比例、加法、减法、积分、微分。答题套路是先写虚短虚断，再在关键节点列 KCL，最后整理输出与输入的关系。若题目只要求简单掌握，重点会识别电路类型和写出基础输入输出关系。",
            "prerequisites": ["虚短虚断", "节点电流法", "反相端虚地"],
            "source_pages": _gallery_sources("第3章 集成运算放大电路/第3章  集成运算放大电路11.pdf", [17, 18, 19, 21, 22, 24, 28])
            + _gallery_sources("第3章 集成运算放大电路/第3章  集成运算放大电路12.pdf", [2, 7, 12, 15, 18]),
            "note": "你说反馈不考运算，所以反馈章不额外展开闭环增益计算。",
        },
        {
            "id": "essential-voltage-comparator",
            "chapter": "3",
            "title": "电压比较器与区间比较",
            "prompt": "电压比较器、区间/窗口比较器怎么判断？",
            "answer": "电压比较器把模拟输入与参考电压比较，输出跳到正饱和或负饱和，是模拟输入、数字输出的接口。基本比较器看 u+ 和 u- 谁大：u+>u- 时输出正饱和，u+<u- 时输出负饱和。单限比较器只有一个门限；滞回比较器引入正反馈，有上、下两个门限，抗干扰更强；区间/窗口比较器本质是两个门限组合，用来判断输入是否落在某一区间内。",
            "prerequisites": ["理想运放非线性区", "参考电压", "正/负饱和值"],
            "source_pages": _gallery_sources("第3章 集成运算放大电路/第3章  集成运算放大电路12.pdf", [20, 21, 22, 23, 24, 26, 27, 32, 33, 35, 36, 40]),
            "note": "比较器没有虚短；画波形时先找门限再看输入穿越时刻。",
        },
        {
            "id": "essential-feedback-types",
            "chapter": "4",
            "title": "负反馈四种类型与特点",
            "prompt": "负反馈四种类型是什么？各有什么特点？",
            "answer": "四种基本负反馈是电压串联、电压并联、电流串联、电流并联。电压反馈取样输出电压，能稳定输出电压并降低输出电阻；电流反馈取样输出电流，能稳定输出电流并提高输出电阻。串联混合使输入电阻增大；并联混合使输入电阻减小。组合起来：电压串联提高输入电阻、降低输出电阻；电压并联降低输入电阻、降低输出电阻；电流串联提高输入电阻、提高输出电阻；电流并联降低输入电阻、提高输出电阻。",
            "prerequisites": ["反馈取样点", "输入混合方式", "输入/输出电阻含义"],
            "source_pages": _gallery_sources("第4章  电子电路中的反馈.ppt", [9, 10, 11, 12, 13, 14, 15, 16, 17, 31, 32, 33]),
            "note": "你明确说负反馈不考运算，所以这里只背类型、判别和特点。",
        },
        {
            "id": "essential-instant-feedback",
            "chapter": "4",
            "title": "瞬时极性法判断负反馈",
            "prompt": "怎么用瞬时极性法判断负反馈？",
            "answer": "瞬时极性法先假设输入端某点瞬时增大，沿基本放大电路推出输出瞬时极性，再沿反馈网络把反馈信号送回输入端。如果反馈信号削弱原输入净作用，就是负反馈；如果增强原输入净作用，就是正反馈。操作时要区分是串联混合还是并联混合：串联看输入电压差是否被削弱，并联看输入电流差是否被削弱。",
            "prerequisites": ["放大器反相/同相关系", "反馈回路路径", "串联/并联混合"],
            "source_pages": _gallery_sources("第4章  电子电路中的反馈.ppt", [6, 7, 18, 19, 20, 34, 35, 36, 37, 38, 39, 40, 41]),
            "note": "考试题通常让你标 + / - 并写出反馈类型。",
        },
        {
            "id": "essential-positive-feedback-oscillator",
            "chapter": "4",
            "title": "正反馈与 RC 正弦波振荡",
            "prompt": "正反馈、RC 正弦波振荡的质量和原理怎么答？",
            "answer": "正反馈会增强输入净作用，满足条件时可产生振荡。正弦波振荡器由放大电路、正反馈网络、选频网络和稳幅环节组成。自激振荡条件是幅值条件 |AF|=1、相位条件 φA+φF=2nπ；起振时通常要求 |AF|>1，稳定后靠稳幅环节回到 |AF|=1。RC 文氏桥振荡中，RC 串并联网络选出特定频率，常见振荡频率为 f0=1/(2πRC)，输出波形质量取决于选频和稳幅是否合适。",
            "prerequisites": ["正反馈概念", "选频网络", "幅值条件和相位条件"],
            "source_pages": _gallery_sources("第4章  电子电路中的反馈.ppt", [42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56]),
            "note": "你写的 RS 我按讲义中的 RC 正弦波/文氏桥振荡处理。",
        },
        {
            "id": "essential-dc-power-supply-blocks",
            "chapter": "5",
            "title": "直流稳压电源几部分",
            "prompt": "直流稳压电源由几部分组成？每部分做什么？",
            "answer": "小功率直流稳压电源通常由变压、整流、滤波、稳压四部分组成。变压把交流电压变成合适大小；整流把交流变成脉动直流；滤波利用电容或电感的储能特性减小脉动；稳压在电网、负载或温度变化时保持输出电压基本稳定。",
            "prerequisites": ["交流有效值", "二极管单向导电", "电容电压不能突变"],
            "source_pages": _gallery_sources("第5章-直流稳压电源.pdf", [1, 2, 3, 4, 37, 38]),
            "note": "这是第 5 章总框架，考试很容易问组成和作用。",
        },
        {
            "id": "essential-rectifier-filter",
            "chapter": "5",
            "title": "整流与滤波",
            "prompt": "单相半波、桥式整流和滤波分别看什么？",
            "answer": "整流靠二极管单向导电。单相半波只利用一个半周，平均输出较小，常用 UO=0.45U2；单相桥式正、负半周都利用，常用 UO=0.9U2。电容滤波与负载并联，充电快、放电慢，使输出更平滑；桥式/全波电容滤波常近似 UO≈1.2U2，半波电容滤波常近似 UO≈1.0U2。复习时重点会看单相半波、单相桥式和电容滤波，三相整流按不考处理。",
            "prerequisites": ["PN 结单向导电", "有效值与峰值", "电容充放电"],
            "source_pages": _gallery_sources("第5章-直流稳压电源.pdf", [4, 5, 6, 9, 10, 13, 14, 15, 23, 24, 25, 26, 28, 29, 30, 31, 32, 36]),
            "note": "半波、桥式两个整流图可以按你说的抄纸上。",
        },
        {
            "id": "essential-stabilizer",
            "chapter": "5",
            "title": "稳压电路只用看",
            "prompt": "稳压电路要看哪些？",
            "answer": "稳压电路用于保持输出电压基本不随电网、负载和温度变化。稳压管稳压电路结构简单，输出约为 UZ，但输出电流小、不可调，适合小电流固定电压场合；串联型稳压电路由调整元件、比较放大、基准电压和采样环节组成，靠调整管 UCE 自动变化使输出稳定。这里只要求看懂工作原理，不深入复杂计算。",
            "prerequisites": ["稳压二极管反向击穿稳压", "负反馈调节思想", "调整管串联概念"],
            "source_pages": _gallery_sources("第5章-直流稳压电源.pdf", [39, 40, 41, 42, 43, 44, 46, 47, 51, 63, 64]),
            "note": "开关稳压电源仍按原黑板范围不展开。",
        },
        {
            "id": "essential-boolean-laws",
            "chapter": "7",
            "title": "逻辑代数运算法则与化简公式",
            "prompt": "数电逻辑代数要背哪些？",
            "answer": "逻辑代数变量只取 0 和 1，常用规则包括自等律、0-1 律、重叠律、还原律、互补律、交换律、结合律、分配律、吸收律和反演律。化简时常从复杂一边出发，利用 A+A=A、A·A=A、A+A'=1、A·A'=0、A+A'B=A+B、A(A+B)=A 等公式，目标是减少变量和门电路数量。",
            "prerequisites": ["与、或、非基本逻辑", "真值表", "二值变量"],
            "source_pages": _gallery_sources("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", [1, 2, 3, 11, 14]),
            "note": "你说这部分较少，可以把核心公式抄到纸上。",
        },
        {
            "id": "essential-gate-symbols-ttl",
            "chapter": "7",
            "title": "门电路逻辑符号与 TTL 与非门",
            "prompt": "门电路逻辑符号和 TTL 与非门要看什么？",
            "answer": "基本门要会认符号、真值表、逻辑表达式和波形：与门有 0 出 0、全 1 出 1；或门有 1 出 1、全 0 出 0；与非门是与门后取反，有 0 出 1、全 1 出 0；异或是相异为 1。TTL 与非门要知道它是晶体管-晶体管逻辑门，常见指标有输出高/低电平、扇出系数和传输延迟，74LS00 是四个二输入与非门。",
            "prerequisites": ["高低电平表示 1/0", "基本逻辑关系", "晶体管开关状态"],
            "source_pages": _gallery_sources("第7章 门电路和组合逻辑电路/第7章-门电路和组合逻辑电路1.pdf", [16, 19, 21, 23, 26, 28, 29])
            + _gallery_sources("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路2.pdf", [1, 2, 7, 8, 9, 25]),
            "note": "按你要求以书上/讲义符号为准，不额外发散。",
        },
        {
            "id": "essential-kmap",
            "chapter": "7",
            "title": "卡诺图化简",
            "prompt": "卡诺图怎么化简？",
            "answer": "卡诺图把最小项按相邻规则排成方格，相邻格只改变一个变量。化简步骤：把输出为 1 的最小项填入图中；按 1、2、4、8 个相邻格圈组，圈尽量大、圈数尽量少，并允许边界相邻；每个圈保留不变变量，消去变化变量；最后把各圈对应的与项相加。无关项可用于扩大圈组，但不能为了使用无关项而漏掉必须覆盖的 1。",
            "prerequisites": ["最小项", "二进制相邻编码", "与或式"],
            "source_pages": _gallery_sources("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", [17, 18, 19, 20, 21, 22, 23, 24]),
            "note": "卡诺图页已经和作业 7.5.14 对应。",
        },
        {
            "id": "essential-combinational-design",
            "chapter": "7",
            "title": "组合逻辑电路分析与设计",
            "prompt": "组合逻辑题怎么做？",
            "answer": "分析题按逻辑图写输出表达式，再化简、列状态表、说明功能。设计题按文字要求列真值表，再写逻辑表达式、化简或变换形式，最后画逻辑图。用与非门实现时常把与或式变成与非-与非形式。",
            "prerequisites": ["真值表", "逻辑代数化简", "基本门电路"],
            "source_pages": _gallery_sources("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路4.pdf", [1, 2, 4, 12, 16]),
            "note": "实验做过的组合逻辑题要加强。",
        },
        {
            "id": "essential-138-153",
            "chapter": "7",
            "title": "74LS138 与 74LS153",
            "prompt": "138 和 153 重点看哪些？",
            "answer": "74LS138 是 3 线-8 线译码器，注意三个输入、八个低有效输出和使能端条件；可用译码输出提供最小项，再配合门电路实现逻辑函数，也可扩展成 4 线-16 线译码器。74LS153 是双 4 选 1 数据选择器，注意使能端、选择端 A1/A0、数据端 D0-D3 和输出表达式；实现逻辑函数时通常把一部分变量接到选择端，剩余变量接到数据端。复习重点是看懂功能表、引脚和实验中做过的实现方法。",
            "prerequisites": ["最小项", "译码器", "数据选择器", "使能端有效电平"],
            "source_pages": _gallery_sources("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路5.pdf", [88, 90, 91, 94, 95, 96, 106, 107, 108, 114, 115, 117]),
            "note": "这是实验加强项，功能表和接线逻辑要能快速看懂。",
        },
    ]


def build_exam_essential_page_lookup(essentials: list[dict] | None = None) -> dict[tuple[str, int], str]:
    if essentials is None:
        essentials = build_exam_essentials()
    lookup: dict[tuple[str, int], list[str]] = {}
    for item in essentials:
        for page in item.get("source_pages", []):
            key = (page.file.replace("\\", "/"), page.page)
            lookup.setdefault(key, []).append(item["title"])
    return {
        key: f"{EXAM_ESSENTIAL_REASON}：{'、'.join(sorted(set(titles)))}"
        for key, titles in lookup.items()
    }


def lecture_gallery_excluded_pages(file_key: str) -> set[int]:
    excluded: set[int] = set()
    for start, end in EXCLUDED_LECTURE_GALLERY_RANGES.get(file_key, []):
        excluded.update(range(start, end + 1))
    return excluded


def super_key_image_names() -> list[str]:
    focus_dir = config.SOURCE_ROOT / SUPER_KEY_DIR_NAME
    if not focus_dir.is_dir():
        candidates = [
            path
            for path in config.SOURCE_ROOT.iterdir()
            if path.is_dir() and len(list(path.glob("*.jpg"))) + len(list(path.glob("*.jpeg"))) >= 5
        ]
        focus_dir = max(candidates, key=lambda path: len(list(path.glob("*.jpg"))) + len(list(path.glob("*.jpeg"))), default=None)
    if focus_dir is None or not focus_dir.is_dir():
        return []
    return sorted(path.name for pattern in ("*.jpg", "*.jpeg") for path in focus_dir.glob(pattern))


def _matching_super_key_targets(file_key: str, available_images: set[str]) -> dict[int, list[str]]:
    matches: dict[int, list[str]] = {}
    for image_name, rules in SUPER_KEY_SOURCE_PAGE_RULES.items():
        if image_name not in available_images:
            continue
        for file_suffix, pages in rules:
            if file_key.endswith(file_suffix):
                for page in pages:
                    matches.setdefault(page, []).append(image_name)
    return matches


def build_super_key_source_page_lookup(available_images: list[str] | None = None) -> dict[tuple[str, int], str]:
    image_names = set(available_images if available_images is not None else super_key_image_names())
    super_key_pages: dict[tuple[str, int], str] = {}
    for files in config.SOURCE_FILES.values():
        for path in files:
            if path.suffix.lower() != ".pdf":
                continue
            file_key = _source_file_key(path)
            excluded_pages = lecture_gallery_excluded_pages(file_key)
            matched_pages = _matching_super_key_targets(file_key, image_names)
            for page, matched_images in matched_pages.items():
                if page in excluded_pages:
                    continue
                super_key_pages[(file_key, page)] = f"{SUPER_KEY_REASON_PREFIX}\uff1a{'、'.join(sorted(set(matched_images)))}"
    return super_key_pages


def build_key_source_page_lookup(
    knowledge_points: list[KnowledgePoint] | None = None,
    questions: list[Question] | None = None,
) -> dict[tuple[str, int], str]:
    if knowledge_points is None:
        knowledge_points = build_knowledge_points()
    if questions is None:
        questions = build_questions()
    direct_pages = {
        (page.file.replace("\\", "/"), page.page)
        for point in knowledge_points
        for page in point.source_pages
    } | {
        (page.file.replace("\\", "/"), page.page)
        for question in questions
        for page in question.source_pages
    }
    key_pages: dict[tuple[str, int], str] = {}
    for file_key, page in direct_pages:
        for neighbor in range(page - 1, page + 2):
            if neighbor > 0:
                key_pages.setdefault((file_key, neighbor), "题目相关相邻讲解页")
        key_pages[(file_key, page)] = "题目/知识点直接来源页"
    return key_pages


def build_lecture_gallery(
    knowledge_points: list[KnowledgePoint] | None = None,
    questions: list[Question] | None = None,
    exam_essentials: list[dict] | None = None,
) -> list[dict]:
    gallery = []
    key_source_pages = build_key_source_page_lookup(knowledge_points, questions)
    super_key_source_pages = build_super_key_source_page_lookup()
    exam_essential_pages = build_exam_essential_page_lookup(exam_essentials)
    for files in config.SOURCE_FILES.values():
        for path in files:
            file_key = _source_file_key(path)
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                doc = fitz.open(str(path))
                page_count = doc.page_count
                doc.close()
                image_name = _gallery_image_name
            elif suffix in {".ppt", ".pptx"}:
                page_count = _office_page_count(path)
                image_name = _ppt_gallery_image_name
            else:
                continue
            if page_count <= 0:
                continue
            excluded_pages = lecture_gallery_excluded_pages(file_key)
            pages = [page for page in range(1, page_count + 1) if page not in excluded_pages]
            chapter = path.name.split("章", 1)[0].replace("第", "")
            gallery.append(
                {
                    "file": file_key,
                    "title": path.name,
                    "chapter": chapter,
                    "pages": [
                        {
                            "page": page,
                            "image_path": image_name(file_key, page),
                            "anchor_id": f"lecture-page-{len(gallery)}-{page}",
                            "is_key_page": (file_key, page) in key_source_pages or (file_key, page) in super_key_source_pages,
                            "key_reason": key_source_pages.get((file_key, page)),
                            "is_super_key_page": (file_key, page) in super_key_source_pages,
                            "super_key_reason": super_key_source_pages.get((file_key, page)),
                            "is_exam_essential_page": (file_key, page) in exam_essential_pages,
                            "exam_essential_reason": exam_essential_pages.get((file_key, page)),
                        }
                        for page in pages
                    ],
                }
            )
    return gallery


def build_knowledge_points() -> list[KnowledgePoint]:
    return [
        KnowledgePoint(
            id="semiconductor_pn_junction",
            chapter="1",
            title="PN结单向导电性",
            summary="PN结正向导通、反向截止，是二极管和晶体管理解的起点。",
            must_know="会判断二极管导通/截止方向，理解伏安特性和反向击穿。",
            intuition="正向电压降低势垒，载流子容易通过；反向电压抬高势垒，电流近似为零。",
            prerequisites=["电流方向与电压极性", "导体、绝缘体和半导体的区别"],
            formulas=[],
            source_pages=[_source("第1章 半导体器件讲义/第1章-半导体器件1.pdf", 29, "assets/course_pages/ch1_p029.png")],
            related_questions=["1.x"],
            pitfalls=["不要把稳压二极管的反向击穿工作状态当成普通二极管损坏。"],
        ),
        KnowledgePoint(
            id="bjt_static_operating_point",
            chapter="2",
            title="共射放大电路静态工作点",
            summary="静态工作点决定三极管是否在线性放大区。",
            must_know="会列直流通路并计算 IB、IC、UCE。",
            intuition="没有交流信号时先把电路停在一个合适位置，交流信号才有上下摆动空间。",
            prerequisites=["PN结和三极管电流关系", "欧姆定律", "基尔霍夫电压定律"],
            formulas=["IB = (UCC - UBE) / RB", "IC = βIB", "UCE = UCC - ICRC"],
            source_pages=[_source("第2章 基本放大电路/第2章-基本放大电路5.pdf", 23, "assets/course_pages/ch2_p023.png")],
            related_questions=["2.4.5"],
            pitfalls=["计算静态量时电容开路，不能把交流负载直接代入直流通路。"],
        ),
        KnowledgePoint(
            id="bjt_small_signal_model",
            chapter="2",
            title="微变等效电路法",
            summary="把三极管在小信号范围内等效成线性受控源模型。",
            must_know="会画交流通路、微变等效电路，并计算 Au、ri、ro。",
            intuition="先固定静态点，再只观察附近很小的交流变化。",
            prerequisites=["静态工作点", "电容交流短路近似", "电阻串并联等效"],
            formulas=["Au = -β(RC // RL) / rbe", "ri = RB1 // RB2 // rbe", "ro ≈ RC"],
            source_pages=[_source("第2章 基本放大电路/第2章-基本放大电路6.pdf", 4, "assets/course_pages/ch2_p004.png")],
            related_questions=["2.4.5", "2.4.7"],
            pitfalls=["带负载和空载增益不同，不能漏掉 RC // RL。"],
        ),
        KnowledgePoint(
            id="ideal_op_amp_rules",
            chapter="3",
            title="理想运放虚短虚断",
            summary="线性负反馈下，理想运放满足虚短和虚断。",
            must_know="会用 u+ = u-、i+ = i- = 0 推导比例、加法、减法运算关系。",
            intuition="运放输出会自动调节，让两个输入端电压几乎相等，但输入端几乎不取电流。",
            prerequisites=["节点电流法", "负反馈的线性工作条件", "电阻分压和反相比例关系"],
            formulas=["u+ = u-", "i+ = i- = 0"],
            source_pages=[_source("第3章 集成运算放大电路/第3章  集成运算放大电路11.pdf", 11, "assets/course_pages/ch3_p011.png")],
            related_questions=["3.2.8", "3.2.13", "3.2.16"],
            pitfalls=["虚短不是输入端真的短接，虚断不是反馈支路断开。"],
        ),
        KnowledgePoint(
            id="negative_feedback_type",
            chapter="4",
            title="负反馈类型判断",
            summary="反馈类型由输出取样方式和输入混合方式决定。",
            must_know="会判断电压/电流反馈、串联/并联反馈，并说明对输入输出电阻的影响。",
            intuition="看反馈从输出端取电压还是取电流，再看回到输入端是串进去还是并进去。",
            prerequisites=["放大电路输入端和输出端定义", "输入电阻和输出电阻含义", "正反馈与负反馈判别"],
            formulas=[],
            source_pages=[_source("第4章  电子电路中的反馈.ppt", 1, "assets/course_pages/ch4_slide001.png")],
            related_questions=["4.2.6", "4.2.12"],
            pitfalls=["不要只看反馈线位置，要看取样量和混合方式。"],
        ),
        KnowledgePoint(
            id="rectifier_bridge",
            chapter="5",
            title="单相桥式整流",
            summary="桥式整流让交流正负半周都以同一方向流过负载。",
            must_know="会计算输出平均电压、平均电流、二极管最大反向电压和二次电流。",
            intuition="四个二极管轮流导通，把负半周翻到正方向。",
            prerequisites=["二极管单向导电性", "正弦交流电有效值与峰值", "负载电阻欧姆定律"],
            formulas=["UO = 0.9U2", "IO = UO / RL", "URM = √2U2"],
            source_pages=[_source("第5章-直流稳压电源.pdf", 9, "assets/course_pages/ch5_p009.png")],
            related_questions=["5.1.8"],
            pitfalls=["题目给的是有效值 U2，输出平均值不是 U2。"],
        ),
        KnowledgePoint(
            id="boolean_simplification",
            chapter="7",
            title="逻辑代数与卡诺图化简",
            summary="用逻辑代数或卡诺图把逻辑函数化到便于实现的形式。",
            must_know="会代数化简、卡诺图圈组、转换成与非门实现。",
            intuition="化简的目标是减少门电路数量和输入端数量。",
            prerequisites=["与或非基本逻辑", "真值表", "二进制变量只有 0 和 1"],
            formulas=["A + A = A", "A·A = A", "A + A'B = A + B"],
            source_pages=[_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", 11, "assets/course_pages/ch7_p011.png")],
            related_questions=["7.5.9", "7.5.13", "7.5.14"],
            pitfalls=["卡诺图圈组必须按 1、2、4、8 个相邻格，边界可相邻。"],
        ),
        KnowledgePoint(
            id="combinational_logic_design",
            chapter="7",
            title="组合逻辑电路设计",
            summary="从逻辑功能要求出发列真值表、写表达式、化简并画逻辑图。",
            must_know="会把文字条件转换成输入输出逻辑关系。",
            intuition="先把题目翻译成真值表，再选择合适门电路实现。",
            prerequisites=["逻辑函数表示方法", "真值表到表达式", "逻辑代数化简"],
            formulas=[],
            source_pages=[_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路4.pdf", 12, "assets/course_pages/ch7_p012.png")],
            related_questions=["7.6.17"],
            pitfalls=["优先级题要先给最高优先级输出，再排除更高优先级后给低优先级输出。"],
        ),
    ]


def build_questions() -> list[Question]:
    return [
        _pending_question(
            "1.3.6",
            "1",
            "二极管削波电路波形判断",
            "在图 1.08 所示各电路中，已知 U=5V、ui=10sinωt V，二极管正向压降忽略不计，分别画出输出电压 uo 的波形。",
            ["assets/homework_images/1,半导体器件作业_image1.png", "assets/homework_images/1,半导体器件作业_image2.png"],
            ["semiconductor_pn_junction"],
            [_source("第1章 半导体器件讲义/第1章-半导体器件2.pdf", 9, "assets/course_pages/ch1_p009.png")],
            ["先判断每个半周二极管是否导通。", "导通时按理想二极管短路处理。", "截止时按开路处理。", "把被限制的电压区间画成输出波形。"],
        ),
        _pending_question(
            "1.3.9",
            "1",
            "二极管逻辑/限幅电路分析",
            "在图 1.11 所示电路中，根据输入 VA、VB 的组合判断输出 VY 的大小。",
            ["assets/homework_images/1,半导体器件作业_image3.png", "assets/homework_images/1,半导体器件作业_image4.png"],
            ["semiconductor_pn_junction"],
            [_source("第1章 半导体器件讲义/第1章-半导体器件2.pdf", 9, "assets/course_pages/ch1_p009.png")],
            ["分别假设二极管导通/截止。", "用节点电压验证假设是否自洽。", "输出取由导通支路钳位后的电压。"],
        ),
        _pending_question(
            "1.4.3",
            "1",
            "稳压二极管稳压电路计算",
            "在图 1.13 中，已知电源、电阻和稳压管参数，求稳压电路工作状态和相关电流/电压。",
            ["assets/homework_images/1,半导体器件作业_image5.png", "assets/homework_images/1,半导体器件作业_image6.png"],
            ["semiconductor_pn_junction"],
            [_source("第1章 半导体器件讲义/第1章-半导体器件2.pdf", 17, "assets/course_pages/ch1_p017.png")],
            ["先判断稳压管是否处于反向击穿稳压区。", "列限流电阻电流。", "由负载电流和稳压管电流关系判断是否满足稳压条件。"],
        ),
        _pending_question(
            "1.5.8",
            "1",
            "晶体管安全工作区判断",
            "某晶体管给定 PCM、ICM、U(BR)CEO，判断不同 UCE、IC 组合下能否正常工作。",
            ["assets/homework_images/1,半导体器件作业_image7.png"],
            ["semiconductor_pn_junction"],
            [_source("第1章 半导体器件讲义/第1章-半导体器件34-.pdf", 27, "assets/course_pages/ch1_p027.png")],
            ["检查集电极电流是否超过 ICM。", "检查管压降是否超过击穿电压。", "计算 PCM = UCE·IC 是否超过最大耗散功率。"],
        ),
        _pending_question(
            "1.5.9",
            "1",
            "晶体管工作状态判断",
            "判断图 1.14 中各晶体管处于截止、放大或饱和状态。",
            ["assets/homework_images/1,半导体器件作业_image7.png"],
            ["semiconductor_pn_junction"],
            [_source("第1章 半导体器件讲义/第1章-半导体器件34-.pdf", 15, "assets/course_pages/ch1_p015.png")],
            ["先看基极-发射极是否正向偏置。", "若导通，估算基极电流和可能的集电极电流。", "比较负载允许的集电极电流判断放大或饱和。"],
        ),
        _pending_question(
            "2.2.5",
            "2",
            "固定偏置共射放大电路静态分析",
            "图 2.01 固定偏置晶体管放大电路中，已知 UCC、RC、RB 和 β，估算静态值；再结合输出特性曲线用图解法求静态工作点，并求静态时 C1、C2 上的电压和极性。",
            ["assets/homework_images/2,基本放大电路作业_image1.png"],
            ["bjt_static_operating_point"],
            [_source("第2章 基本放大电路/第2章-基本放大电路5.pdf", 23, "assets/course_pages/ch2_p023.png")],
            ["先画直流通路，耦合电容视为开路。", "由 RB 和 UCC 估算 IB，再用 βIB 估算 IC。", "用 UCE=UCC-ICRC 求管压降。", "在输出特性曲线上叠加载直线校核静态工作点。", "静态时电容两端电压由两侧直流电位差决定。"],
        ),
        _pending_question(
            "2.3.4",
            "2",
            "固定偏置放大电路电压放大倍数",
            "利用微变等效电路计算题 2.2.5 放大电路的电压放大倍数 Au，分别讨论输出端开路和接入 RL=6kΩ、rbe=0.8kΩ 时的情况。",
            ["assets/homework_images/2,基本放大电路作业_image1.png", "assets/homework_images/2,基本放大电路作业_image2.png"],
            ["bjt_small_signal_model"],
            [_source("第2章 基本放大电路/第2章-基本放大电路6.pdf", 4, "assets/course_pages/ch2_p004.png")],
            ["把三极管替换为 rbe 与 βib 微变模型。", "输出端开路时负载为 RC。", "接入 RL 后使用 RC // RL。", "共射极电路输出反相，注意 Au 的符号。"],
        ),
        _pending_question(
            "2.3.5",
            "2",
            "共射放大电路输入输出电压与负载影响",
            "图 2.01(a) 电路中已知 UCC、RC、rbe 和 β；根据测得静态值判断管子工作状态，计算输出端开路时的电压放大倍数，并在 ui 有效值为 1mV 时求空载和 RL=6kΩ 时的输出电压。",
            ["assets/homework_images/2,基本放大电路作业_image1.png", "assets/homework_images/2,基本放大电路作业_image2.png"],
            ["bjt_static_operating_point", "bjt_small_signal_model"],
            [_source("第2章 基本放大电路/第2章-基本放大电路6.pdf", 4, "assets/course_pages/ch2_p004.png")],
            ["先由 UCE 和输出特性判断是否位于放大区。", "空载时用 RC 计算电压放大倍数。", "有负载时把 RC 换为 RC // RL。", "输出电压有效值等于输入有效值乘以放大倍数的绝对值。"],
        ),
        Question(
            id="2.4.5",
            chapter="2",
            title="分压式偏置放大电路综合计算",
            prompt="计算静态值，画微变等效电路，计算 Au、ri、ro，并分析负载影响。",
            image_paths=["assets/homework_images/2,基本放大电路作业_image3.png"],
            knowledge_ids=["bjt_static_operating_point", "bjt_small_signal_model"],
            source_pages=[_source("第2章 基本放大电路/第2章-基本放大电路7.pdf", 5, "assets/course_pages/ch2_p005.png")],
            subquestions=[
                SubQuestion("2.4.5(1)", "计算静态值 IB、IC、UCE。", "待接入官方答案或推导。", ["列直流通路。", "用分压偏置估算法求基极电位。", "求 IE、IC、IB 和 UCE。"]),
                SubQuestion("2.4.5(2)", "画出微变等效电路。", "待接入官方答案或推导。", ["交流分析中电容视为短路。", "电源端为交流地。", "三极管替换为 rbe 与 βib 受控源模型。"]),
                SubQuestion("2.4.5(3)", "计算 Au、ri、ro。", "待接入官方答案或推导。", ["使用 RC // RL。", "输入电阻考虑偏置电阻并联。", "输出电阻近似为 RC。"]),
                SubQuestion("2.4.5(4)", "计算输出端开路时电压放大倍数并说明 RL 影响。", "待接入官方答案或推导。", ["开路时去掉 RL。", "比较 RC 与 RC // RL。"]),
            ],
            answer_source="待核对",
        ),
        Question(
            id="2.4.6",
            chapter="2",
            title="信号源内阻对电压放大倍数的影响",
            prompt="在 2.4.5 中设 RS=1kΩ，计算输出端接有负载时的电压放大倍数，并说明信号源内阻 RS 的影响。",
            image_paths=["assets/homework_images/2,基本放大电路作业_image3.png"],
            knowledge_ids=["bjt_small_signal_model"],
            source_pages=[_source("第2章 基本放大电路/第2章-基本放大电路6.pdf", 4, "assets/course_pages/ch2_p004.png")],
            subquestions=[
                SubQuestion("2.4.6", "计算考虑 RS 后的整体电压放大倍数。", "待接入官方答案或推导。", ["先沿用 2.4.5 的输入电阻 ri。", "信号源内阻与 ri 构成分压。", "整体增益等于输入分压系数乘以放大电路本身增益。"]),
            ],
            answer_source="待核对",
        ),
        Question(
            id="2.4.7",
            chapter="2",
            title="去掉发射极旁路电容后的动态分析",
            prompt="在 2.4.5 电路中去掉发射极交流旁路电容 CE，判断静态值变化并计算 Au、ri、ro。",
            image_paths=["assets/homework_images/2,基本放大电路作业_image3.png"],
            knowledge_ids=["bjt_static_operating_point", "bjt_small_signal_model"],
            source_pages=[_source("第2章 基本放大电路/第2章-基本放大电路7.pdf", 5, "assets/course_pages/ch2_p005.png")],
            subquestions=[
                SubQuestion("2.4.7(1)", "判断静态值是否变化。", "静态值不因去掉交流旁路电容而改变。", ["静态分析中电容本来视为开路。", "CE 只影响交流通路，不改变直流偏置。"]),
                SubQuestion("2.4.7(2)", "画出微变等效电路。", "待接入官方答案或推导。", ["交流通路中 RE 不再被 CE 短路。", "发射极电阻进入微变等效电路。"]),
                SubQuestion("2.4.7(3)", "计算 Au、ri、ro 并说明 RE 的影响。", "待接入官方答案或推导。", ["RE 引入交流负反馈。", "电压增益绝对值下降。", "输入电阻增大，输出电阻近似仍主要由 RC 决定。"]),
            ],
            answer_source="待核对",
        ),
        _pending_question(
            "2.6.2",
            "2",
            "射极输出器动态指标计算",
            "在射极输出器中，已知 RS、RB1、RB2、RE、β、rbe，求 Au、ri、ro。",
            ["assets/homework_images/2,基本放大电路作业_image6.png"],
            ["bjt_small_signal_model"],
            [_source("第2章 基本放大电路/第2章-基本放大电路8.pdf", 1, "assets/course_pages/ch2_p001.png")],
            ["画出射极输出器交流等效电路。", "使用共集电极电路近似 Au≈1。", "计算输入电阻和输出电阻。"],
        ),
        _pending_question(
            "2.6.3",
            "2",
            "两级放大电路综合分析",
            "两级放大电路中，估算各级静态值，画微变等效电路并计算 Au1、Au2、Au、ri、ro。",
            ["assets/homework_images/2,基本放大电路作业_image7.png"],
            ["bjt_static_operating_point", "bjt_small_signal_model"],
            [_source("第2章 基本放大电路/第2章-基本放大电路10.pdf", 1, "assets/course_pages/ch2_p010_001.png")],
            ["先分级画直流通路。", "计算每一级静态工作点。", "第二级输入电阻作为第一级负载。", "总增益为各级增益乘积。"],
        ),
        _pending_question(
            "2.6.4",
            "2",
            "双输出端放大电路分析",
            "给定单管放大电路两个输出端，求两个电压放大倍数和两个输出电阻。",
            ["assets/homework_images/2,基本放大电路作业_image11.png"],
            ["bjt_small_signal_model"],
            [_source("第2章 基本放大电路/第2章-基本放大电路6.pdf", 4, "assets/course_pages/ch2_p004.png")],
            ["分别识别集电极输出和发射极输出。", "集电极输出反相，发射极输出同相。", "分别计算两个输出端看到的输出电阻。"],
        ),
        _pending_question(
            "3.1.2",
            "3",
            "电桥输出与电阻变化关系证明",
            "在图 3.08 电桥中，某桥臂电阻变化 ΔR，证明输出电压 uo 与非电量变化的关系。",
            ["assets/homework_images/3, 运算放大电路作业_image1.png"],
            ["ideal_op_amp_rules"],
            [_source("第3章 集成运算放大电路/第3章  集成运算放大电路11.pdf", 11, "assets/course_pages/ch3_p011.png")],
            ["先求电桥两个中点电位。", "对变化电阻使用近似展开。", "再利用运放输入输出关系得到 uo。"],
        ),
        _pending_question(
            "3.2.8",
            "3",
            "T 型反馈网络反相比例运算证明",
            "为获得较高电压放大倍数且避免高值 RF，证明图 3.10 电路的等效增益关系。",
            ["assets/homework_images/3, 运算放大电路作业_image3.png"],
            ["ideal_op_amp_rules"],
            [_source("第3章 集成运算放大电路/第3章  集成运算放大电路11.pdf", 18, "assets/course_pages/ch3_p018.png")],
            ["利用虚地确定输入电流。", "把 T 型网络等效成反馈电阻。", "推导输出与输入的比例关系。"],
        ),
        Question(
            id="3.2.13",
            chapter="3",
            title="运放多输入运算关系推导",
            prompt="求图示电路中 uo 与各输入电压的运算关系式。",
            image_paths=["assets/homework_images/3, 运算放大电路作业_image5.png"],
            knowledge_ids=["ideal_op_amp_rules"],
            source_pages=[_source("第3章 集成运算放大电路/第3章  集成运算放大电路12.pdf", 2, "assets/course_pages/ch3_p002.png")],
            subquestions=[
                SubQuestion("3.2.13", "求输出表达式。", "待接入官方答案或推导。", ["使用虚短虚断。", "对反相端或同相端列 KCL。", "整理 uo 与输入电压关系。"]),
            ],
            answer_source="待核对",
        ),
        _pending_question(
            "3.2.16",
            "3",
            "差动/仪用运放电路输出计算",
            "图 3.16 中已知 uI=uI1-uI2、R1、RP，求输出电压 uo。",
            ["assets/homework_images/3, 运算放大电路作业_image6.png"],
            ["ideal_op_amp_rules"],
            [_source("第3章 集成运算放大电路/第3章  集成运算放大电路12.pdf", 7, "assets/course_pages/ch3_p007.png")],
            ["识别两级运放结构。", "用虚短虚断分别求两级输出。", "把差模输入代入最终表达式。"],
        ),
        _pending_question(
            "3.2.21",
            "3",
            "积分运算电路输出关系",
            "图 3.19 积分运算电路中，试求 uo 与 uI1、uI2 的关系式。",
            ["assets/homework_images/3, 运算放大电路作业_image7.png"],
            ["ideal_op_amp_rules"],
            [_source("第3章 集成运算放大电路/第3章  集成运算放大电路12.pdf", 7, "assets/course_pages/ch3_p007.png")],
            ["使用虚短虚断确定输入端电位。", "对求和节点列 KCL。", "电容支路电流与输出电压导数相关。", "整理得到输出对输入信号积分的表达式。"],
        ),
        _pending_question(
            "3.3.4",
            "3",
            "电压比较器传输特性与波形",
            "在图 3.27 中，给定 UOM、稳压管参数、ui 和参考电压，画传输特性和输出波形。",
            ["assets/homework_images/3, 运算放大电路作业_image8.png"],
            ["ideal_op_amp_rules"],
            [_source("第3章 集成运算放大电路/第3章  集成运算放大电路12.pdf", 20, "assets/course_pages/ch3_p020.png")],
            ["比较 ui 与参考电压确定翻转点。", "根据限幅稳压管确定输出高低电平。", "把正弦输入超过阈值的区间映射到输出波形。"],
        ),
        _pending_question(
            "4.2.6",
            "4",
            "交流反馈类型判断",
            "判断图 (a) 和 (b) 两个两级放大电路中引入了何种类型的交流反馈。",
            ["assets/homework_images/4 电子电路中的负反馈作业_image1.png"],
            ["negative_feedback_type"],
            [_source("第4章  电子电路中的反馈.ppt", 1, "assets/course_pages/ch4_slide001.png")],
            ["先判断反馈信号从输出电压还是输出电流取样。", "再判断反馈回输入端是串联还是并联。", "最后判断反馈极性是否为负反馈。"],
        ),
        Question(
            id="4.2.12",
            chapter="4",
            title="按指标选择负反馈类型",
            prompt="为了实现指定输入输出电阻变化和稳定对象，判断应引入何种负反馈。",
            image_paths=["assets/homework_images/4 电子电路中的负反馈作业_image2.png"],
            knowledge_ids=["negative_feedback_type"],
            source_pages=[_source("第4章  电子电路中的反馈.ppt", 1, "assets/course_pages/ch4_slide001.png")],
            subquestions=[
                SubQuestion("4.2.12(1)", "减少输入电阻，增大输出电阻。", "应选择并联电流负反馈方向，待图确认接法。", ["减少输入电阻对应并联混合。", "增大输出电阻对应电流取样。"]),
                SubQuestion("4.2.12(2)", "稳定输出电压，判断输入电阻是否增大。", "应选择电压反馈；若为串联混合则输入电阻增大，具体接法待图确认。", ["稳定输出电压对应电压取样。", "输入电阻变化由串联或并联混合决定。"]),
                SubQuestion("4.2.12(3)", "稳定输出电流，并减小输入电阻。", "应选择并联电流负反馈，待图确认接法。", ["稳定输出电流对应电流取样。", "减小输入电阻对应并联混合。"]),
            ],
            answer_source="推导答案",
        ),
        Question(
            id="5.1.1",
            chapter="5",
            title="单相半波整流平均值与反向峰值",
            prompt="单相半波整流电路中，已知二次电压有效值 U=30V、负载电阻 RL=100Ω，求输出平均电压、电流及电源波动时二极管最高反向电压。",
            image_paths=["assets/homework_images/ch5_homework_page001.png"],
            knowledge_ids=["rectifier_bridge"],
            source_pages=[_source("第5章-直流稳压电源.pdf", 5, "assets/course_pages/ch5_p005.png")],
            subquestions=[
                SubQuestion("5.1.1(1)", "求输出电压和输出电流平均值。", "UO≈13.5V，IO≈0.135A。", ["半波整流平均输出 UO=0.45U。", "UO=0.45×30=13.5V。", "IO=UO/RL=13.5/100=0.135A。"]),
                SubQuestion("5.1.1(2)", "电源电压波动 +10% 时求最高反向电压。", "URM≈46.7V。", ["半波整流二极管最高反向电压约为 √2U。", "考虑 +10% 波动，Umax=33V。", "URM≈√2×33≈46.7V。"]),
            ],
            answer_source="AI兜底答案",
        ),
        Question(
            id="5.1.8",
            chapter="5",
            title="单相桥式整流参数计算",
            prompt="直流负载 110V、55Ω，采用单相桥式整流电路供电，求变压器二次电压、二次电流有效值并选用二极管。",
            image_paths=["assets/homework_images/ch5_homework_page001.png"],
            knowledge_ids=["rectifier_bridge"],
            source_pages=[_source("第5章-直流稳压电源.pdf", 9, "assets/course_pages/ch5_p009.png")],
            subquestions=[
                SubQuestion("5.1.8(1)", "求变压器二次电压有效值。", "U2 ≈ 122 V。", ["桥式整流无滤波时 UO = 0.9U2。", "U2 = 110 / 0.9 ≈ 122 V。"]),
                SubQuestion("5.1.8(2)", "求二次电流有效值。", "I2 ≈ 2.22 A。", ["负载电流 IO = 110 / 55 = 2 A。", "桥式整流中 I2 ≈ 1.11IO。", "I2 ≈ 2.22 A。"]),
                SubQuestion("5.1.8(3)", "选用二极管。", "二极管平均电流应大于 1 A，反向峰值电压应大于约 173 V，并留裕量。", ["每只二极管平均电流约为 IO / 2 = 1 A。", "URM = √2U2 ≈ 173 V。", "实际选型应留额定裕量。"]),
            ],
            answer_source="AI兜底答案",
        ),
        _ai_fallback_question(
            "7.2.5",
            "7",
            "控制门电路逻辑式与波形",
            "在图 (a) 门电路中，分别在 C=1 和 C=0 时求输出 Y 的逻辑式和波形，并说明功能。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章-门电路和组合逻辑电路1.pdf", 16, "assets/course_pages/ch7_p016.png")],
            "由图可得上支路为 (AC)'，下支路为 (BC')'，末级与非后 Y = AC + BC'。当 C=1 时，Y=A；当 C=0 时，Y=B，所以该电路等效为由 C 控制的二选一数据选择器。",
            ["先写出每一级门输出表达式。", "分别代入 C=1 和 C=0 化简。", "根据 A、B 波形逐段画 Y。"],
        ),
        _ai_fallback_question(
            "7.3.1",
            "7",
            "用 74LS00 与非门实现逻辑功能",
            "试用一片 74LS00 与非门实现指定逻辑关系。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image2.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路2.pdf", 1, "assets/course_pages/ch7_2_p001.png")],
            "74LS00 内含四个二输入与非门，可把目标函数先化为与非-与非形式。常用接法是用一个与非门作反相器：X' = (XX)'，再用其余与非门实现乘积项和末级合成；画图时按 1A/1B/1Y、2A/2B/2Y、3A/3B/3Y、4A/4B/4Y 分配引脚。",
            ["确认 74LS00 内含四个二输入与非门。", "把目标逻辑改写成与非-与非形式。", "分配芯片内四个门并画引脚连接。"],
        ),
        _ai_fallback_question(
            "7.5.9",
            "7",
            "与非门和非门实现逻辑关系",
            "用与非门和非门实现给定逻辑关系，并画出逻辑图。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", 11, "assets/course_pages/ch7_p011.png")],
            "AI兜底做法：先把题面给出的逻辑函数化成最简与或式 F = P1 + P2 + ...，再用双重否定改写为 F = ((P1)'(P2)'...)'。每个 (Pi)' 用与非门得到，末级再用与非门合成；若需要变量反相，则用非门或与非门输入并接得到。",
            ["先把逻辑式化简。", "用双重否定把表达式变成与非形式。", "需要反相时用与非门输入并接实现非门。"],
        ),
        _ai_fallback_question(
            "7.5.13",
            "7",
            "逻辑代数恒等式推证",
            "应用逻辑代数运算法则推证给定各式。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", 2, "assets/course_pages/ch7_3_p002.png")],
            "AI兜底做法：从较复杂一边开始，优先使用 A + A'B = A + B、A(A+B)=A、A+A=A、AA=A、A+A'=1、AA'=0 等恒等式逐步化简，直到得到另一边。每一步都应写出所用规则，不能只写最终等式。",
            ["从复杂一边出发。", "使用吸收律、互补律、分配律逐步化简。", "每一步写明使用的逻辑代数规则。"],
        ),
        Question(
            id="7.5.14",
            chapter="7",
            title="卡诺图化简",
            prompt="应用卡诺图化简给定逻辑函数。",
            image_paths=["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png", "assets/homework_images/7 门电路和组合逻辑电路作业_image2.png"],
            knowledge_ids=["boolean_simplification"],
            source_pages=[_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", 11, "assets/course_pages/ch7_p011.png")],
            subquestions=[
                SubQuestion("7.5.14(1)", "化简第一个逻辑式。", "AI兜底做法：把题面列出的最小项或真值表填入卡诺图，按 1、2、4、8 个相邻格优先圈最大圈，可利用边界相邻和无关项，最后写出每个圈对应的最简与项并相加。", ["把最小项填入卡诺图。", "按最大圈组覆盖所有 1。", "写出最简与或式。"]),
                SubQuestion("7.5.14(2)", "化简第二个逻辑式。", "AI兜底做法：同样先填卡诺图，再检查是否存在只改变一个变量的相邻格。圈组越大，保留下来的变量越少；最终答案应为覆盖所有 1 的最简与或式。", ["把最小项填入卡诺图。", "按最大圈组覆盖所有 1。", "写出最简与或式。"]),
            ],
            answer_source="AI兜底答案",
        ),
        _ai_fallback_question(
            "7.6.17a",
            "7",
            "列车优先通行组合逻辑设计",
            "特快、普快、普慢按优先级通行，同一时刻只能给一个开车信号，设计逻辑电路。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["combinational_logic_design"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路4.pdf", 12, "assets/course_pages/ch7_p012.png")],
            "设 A、B、C 分别表示特快、普快、普慢请求。按优先级输出：YA = A，YB = A'B，YC = A'B'C。这样同一时刻最多只有一个输出为 1，并且高优先级请求会屏蔽低优先级。",
            ["定义 A、B、C 为请求信号。", "最高优先级 YA=A。", "普快需在无特快时输出。", "普慢需在无特快且无普快时输出。"],
        ),
        _ai_fallback_question(
            "7.6.17b",
            "7",
            "8421BCD 码范围检测逻辑设计",
            "设 A、B、C、D 为 4 位 8421BCD 码，当数字 x<3 或 x>6 时输出 1，否则输出 0，用与非门组成逻辑图。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["combinational_logic_design", "boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路4.pdf", 12, "assets/course_pages/ch7_p012.png")],
            "若 A 为 8 位、B 为 4 位、C 为 2 位、D 为 1 位，则 x<3 对应 0000、0001、0010，x>6 对应 0111、1000、1001；10 到 15 可作无关项。卡诺图化简可得 Y = B'C' + B'D' + BCD。用与非门实现时写成 Y = ((B'C')'(B'D')'(BCD)')'。",
            ["列出 0 到 9 的 BCD 真值表。", "把 0、1、2、7、8、9 标为输出 1。", "10 到 15 可作为无关项。", "化简后转成与非门实现。"],
        ),
    ]


def seed_content() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    knowledge_points = build_knowledge_points()
    questions = _apply_official_answer_pages(build_questions())
    exam_essentials = build_exam_essentials()
    lecture_gallery = build_lecture_gallery(knowledge_points, questions, exam_essentials)
    manifest = {
        "course_pages": sorted(
            {page.image_path for point in knowledge_points for page in point.source_pages}
            | {page.image_path for question in questions for page in question.source_pages}
            | {page.image_path for item in exam_essentials for page in item["source_pages"]}
            | {page["image_path"] for source in lecture_gallery for page in source["pages"]}
        ),
        "official_answer_pages": sorted({page.image_path for question in questions for page in question.official_answer_pages}),
        "homework_images": sorted({path for question in questions for path in question.image_paths}),
        "lecture_gallery": lecture_gallery,
        "exam_essentials": [to_jsonable(item) for item in exam_essentials],
        "notes": [
            "Curated review records include all currently extracted homework IDs. Official answer PDF pages are attached for matched chapter exercises.",
            "Blackboard exclusions are enforced by content review and validation.",
        ],
    }

    config.KNOWLEDGE_MAP_JSON.write_text(
        json.dumps({"knowledge_points": [to_jsonable(point) for point in knowledge_points]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    config.QUESTION_BANK_JSON.write_text(
        json.dumps({"questions": [to_jsonable(question) for question in questions]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    config.SOURCE_MANIFEST_JSON.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def render_required_source_pages() -> None:
    from .extract_sources import convert_office_to_pdf, render_pdf_page

    known_files = {
        str(path.relative_to(config.SOURCE_ROOT)).replace("\\", "/"): path
        for files in config.SOURCE_FILES.values()
        for path in files
    }
    knowledge_points = build_knowledge_points()
    questions = build_questions()
    exam_essentials = build_exam_essentials()
    required_pages = [page for point in knowledge_points for page in point.source_pages]
    required_pages.extend(page for question in questions for page in question.source_pages)
    required_pages.extend(page for item in exam_essentials for page in item["source_pages"])
    for source in build_lecture_gallery(knowledge_points, questions, exam_essentials):
        required_pages.extend(_source(source["file"], page["page"], page["image_path"]) for page in source["pages"])
    rendered: set[str] = set()
    converted_office_pdfs: dict[str, Path] = {}
    for page in required_pages:
        source = known_files.get(page.file.replace("\\", "/"))
        if source is None or page.image_path in rendered:
            continue
        if source.suffix.lower() == ".pdf":
            render_pdf_page(source, page.page, config.PROJECT_ROOT / page.image_path)
            rendered.add(page.image_path)
            continue
        if source.suffix.lower() in {".ppt", ".pptx"}:
            source_key = source.resolve().as_posix()
            output_pdf = converted_office_pdfs.get(source_key)
            if output_pdf is None:
                output_pdf = _office_pdf_path(source)
                if output_pdf.is_file() or convert_office_to_pdf(source, output_pdf):
                    converted_office_pdfs[source_key] = output_pdf
            if output_pdf is not None and output_pdf.is_file():
                render_pdf_page(output_pdf, page.page, config.PROJECT_ROOT / page.image_path)
                rendered.add(page.image_path)


def render_required_homework_pages() -> None:
    from .extract_sources import convert_office_to_pdf, render_pdf_page

    ch5_homework = next((path for path in config.HOMEWORK_FILES if path.name.startswith("5 ")), None)
    if ch5_homework is None:
        return
    output_pdf = config.PROJECT_ROOT / "tmp" / "office_convert" / "ch5_homework.pdf"
    if convert_office_to_pdf(ch5_homework, output_pdf):
        render_pdf_page(output_pdf, 1, config.PROJECT_ROOT / "assets/homework_images/ch5_homework_page001.png")


def render_required_official_answer_pages() -> None:
    from .extract_sources import render_pdf_page

    answer_pdf = config.SOURCE_ROOT / OFFICIAL_ANSWER_FILE
    if not answer_pdf.is_file():
        return
    for page in sorted({page for pages in OFFICIAL_ANSWER_PAGE_LOOKUP.values() for page in pages}):
        render_pdf_page(answer_pdf, page, config.PROJECT_ROOT / _official_answer_image_name(page))
