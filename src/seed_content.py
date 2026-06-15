from __future__ import annotations

import json

from . import config
from .models import KnowledgePoint, Question, SourcePage, SubQuestion, to_jsonable


def _source(file: str, page: int, image: str) -> SourcePage:
    return SourcePage(file=file, page=page, image_path=image)


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
            answer_source="推导答案",
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
            answer_source="推导答案",
        ),
        _pending_question(
            "7.2.5",
            "7",
            "控制门电路逻辑式与波形",
            "在图 (a) 门电路中，分别在 C=1 和 C=0 时求输出 Y 的逻辑式和波形，并说明功能。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章-门电路和组合逻辑电路1.pdf", 16, "assets/course_pages/ch7_p016.png")],
            ["先写出每一级门输出表达式。", "分别代入 C=1 和 C=0 化简。", "根据 A、B 波形逐段画 Y。"],
        ),
        _pending_question(
            "7.3.1",
            "7",
            "用 74LS00 与非门实现逻辑功能",
            "试用一片 74LS00 与非门实现指定逻辑关系。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image2.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路2.pdf", 1, "assets/course_pages/ch7_2_p001.png")],
            ["确认 74LS00 内含四个二输入与非门。", "把目标逻辑改写成与非-与非形式。", "分配芯片内四个门并画引脚连接。"],
        ),
        _pending_question(
            "7.5.9",
            "7",
            "与非门和非门实现逻辑关系",
            "用与非门和非门实现给定逻辑关系，并画出逻辑图。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", 11, "assets/course_pages/ch7_p011.png")],
            ["先把逻辑式化简。", "用双重否定把表达式变成与非形式。", "需要反相时用与非门输入并接实现非门。"],
        ),
        _pending_question(
            "7.5.13",
            "7",
            "逻辑代数恒等式推证",
            "应用逻辑代数运算法则推证给定各式。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路3.pdf", 2, "assets/course_pages/ch7_3_p002.png")],
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
                SubQuestion("7.5.14(1)", "化简第一个逻辑式。", "待接入官方答案或题图识别。", ["把最小项填入卡诺图。", "按最大圈组覆盖所有 1。", "写出最简与或式。"]),
                SubQuestion("7.5.14(2)", "化简第二个逻辑式。", "待接入官方答案或题图识别。", ["把最小项填入卡诺图。", "按最大圈组覆盖所有 1。", "写出最简与或式。"]),
            ],
            answer_source="待核对",
        ),
        _pending_question(
            "7.6.17a",
            "7",
            "列车优先通行组合逻辑设计",
            "特快、普快、普慢按优先级通行，同一时刻只能给一个开车信号，设计逻辑电路。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["combinational_logic_design"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路4.pdf", 12, "assets/course_pages/ch7_p012.png")],
            ["定义 A、B、C 为请求信号。", "最高优先级 YA=A。", "普快需在无特快时输出。", "普慢需在无特快且无普快时输出。"],
        ),
        _pending_question(
            "7.6.17b",
            "7",
            "8421BCD 码范围检测逻辑设计",
            "设 A、B、C、D 为 4 位 8421BCD 码，当数字 x<3 或 x>6 时输出 1，否则输出 0，用与非门组成逻辑图。",
            ["assets/homework_images/7 门电路和组合逻辑电路作业_image1.png"],
            ["combinational_logic_design", "boolean_simplification"],
            [_source("第7章 门电路和组合逻辑电路/第7章 门电路和组合逻辑电路4.pdf", 12, "assets/course_pages/ch7_p012.png")],
            ["列出 0 到 9 的 BCD 真值表。", "把 0、1、2、7、8、9 标为输出 1。", "10 到 15 可作为无关项。", "化简后转成与非门实现。"],
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


def render_required_source_pages() -> None:
    from .extract_sources import convert_office_to_pdf, render_pdf_page

    known_files = {
        str(path.relative_to(config.SOURCE_ROOT)).replace("\\", "/"): path
        for files in config.SOURCE_FILES.values()
        for path in files
    }
    rendered: set[str] = set()
    for point in build_knowledge_points():
        for page in point.source_pages:
            source = known_files.get(page.file.replace("\\", "/"))
            if source is None or source.suffix.lower() != ".pdf" or page.image_path in rendered:
                if source is not None and source.suffix.lower() in {".ppt", ".pptx"}:
                    output_pdf = config.PROJECT_ROOT / "tmp" / "office_convert" / "ch4_feedback.pdf"
                    if convert_office_to_pdf(source, output_pdf):
                        render_pdf_page(output_pdf, page.page, config.PROJECT_ROOT / page.image_path)
                        rendered.add(page.image_path)
                continue
            render_pdf_page(source, page.page, config.PROJECT_ROOT / page.image_path)
            rendered.add(page.image_path)


def render_required_homework_pages() -> None:
    from .extract_sources import convert_office_to_pdf, render_pdf_page

    ch5_homework = next((path for path in config.HOMEWORK_FILES if path.name.startswith("5 ")), None)
    if ch5_homework is None:
        return
    output_pdf = config.PROJECT_ROOT / "tmp" / "office_convert" / "ch5_homework.pdf"
    if convert_office_to_pdf(ch5_homework, output_pdf):
        render_pdf_page(output_pdf, 1, config.PROJECT_ROOT / "assets/homework_images/ch5_homework_page001.png")
