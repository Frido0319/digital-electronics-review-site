from __future__ import annotations

import json

from . import config
from .models import KnowledgePoint, Question, SourcePage, SubQuestion, to_jsonable


def _source(file: str, page: int, image: str) -> SourcePage:
    return SourcePage(file=file, page=page, image_path=image)


def build_knowledge_points() -> list[KnowledgePoint]:
    return [
        KnowledgePoint(
            id="semiconductor_pn_junction",
            chapter="1",
            title="PN结单向导电性",
            summary="PN结正向导通、反向截止，是二极管和晶体管理解的起点。",
            must_know="会判断二极管导通/截止方向，理解伏安特性和反向击穿。",
            intuition="正向电压降低势垒，载流子容易通过；反向电压抬高势垒，电流近似为零。",
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
            formulas=[],
            source_pages=[_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路4.pdf", 12, "assets/course_pages/ch7_p012.png")],
            related_questions=["7.6.17"],
            pitfalls=["优先级题要先给最高优先级输出，再排除更高优先级后给低优先级输出。"],
        ),
    ]


def build_questions() -> list[Question]:
    return [
        Question(
            id="2.4.5",
            chapter="2",
            title="分压式偏置放大电路综合计算",
            prompt="计算静态值，画微变等效电路，计算 Au、ri、ro，并分析负载影响。",
            image_paths=["assets/homework_images/2_4_5_placeholder.png"],
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
            id="3.2.13",
            chapter="3",
            title="运放多输入运算关系推导",
            prompt="求图示电路中 uo 与各输入电压的运算关系式。",
            image_paths=["assets/homework_images/3_2_13_placeholder.png"],
            knowledge_ids=["ideal_op_amp_rules"],
            source_pages=[_source("第3章 集成运算放大电路/第3章  集成运算放大电路12.pdf", 2, "assets/course_pages/ch3_p002.png")],
            subquestions=[
                SubQuestion("3.2.13", "求输出表达式。", "待接入官方答案或推导。", ["使用虚短虚断。", "对反相端或同相端列 KCL。", "整理 uo 与输入电压关系。"]),
            ],
            answer_source="待核对",
        ),
        Question(
            id="4.2.12",
            chapter="4",
            title="按指标选择负反馈类型",
            prompt="为了实现指定输入输出电阻变化和稳定对象，判断应引入何种负反馈。",
            image_paths=["assets/homework_images/4_2_12_placeholder.png"],
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
            id="5.1.8",
            chapter="5",
            title="单相桥式整流参数计算",
            prompt="直流负载 110V、55Ω，采用单相桥式整流电路供电，求变压器二次电压、二次电流有效值并选用二极管。",
            image_paths=["assets/homework_images/5_1_8_placeholder.png"],
            knowledge_ids=["rectifier_bridge"],
            source_pages=[_source("第5章-直流稳压电源.pdf", 9, "assets/course_pages/ch5_p009.png")],
            subquestions=[
                SubQuestion("5.1.8(1)", "求变压器二次电压有效值。", "U2 ≈ 122 V。", ["桥式整流无滤波时 UO = 0.9U2。", "U2 = 110 / 0.9 ≈ 122 V。"]),
                SubQuestion("5.1.8(2)", "求二次电流有效值。", "I2 ≈ 2.22 A。", ["负载电流 IO = 110 / 55 = 2 A。", "桥式整流中 I2 ≈ 1.11IO。", "I2 ≈ 2.22 A。"]),
                SubQuestion("5.1.8(3)", "选用二极管。", "二极管平均电流应大于 1 A，反向峰值电压应大于约 173 V，并留裕量。", ["每只二极管平均电流约为 IO / 2 = 1 A。", "URM = √2U2 ≈ 173 V。", "实际选型应留额定裕量。"]),
            ],
            answer_source="推导答案",
        ),
        Question(
            id="7.5.14",
            chapter="7",
            title="卡诺图化简",
            prompt="应用卡诺图化简给定逻辑函数。",
            image_paths=["assets/homework_images/7_5_14_placeholder.png"],
            knowledge_ids=["boolean_simplification"],
            source_pages=[_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", 11, "assets/course_pages/ch7_p011.png")],
            subquestions=[
                SubQuestion("7.5.14(1)", "化简第一个逻辑式。", "待接入官方答案或题图识别。", ["把最小项填入卡诺图。", "按最大圈组覆盖所有 1。", "写出最简与或式。"]),
                SubQuestion("7.5.14(2)", "化简第二个逻辑式。", "待接入官方答案或题图识别。", ["把最小项填入卡诺图。", "按最大圈组覆盖所有 1。", "写出最简与或式。"]),
            ],
            answer_source="待核对",
        ),
    ]


def seed_content() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    knowledge_points = build_knowledge_points()
    questions = build_questions()
    manifest = {
        "course_pages": sorted({page.image_path for point in knowledge_points for page in point.source_pages}),
        "homework_images": sorted({path for question in questions for path in question.image_paths}),
        "notes": [
            "MVP contains curated representative records; later extraction/OCR tasks should replace placeholders with real images and full question set.",
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
