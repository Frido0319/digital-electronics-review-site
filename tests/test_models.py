from src.models import (
    KnowledgePoint,
    Question,
    SourcePage,
    SubQuestion,
    to_jsonable,
)


def test_question_serializes_with_subquestions_and_sources():
    question = Question(
        id="5.1.8",
        chapter="5",
        title="桥式整流参数计算",
        prompt="采用单相桥式整流电路供电。",
        image_paths=["assets/homework_images/5_1_8.png"],
        knowledge_ids=["rectifier_bridge"],
        source_pages=[SourcePage(file="第5章-直流稳压电源.pdf", page=9, image_path="assets/course_pages/ch5_p009.png")],
        subquestions=[
            SubQuestion(
                id="5.1.8(1)",
                prompt="求变压器二次电压。",
                answer="U2 = 122 V",
                solution_steps=["UO = 0.9U2", "U2 = 110 / 0.9"],
            )
        ],
        answer_source="推导答案",
    )

    data = to_jsonable(question)

    assert data["id"] == "5.1.8"
    assert data["subquestions"][0]["id"] == "5.1.8(1)"
    assert data["source_pages"][0]["page"] == 9


def test_knowledge_point_serializes_related_questions():
    point = KnowledgePoint(
        id="rectifier_bridge",
        chapter="5",
        title="单相桥式整流",
        summary="把交流电变成脉动直流。",
        must_know="会计算输出平均电压、电流和二极管反向峰值。",
        intuition="桥式电路让负半周也以同一方向流过负载。",
        prerequisites=["二极管单向导电性", "正弦交流电有效值与峰值"],
        formulas=["UO = 0.9U2", "IO = UO / RL"],
        source_pages=[SourcePage(file="第5章-直流稳压电源.pdf", page=9, image_path="assets/course_pages/ch5_p009.png")],
        related_questions=["5.1.8"],
        pitfalls=["不要把有效值和平均值混用。"],
    )

    data = to_jsonable(point)

    assert data["id"] == "rectifier_bridge"
    assert data["prerequisites"] == ["二极管单向导电性", "正弦交流电有效值与峰值"]
    assert data["related_questions"] == ["5.1.8"]
