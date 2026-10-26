"""实验5：LLM、Context 与 RAG 的最小可运行链路。

默认使用离线演示模型，保证没有 API Key 时也能重复运行检索、上下文组织、
引用和对比测试。设置 LLM_API_KEY 后可通过 OpenAI 兼容接口切换到云端模型。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = ROOT / "docs" / "knowledge"
EVIDENCE_DIR = ROOT / "docs" / "evidence" / "exp5"
DEFAULT_KNOWLEDGE = KNOWLEDGE_DIR / "xiangqi_rules.md"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source: str
    heading: str


@dataclass
class Retrieval:
    chunk: Chunk
    score: int
    matched_terms: list[str]


def tokenize(text: str) -> list[str]:
    """提取中文词串、英文词和数字；去重但保留首次出现顺序。"""

    text = text.lower()
    runs = re.findall(r"[\u4e00-\u9fff]+", text)
    tokens: list[str] = []
    for run in runs:
        tokens.extend(run)
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
        tokens.extend(run[index : index + 3] for index in range(len(run) - 2))
        if len(run) <= 8:
            tokens.append(run)
    tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9_-]*|\d+", text))
    stop = {"什么", "如何", "可以", "系统", "请问", "一下", "这个", "以及", "关于", "的", "吗", "了", "在", "哪", "里", "怎么"}
    return list(dict.fromkeys(t for t in tokens if t not in stop))


def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_documents(directory: Path = KNOWLEDGE_DIR) -> list[tuple[str, str]]:
    docs = []
    for path in sorted(directory.glob("*.md")):
        text = clean_text(path.read_text(encoding="utf-8"))
        if text:
            docs.append((path.name, text))
    return docs


def split_documents(documents: Iterable[tuple[str, str]], max_chars: int = 360, overlap: int = 60) -> list[Chunk]:
    """按标题和段落切分，过长段落按字符窗口切分并保留少量重叠。"""

    chunks: list[Chunk] = []
    for source, document in documents:
        heading = "文档"
        section_parts: list[str] = []
        for line in document.splitlines():
            if line.startswith("#"):
                if section_parts:
                    chunks.extend(_window_chunks(source, heading, "\n".join(section_parts), max_chars, overlap))
                    section_parts = []
                heading = line.lstrip("# ").strip() or heading
            elif line.strip():
                section_parts.append(line.strip())
        if section_parts:
            chunks.extend(_window_chunks(source, heading, "\n".join(section_parts), max_chars, overlap))
    return [Chunk(f"K-{index:03d}", c.text, c.source, c.heading) for index, c in enumerate(chunks, 1)]


def _window_chunks(source: str, heading: str, text: str, max_chars: int, overlap: int) -> list[Chunk]:
    text = clean_text(text)
    if len(text) <= max_chars:
        return [Chunk("", text, source, heading)]
    pieces = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            boundary = max(text.rfind("。", start, end), text.rfind("\n", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        pieces.append(Chunk("", text[start:end].strip(), source, heading))
        if end == len(text):
            break
        start = max(0, end - overlap)
    return pieces


def retrieve(query: str, chunks: list[Chunk], top_k: int = 3) -> list[Retrieval]:
    # 单字在中文中区分度很低；只保留长度>=2的词组，并保留少数领域关键词。
    terms = [term for term in tokenize(query) if len(term) >= 2 or term in {"兵", "卒", "AI", "RAG"}]
    ranked: list[Retrieval] = []
    for chunk in chunks:
        haystack = f"{chunk.heading} {chunk.text}".lower()
        matched = [term for term in terms if term in haystack]
        score = sum(haystack.count(term) for term in matched)
        if score:
            ranked.append(Retrieval(chunk, score, matched))
    ranked.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
    return ranked[:top_k]


PROMPT_V1 = """你是象棋学习助手。请根据用户问题回答，信息不足时说明不知道。
用户问题：{question}
"""

PROMPT_V2 = """你是 AI 象棋对弈助手的知识问答模块。
任务要求：只根据给定资料回答；资料不足时明确说“资料不足”，不要凭空补充。
回答格式：先给结论，再给不超过3条要点；每个事实后用 [来源: K-xxx] 标注。
用户问题：{question}
检索资料：
{context}
"""


def build_context(results: list[Retrieval]) -> str:
    if not results:
        return "（没有检索到相关资料）"
    return "\n\n".join(
        f"[{item.chunk.chunk_id}] 来源={item.chunk.source}，标题={item.chunk.heading}\n{item.chunk.text}"
        for item in results
    )


class OfflineDemoModel:
    """可重复的本地演示模型，用于没有 API Key 时验证链路。"""

    name = "offline-demo-v1"

    def answer(self, question: str, prompt: str, results: list[Retrieval] | None = None) -> str:
        if not results:
            return "资料不足：当前知识库没有能支持该问题的片段。"
        if "保存" in question or "棋局" in question:
            conclusion = "棋局使用本地 JSON 文件保存，文件名为 data/games.json。"
        elif "兵" in question or "过河" in question:
            conclusion = "红兵未过河只能向前走一格；过河后可以向前或横向走一格。"
        elif "RAG" in question or "检索" in question:
            conclusion = "RAG 先检索相关片段，再把片段和来源编号加入模型上下文。"
        elif "引擎" in question or "AI" in question:
            conclusion = "当前版本是本地练习模式，尚未接入真实象棋引擎。"
        else:
            conclusion = results[0].chunk.text.split("。", 1)[0] + "。"
        citations = " ".join(f"[来源: {item.chunk.chunk_id}]" for item in results[:2])
        return f"{conclusion}\n- 回答依据：{citations}"


class OpenAICompatibleModel:
    """调用 OpenAI Chat Completions 兼容接口；不保存 API Key。"""

    def __init__(self, api_key: str, model: str, endpoint: str, timeout: float = 20.0):
        self.api_key = api_key
        self.name = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def answer(self, question: str, prompt: str, results: list[Retrieval] | None = None) -> str:
        body = json.dumps(
            {
                "model": self.name,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "你是严谨的知识问答助手。"},
                    {"role": "user", "content": prompt},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"模型调用失败：{exc}") from exc


def make_model(mode: str):
    if mode == "offline":
        return OfflineDemoModel()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("缺少 LLM_API_KEY；请设置环境变量，或使用 --mode offline")
    return OpenAICompatibleModel(
        api_key,
        os.getenv("LLM_MODEL", "gpt-4o-mini"),
        os.getenv("LLM_ENDPOINT", "https://api.openai.com/v1"),
    )


def run_query(question: str, mode: str = "offline", top_k: int = 3, prompt_version: str = "v2") -> dict[str, Any]:
    chunks = split_documents(load_documents())
    results = retrieve(question, chunks, top_k=top_k)
    context = build_context(results)
    template = PROMPT_V2 if prompt_version == "v2" else PROMPT_V1
    prompt = template.format(question=question, context=context) if prompt_version == "v2" else template.format(question=question)
    started = time.perf_counter()
    model = None
    model_error = None
    try:
        model = make_model(mode)
    except RuntimeError as exc:
        model_error = str(exc)
    try:
        if model_error:
            raise RuntimeError(model_error)
        answer = model.answer(question, prompt, results)
        error = None
    except RuntimeError as exc:
        answer = ""
        error = str(exc)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "question": question,
        "mode": mode,
        "model": getattr(model, "name", os.getenv("LLM_MODEL", "unavailable")),
        "prompt_version": prompt_version,
        "top_k": top_k,
        "chunks": [asdict(item.chunk) | {"score": item.score, "matched_terms": item.matched_terms} for item in results],
        "context": context,
        "prompt": prompt,
        "answer": answer,
        "error": error,
        "elapsed_ms": elapsed_ms,
    }


FIXED_QUESTIONS = [
    "棋局保存在哪里？",
    "红兵过河前后分别怎么走？",
    "RAG 检索链路如何组织上下文？",
    "当前版本是否已经接入真实象棋引擎？",
    "如何修改用户的 GitHub 密码？",
    "系统能否保证每一步都是绝对最优？",
]


def compare_suite(mode: str = "offline") -> list[dict[str, Any]]:
    """用相同问题分别执行直接模型和 RAG；直接组不把检索资料放入 prompt。"""

    chunks = split_documents(load_documents())
    model = make_model(mode)
    rows = []
    for question in FIXED_QUESTIONS:
        results = retrieve(question, chunks, top_k=3)
        direct_prompt = PROMPT_V1.format(question=question)
        rag_prompt = PROMPT_V2.format(question=question, context=build_context(results))
        started = time.perf_counter()
        direct_error = None
        try:
            direct_answer = model.answer(question, direct_prompt, []) if mode == "offline" else model.answer(question, direct_prompt, [])
        except RuntimeError as exc:
            direct_answer, direct_error = "", str(exc)
        direct_ms = round((time.perf_counter() - started) * 1000, 2)
        started = time.perf_counter()
        rag_error = None
        try:
            rag_answer = model.answer(question, rag_prompt, results)
        except RuntimeError as exc:
            rag_answer, rag_error = "", str(exc)
        rag_ms = round((time.perf_counter() - started) * 1000, 2)
        rows.append(
            {
                "question": question,
                "direct": {"prompt": direct_prompt, "answer": direct_answer, "error": direct_error, "elapsed_ms": direct_ms},
                "rag": {"prompt": rag_prompt, "answer": rag_answer, "error": rag_error, "elapsed_ms": rag_ms, "sources": [x.chunk.chunk_id for x in results]},
                "judgement_rule": "回答必须有依据；资料无答案时应明确资料不足；引用必须来自返回片段。",
            }
        )
    return rows


def write_evidence(payload: Any, name: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="实验5 LLM、Context 与 RAG 演示")
    parser.add_argument("--question", default="红兵过河前后分别怎么走？")
    parser.add_argument("--mode", choices=["offline", "cloud"], default="offline")
    parser.add_argument("--prompt", choices=["v1", "v2"], default="v2")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--suite", action="store_true", help="运行6个固定问题的直接模型/RAG对比")
    parser.add_argument("--failure-test", action="store_true", help="执行一次云端连接失败/缺少Key测试")
    args = parser.parse_args(argv)
    if args.failure_test:
        result = run_query(args.question, mode="cloud", top_k=args.top_k, prompt_version=args.prompt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        path = write_evidence(result, "failure-cloud.json")
        print(f"证据文件：{path}")
        return 0 if result["error"] else 1
    if args.suite:
        result = compare_suite(args.mode)
        path = write_evidence(result, f"comparison-{args.mode}.json")
        print(f"固定问题数：{len(result)}")
        print(f"对比结果：{path}")
        for row in result:
            print(f"- {row['question']} | direct={row['direct']['elapsed_ms']}ms | rag={row['rag']['elapsed_ms']}ms | sources={','.join(row['rag']['sources']) or 'none'}")
        return 0
    result = run_query(args.question, mode=args.mode, top_k=args.top_k, prompt_version=args.prompt)
    path = write_evidence(result, f"query-{args.mode}-{args.prompt}.json")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"证据文件：{path}")
    return 0 if not result["error"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
