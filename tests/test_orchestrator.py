"""Orchestrator + LangGraph 测试。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from orchestrator.models import ExamConfig, ExamPaper, ChoiceQuestion, Difficulty, QuestionType
from orchestrator.graph import build_exam_graph

def test_exam_config():
    c = ExamConfig(source_material="test", question_types=["choice","judgment"], total_count=5)
    assert c.total_count == 5

def test_exam_paper():
    q = ChoiceQuestion(stem="Q?", options=["A","B","C","D"], correct_index=0, knowledge_point="x", difficulty=Difficulty.EASY)
    p = ExamPaper(id="t1", questions=[q], question_count=1)
    assert p.question_count == 1
    assert len(p.questions) == 1

def test_graph_build():
    g = build_exam_graph()
    nodes = [n for n in g.nodes]
    assert "extract_knowledge" in nodes
    assert "compose_exam" in nodes
    assert len(nodes) == 5  # START + 4 nodes

def test_graph_structure():
    g = build_exam_graph()
    # 验证条件边存在
    assert "process_next_question" in [n for n in g.nodes]
