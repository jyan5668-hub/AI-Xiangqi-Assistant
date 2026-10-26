from app.exp5_rag import (
    DEFAULT_KNOWLEDGE,
    FIXED_QUESTIONS,
    PROMPT_V1,
    PROMPT_V2,
    build_context,
    compare_suite,
    load_documents,
    retrieve,
    run_query,
    split_documents,
)


def test_knowledge_file_exists_and_splits():
    assert DEFAULT_KNOWLEDGE.exists()
    chunks = split_documents(load_documents())
    assert len(chunks) >= 3
    assert all(chunk.chunk_id.startswith("K-") for chunk in chunks)
    assert all(chunk.source == DEFAULT_KNOWLEDGE.name for chunk in chunks)


def test_retrieval_is_ranked_and_has_metadata():
    chunks = split_documents(load_documents())
    results = retrieve("红兵过河后怎么走", chunks, top_k=2)
    assert results
    assert results[0].score >= results[-1].score
    assert "兵" in results[0].matched_terms or "过河" in results[0].matched_terms
    assert "来源=" in build_context(results)


def test_rag_answer_contains_source_and_prompt_context():
    result = run_query("棋局保存在哪里？")
    assert result["error"] is None
    assert "data/games.json" in result["answer"]
    assert "K-" in result["answer"]
    assert "data/games.json" in result["prompt"]


def test_missing_information_returns_insufficient_material():
    result = run_query("如何修改用户的 GitHub 密码？")
    assert "资料不足" in result["answer"]
    assert result["chunks"] == []


def test_prompt_revision_is_more_constrained():
    assert len(PROMPT_V2) > len(PROMPT_V1)
    assert "来源" in PROMPT_V2
    assert "不要凭空补充" in PROMPT_V2


def test_comparison_suite_has_six_independent_questions():
    rows = compare_suite()
    assert len(rows) == len(FIXED_QUESTIONS) == 6
    assert all(row["direct"]["prompt"] != row["rag"]["prompt"] for row in rows)
    assert all("judgement_rule" in row for row in rows)
