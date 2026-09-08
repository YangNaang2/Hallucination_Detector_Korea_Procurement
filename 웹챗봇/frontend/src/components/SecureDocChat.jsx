import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";

const API_URL = "/api/v1/chat-and-detect";
const REPORT_URL = "/api/v1/report-false-positive";
// 0.35 는 원래 Gradio 화면의 기본값이지만, 문서를 추려 넣게 되면서 이 값에서는
// 놓치는 게 많아졌다. 0.15 는 정답 답변에 형광펜을 칠하지 않으면서 더 많이 잡는다.
const DEFAULT_THRESHOLD = 0.15;
const USER_NAME = "박지훈";

/** 환각 의심 구간에 빨간 형광펜을 칠한 답변 본문 */
function HighlightedAnswer({ chunks }) {
  return (
    <p className="whitespace-pre-wrap leading-7 text-slate-800">
      {chunks.map((chunk, i) =>
        chunk.label === "환각 의심" ? (
          <mark
            key={i}
            title="문서에서 근거를 찾지 못한 구간입니다"
            className="rounded bg-red-300/80 px-1 font-medium text-red-950 decoration-red-600 border-b-2 border-red-600"
          >
            {chunk.text}
          </mark>
        ) : (
          <span key={i}>{chunk.text}</span>
        )
      )}
    </p>
  );
}

/** suspicious_count 기반 요약 카드 + 오탐지 신고 */
function VerdictCard({ count, ratio, onReport, reported }) {
  const clean = count === 0;

  return (
    <div className="mt-3 space-y-2">
      <div
        className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
          clean
            ? "border-emerald-300 bg-emerald-50"
            : "border-red-300 bg-red-50"
        }`}
      >
        <span className="text-xl">{clean ? "✅" : "⚠️"}</span>
        <div>
          <p className="text-sm font-semibold text-slate-800">
            {clean ? "근거 없는 부분이 발견되지 않았습니다" : `환각 의심 ${count}곳 발견`}
          </p>
          <p className="text-xs text-slate-500">
            {clean
              ? "답변이 업로드한 문서와 대체로 일치합니다."
              : `답변 글자 수 기준 약 ${(ratio * 100).toFixed(1)}%가 근거 부족 구간입니다.`}
          </p>
        </div>
      </div>

      <div className="text-right">
        {reported ? (
          <span className="text-[11px] text-slate-400">신고가 접수되었습니다. 감사합니다.</span>
        ) : (
          <button
            type="button"
            onClick={onReport}
            className="text-[11px] text-slate-400 underline underline-offset-2 hover:text-slate-600"
          >
            맞는 문장에 형광펜이 칠해졌나요? [오탐지 신고]
          </button>
        )}
      </div>
    </div>
  );
}

/** 생성 + 교차 검증이 끝날 때까지 말풍선 자리를 지키는 스켈레톤 */
function SkeletonBubble() {
  return (
    <div className="w-[28rem] max-w-[80%] rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <p className="mb-3 text-sm text-slate-500">
        AI가 답변을 작성하고 문서를 교차 검증 중입니다...
      </p>
      <div className="animate-pulse space-y-2">
        <div className="h-3 w-11/12 rounded bg-slate-200" />
        <div className="h-3 w-full rounded bg-slate-200" />
        <div className="h-3 w-4/5 rounded bg-slate-200" />
        <div className="h-12 w-full rounded bg-slate-100" />
      </div>
    </div>
  );
}

export default function SecureDocChat() {
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const [loose, setLoose] = useState(false);

  const onDrop = useCallback((accepted) => {
    if (accepted.length) {
      setFile(accepted[0]);
      setError("");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    multiple: false,
    noClick: true,
    accept: {
      "application/pdf": [".pdf"],
      "text/plain": [".txt"],
    },
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    if (!file) return setError("검토할 보안 문서를 먼저 올려주세요.");
    if (!question.trim()) return setError("질문을 입력해 주세요.");

    const asked = question.trim();
    setMessages((prev) => [...prev, { role: "user", text: asked, fileName: file.name }]);
    setQuestion("");
    setError("");
    setLoading(true);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("question", asked);
      form.append("threshold", String(threshold));
      form.append("loose", String(loose));

      const res = await fetch(API_URL, { method: "POST", body: form });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `요청이 실패했습니다 (${res.status})`);
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          question: asked,
          answer: data.answer,
          chunks: data.chunks ?? [],
          count: data.suspicious_count ?? 0,
          ratio: data.suspicious_ratio ?? 0,
          generatedBy: data.generated_by,
          reported: false,
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const reportFalsePositive = async (index) => {
    const target = messages[index];
    setMessages((prev) =>
      prev.map((m, i) => (i === index ? { ...m, reported: true } : m))
    );
    try {
      await fetch(REPORT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: target.question,
          answer: target.answer,
          flagged: target.chunks
            .filter((c) => c.label === "환각 의심")
            .map((c) => c.text),
        }),
      });
    } catch {
      // 신고 전송이 실패해도 시연 흐름을 끊지 않는다.
    }
  };

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      {/* 헤더 */}
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-slate-900">
          {USER_NAME} 님, 검토할 보안 문서를 올려주세요.
        </h1>
        <p className="mt-0.5 text-sm text-slate-500">
          사내 문서 전용 보안 질의응답 · 업로드한 문서 안에서만 답하고, 근거 없는 구간은 형광펜으로 표시합니다.
        </p>
      </header>

      {/* 대화 영역 */}
      <main className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.length === 0 && !loading && (
          <p className="mt-16 text-center text-sm text-slate-400">
            아래에 문서를 끌어다 놓고 질문을 입력하면 검토가 시작됩니다.
          </p>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-slate-900 px-4 py-3 text-white shadow-sm">
                <p className="whitespace-pre-wrap leading-6">{m.text}</p>
                <p className="mt-1.5 text-[11px] text-slate-400">📎 {m.fileName}</p>
              </div>
            </div>
          ) : (
            <div key={i} className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
                {m.generatedBy === "mock" && (
                  <p className="mb-2 inline-block rounded bg-amber-100 px-2 py-0.5 text-[11px] text-amber-700">
                    목업 답변 (Ollama 미연결 · 탐지 결과는 실제 모델)
                  </p>
                )}
                <HighlightedAnswer chunks={m.chunks} />
                <VerdictCard
                  count={m.count}
                  ratio={m.ratio}
                  reported={m.reported}
                  onReport={() => reportFalsePositive(i)}
                />
              </div>
            </div>
          )
        )}

        {loading && (
          <div className="flex justify-start">
            <SkeletonBubble />
          </div>
        )}
      </main>

      {/* 입력 영역 */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-slate-200 bg-white px-6 py-4"
      >
        <div
          {...getRootProps()}
          className={`mb-3 rounded-xl border-2 border-dashed px-4 py-4 text-center transition ${
            isDragActive
              ? "border-slate-900 bg-slate-100"
              : "border-slate-300 bg-slate-50"
          }`}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="flex items-center justify-center gap-2 text-sm text-slate-700">
              <span>📄 {file.name}</span>
              <button
                type="button"
                onClick={() => setFile(null)}
                className="text-xs text-slate-400 hover:text-red-500"
              >
                제거
              </button>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              보안 문서(PDF · TXT)를 이곳에 드래그 앤 드롭하거나{" "}
              <button
                type="button"
                onClick={open}
                className="font-medium text-slate-900 underline underline-offset-2"
              >
                파일 선택
              </button>
            </p>
          )}
        </div>

        <div className="mb-3 flex items-center gap-3">
          <label
            htmlFor="threshold"
            className="shrink-0 text-xs font-medium text-slate-600"
          >
            민감도 {threshold.toFixed(2)}
          </label>
          <input
            id="threshold"
            type="range"
            min="0.05"
            max="0.9"
            step="0.05"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="h-1 flex-1 cursor-pointer accent-slate-900"
          />
          <span className="shrink-0 text-[11px] text-slate-400">
            낮출수록 더 많이 잡습니다
          </span>

          <label className="flex shrink-0 cursor-pointer items-center gap-1.5 border-l border-slate-200 pl-3 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={loose}
              onChange={(e) => setLoose(e.target.checked)}
              className="accent-red-600"
            />
            환각 유발 모드
          </label>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="문서에 대해 궁금한 점을 입력하세요."
            className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-900"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? "검증 중..." : "전송"}
          </button>
        </div>

        {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      </form>
    </div>
  );
}
